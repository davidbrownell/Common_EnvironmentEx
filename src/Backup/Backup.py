# ----------------------------------------------------------------------
# |  
# |  Backup.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-09-19 21:31:45
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018-19.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""Processes files for offsite or mirrored backup."""

import hashlib
import json
import os
import re
import shutil
import sys
import textwrap
import threading

from collections import OrderedDict

import inflect as inflect_mod
import six

import CommonEnvironment
from CommonEnvironment.CallOnExit import CallOnExit
from CommonEnvironment import CommandLine
from CommonEnvironment import FileSystem
from CommonEnvironment import Process
from CommonEnvironment.Shell.All import CurrentShell
from CommonEnvironment.StreamDecorator import StreamDecorator
from CommonEnvironment import TaskPool

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

OFFSITE_BACKUP_FILENAME                     = "Backup.7z"
DATA_FILENAME                               = "data.json"

inflect                                     = inflect_mod.engine()

StreamDecorator.InitAnsiSequenceStreams()

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( destination=CommandLine.EntryPoint.Parameter("Destination directory"),
                         input=CommandLine.EntryPoint.Parameter("One or more filenames or directories used to parse for input"),
                         force=CommandLine.EntryPoint.Parameter("Ignore information in the destination when calculating work to execute"),
                         simple_compare=CommandLine.EntryPoint.Parameter("Compare via file size and modified date rather than with a hash. This will be faster, but more error prone when detecting changes."),
                         include=CommandLine.EntryPoint.Parameter("One or more regular expressions used to specify filenames to include"),
                         exclude=CommandLine.EntryPoint.Parameter("One or more regular expressions used to specify filenames to exclude"),
                         traverse_include=CommandLine.EntryPoint.Parameter("One or more regular expressions used to specify directory names to include while parsing"),
                         traverse_exclude=CommandLine.EntryPoint.Parameter("One or more regular expressions used to specify directory names to exclude while parsing"),
                         display_only=CommandLine.EntryPoint.Parameter("Display the operations that would be taken but do not perform them"),
                         no_status=CommandLine.EntryPoint.Parameter("Do not display file-specific status when performing long-running operations"),
                       )
@CommandLine.Constraints( destination=CommandLine.DirectoryTypeInfo(ensure_exists=False),
                          input=CommandLine.FilenameTypeInfo(match_any=True, arity='+'),
                          include=CommandLine.StringTypeInfo(arity='*'),
                          exclude=CommandLine.StringTypeInfo(arity='*'),
                          traverse_include=CommandLine.StringTypeInfo(arity='*'),
                          traverse_exclude=CommandLine.StringTypeInfo(arity='*'),
                          output_stream=None,
                        )
def Mirror( destination,
            input,
            force=False,
            simple_compare=False,
            include=None,
            exclude=None,
            traverse_include=None,
            traverse_exclude=None,
            display_only=False,
            no_status=False,
            output_stream=sys.stdout,
            verbose=False,
            preserve_ansi_escape_sequences=False,
          ):
    """\
    Mirrors files to a different location. Both the input source and destination are 
    scanned when calculating the operations necessary to ensure that the destination
    matches the input source(s).
    """

    destination = FileSystem.Normalize(destination)
    inputs = [ FileSystem.Normalize(i) for i in input ]; del input
    includes = include; del include
    excludes = exclude; del exclude
    traverse_includes = traverse_include; del traverse_include
    traverse_excludes = traverse_exclude; del traverse_exclude

    with StreamDecorator.GenerateAnsiSequenceStream( output_stream,
                                                     preserve_ansi_escape_sequences=preserve_ansi_escape_sequences,
                                                   ) as output_stream:
        with output_stream.DoneManager( line_prefix='',
                                        prefix="\nResults: ",
                                        suffix='\n',
                                      ) as dm:
            source_file_info = _GetFileInfo( "source",
                                             inputs,
                                             includes,
                                             excludes,
                                             traverse_includes,
                                             traverse_excludes,
                                             simple_compare,
                                             dm.stream,
                                             is_ssd=False,
                                             no_status=no_status,
                                           )
            dm.stream.write('\n')

            if not force and os.path.isdir(destination):
                dest_file_info = _GetFileInfo( "destination",
                                               [ destination, ],
                                               None, # includes
                                               None, # excludes
                                               None, # traverse_includes
                                               None, # traverse_excludes
                                               simple_compare,
                                               dm.stream,
                                               is_ssd=False,
                                               no_status=no_status,
                                             )
                dm.stream.write('\n')
            else:
                dest_file_info = {}

            work = _CreateWork( source_file_info,
                                dest_file_info,
                                destination,
                                simple_compare,
                                dm.stream,
                                verbose,
                              )

            if display_only:
                _Display(work, dm.stream, show_dest=True)
                return dm.result

            FileSystem.MakeDirs(destination)

            executed_work = False

            # Copy files
            tasks = []

            for sfi, dfi in six.iteritems(work):
                if sfi is None:
                    continue

                sfi = sfi.Name
                dfi = getattr(dfi, "Name", dfi)

                tasks.append(( sfi, dfi ))

            if tasks:
                # ----------------------------------------------------------------------
                def Execute(task_index, task_output):
                    try:
                        source, dest = tasks[task_index]

                        FileSystem.MakeDirs(os.path.dirname(dest))

                        dest_temp = "{}.copying".format(dest)
                        FileSystem.RemoveFile(dest_temp)

                        shutil.copy2(source, dest_temp)
                        FileSystem.RemoveFile(dest)
                        shutil.move(dest_temp, dest)

                    except Exception as ex:
                        task_output.write(str(ex))
                        return -1

                # ----------------------------------------------------------------------

                with dm.stream.SingleLineDoneManager( "Copying {}...".format(inflect.no("file", len(tasks))),
                                                    ) as this_dm:
                    this_dm.result = TaskPool.Execute( [ TaskPool.Task( "Copy '{}' to '{}'".format(source, dest),
                                                                        Execute,
                                                                      ) 
                                                         for source, dest in tasks
                                                       ],
                                                       num_concurrent_tasks=1,
                                                       optional_output_stream=this_dm.stream,
                                                       progress_bar=True,
                                                     )
                    if this_dm.result != 0:
                        return this_dm.result

                executed_work = True

            # Remove files
            removed_files = [ dfi.Name for dfi in work.get(None, []) ]

            if removed_files:
                # ----------------------------------------------------------------------
                def Execute(task_index, task_output):
                    try:
                        filename = removed_files[task_index]
                        FileSystem.RemoveFile(filename)

                    except Exception as ex:
                        task_output.write(str(ex))
                        return -1

                # ----------------------------------------------------------------------

                with dm.stream.SingleLineDoneManager( "Removing {}...".format(inflect.no("file", len(removed_files))),
                                                    ) as this_dm:
                    this_dm.result = TaskPool.Execute( [ TaskPool.Task( "Remove '{}'".format(filename),
                                                                        Execute
                                                                      ) 
                                                         for filename in removed_files
                                                       ],
                                                       num_concurrent_tasks=1,
                                                       optional_output_stream=this_dm.stream,
                                                       progress_bar=True,
                                                     )
                    if this_dm.result != 0:
                        return this_dm.result

                executed_work = True

            if not executed_work:
                dm.result = 1

        return dm.result

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( backup_name=CommandLine.EntryPoint.Parameter("Name used to uniquely identify the backup"),
                         output_dir=CommandLine.EntryPoint.Parameter("Output directory that will contain the file(s) that have been added/removed"),
                         input=CommandLine.EntryPoint.Parameter("One or more filenames or directories used to parse for input"),
                         force=CommandLine.EntryPoint.Parameter("Ignore previously saved information when calculating work to execute"),
                         ssd=CommandLine.EntryPoint.Parameter("Leverage optimizations available if the source drive is a Solid-State Drive (SSD)"),
                         compress=CommandLine.EntryPoint.Parameter("Compress the data"),
                         encryption_password=CommandLine.EntryPoint.Parameter("Encrypt the data with this password"),
                         symlinks=CommandLine.EntryPoint.Parameter("Create symbolic links rather than copying files"),
                         auto_commit=CommandLine.EntryPoint.Parameter("Invoke 'CommitOffsite' automatically"),
                         include=CommandLine.EntryPoint.Parameter("One or more regular expressions used to specify filenames to include"),
                         exclude=CommandLine.EntryPoint.Parameter("One or more regular expressions used to specify filenames to exclude"),
                         traverse_include=CommandLine.EntryPoint.Parameter("One or more regular expressions used to specify directory names to include while parsing"),
                         traverse_exclude=CommandLine.EntryPoint.Parameter("One or more regular expressions used to specify directory names to exclude while parsing"),
                         display_only=CommandLine.EntryPoint.Parameter("Display the operations that would be taken but does not perform them"),
                         working_dir=CommandLine.EntryPoint.Parameter("Specify a custom working directory; use this option if space on the drive associated with 'output_dir' is limited and another drive is available"),
                         no_status=CommandLine.EntryPoint.Parameter("Do not display file-specific status when performing long-running operations"),
                       )
@CommandLine.Constraints( backup_name=CommandLine.StringTypeInfo(),
                          output_dir=CommandLine.DirectoryTypeInfo(ensure_exists=False),
                          input=CommandLine.FilenameTypeInfo(match_any=True, arity='+'),
                          encryption_password=CommandLine.StringTypeInfo(arity='?'),
                          include=CommandLine.StringTypeInfo(arity='*'),
                          exclude=CommandLine.StringTypeInfo(arity='*'),
                          traverse_include=CommandLine.StringTypeInfo(arity='*'),
                          traverse_exclude=CommandLine.StringTypeInfo(arity='*'),
                          working_dir=CommandLine.DirectoryTypeInfo(ensure_exists=False, arity='?'),
                          hash_block_size=CommandLine.IntTypeInfo(min=1, arity='?'),
                          output_stream=None,
                        )
def Offsite( backup_name,
             output_dir,
             input,
             force=False,
             ssd=False,
             compress=False,
             encryption_password=None,
             symlinks=False,
             auto_commit=False,
             include=None,
             exclude=None,
             traverse_include=None,
             traverse_exclude=None,
             display_only=False,
             no_status=False,
             working_dir=None,
             hash_block_size=None,
             output_stream=sys.stdout,
             verbose=False,
             preserve_ansi_escape_sequences=False,
           ):
    """\
    Prepares data to backup based on the result of previous invocations.
    """

    if symlinks and (compress or encryption_password):
        raise CommandLine.UsageException("The 'symlinks' option is not compatible with compression or encryption")

    inputs = input; del input
    includes = include; del include
    excludes = exclude; del exclude
    traverse_includes = traverse_include; del traverse_include
    traverse_excludes = traverse_exclude; del traverse_exclude

    with StreamDecorator.GenerateAnsiSequenceStream( output_stream,
                                                     preserve_ansi_escape_sequences=preserve_ansi_escape_sequences,
                                                   ) as output_stream:
        with output_stream.DoneManager( line_prefix='',
                                        prefix="\nResults: ",
                                        suffix='\n',
                                      ) as dm:
            json_filename = _CreateJsonFilename(backup_name)

            # Read the source info
            source_file_info = _GetFileInfo( "source",
                                             inputs,
                                             includes,
                                             excludes,
                                             traverse_includes,
                                             traverse_excludes,
                                             False,     # simple_compare
                                             dm.stream,
                                             is_ssd=ssd,
                                             no_status=no_status,
                                             hash_block_size=hash_block_size,
                                           )
            dm.stream.write('\n')

            # Read the destination info
            dest_file_info = {}
            dest_hashes = set()

            if not force and os.path.isfile(json_filename):
                try:
                    with open(json_filename) as f:
                        dest_file_info = [ _FileInfo.FromJson(item) for item in json.load(f) ]

                    for dfi in dest_file_info:
                        dest_hashes.add(dfi.Hash)

                except:
                    dm.stream.write("WARNING: The previously saved data appears to be corrupt and will not be used.\n")
            
            # Calculate the work to complete
            work = _CreateWork( source_file_info,
                                dest_file_info,
                                None,
                                False,      # simple_compare
                                dm.stream,
                                verbose,
                              )

            if display_only:
                _Display(work, dm.stream, show_dest=False)
                return dm.result

            # Process the files to add
            to_copy = OrderedDict()

            dm.stream.write("Creating Application Data...")
            with dm.stream.DoneManager():
                data = []

                for sfi, dfi in six.iteritems(work):
                    if sfi is None:
                        continue
                    
                    if sfi.Hash not in dest_hashes:
                        to_copy[sfi.Name] = os.path.join(output_dir, sfi.Hash)
                        dest_hashes.add(sfi.Hash)

                    data.append({ "filename" : sfi.Name,
                                  "hash" : sfi.Hash,
                                  "operation" : "add" if isinstance(dfi, six.string_types) else "modify",
                                })

                for dfi in work.get(None, []):
                    data.append({ "filename" : dfi.Name,
                                  "hash" : dfi.Hash,
                                  "operation" : "remove",
                                })

            if not data:
                dm.stream.write("No content to apply.\n")
                dm.result = 1
            
                return dm.result

            dm.stream.write("Applying Content...")
            with dm.stream.DoneManager( suffix='\n',    
                                      ) as apply_dm:
                apply_dm.stream.write("Cleaning Previous Content...")
                with apply_dm.stream.DoneManager():
                    FileSystem.RemoveTree(output_dir)

                os.makedirs(output_dir)

                apply_dm.stream.write("Writing '{}'...".format(DATA_FILENAME))
                with apply_dm.stream.DoneManager():
                    with open(os.path.join(output_dir, DATA_FILENAME), 'w') as f:
                        json.dump(data, f)

                del data # Save memory

                if to_copy:
                    with apply_dm.stream.SingleLineDoneManager( "Copying Content...",
                                                              ) as copy_dm:
                        items = [ (k, v) for k, v in six.iteritems(to_copy) ]

                        if symlinks:
                            # Use task pool functionality for the progress bar
                            batch_size = 1000

                            batches = list(six.moves.range(0, len(items), batch_size))

                            # ----------------------------------------------------------------------
                            def Execute(task_index, task_output):
                                index = batches[task_index]
                                these_items = items[index:index + batch_size]

                                # Create symlink commands for these items
                                commands = [ CurrentShell.Commands.SymbolicLink(dest, source) for source, dest in these_items ]

                                result, output = CurrentShell.ExecuteCommands(commands)
                                if result != 0:
                                    task_output.write(output)

                                return result

                            # ----------------------------------------------------------------------

                            tasks = [ TaskPool.Task(str(batch), Execute) for batch in batches ]

                        else:
                            # ----------------------------------------------------------------------
                            def Execute(task_index, on_status_update):
                                source, dest = items[task_index]

                                if not no_status:
                                    on_status_update(FileSystem.GetSizeDisplay(os.path.getsize(source)))

                                shutil.copy2(source, dest)

                            # ----------------------------------------------------------------------

                            tasks = [ TaskPool.Task( "'{}' -> '{}'".format(source, dest),
                                                     Execute,
                                                   )
                                      for source, dest in items 
                                    ]

                        # Execute the tasks
                        copy_dm.result = TaskPool.Execute( tasks,
                                                           copy_dm.stream,
                                                           num_concurrent_tasks=None if ssd else 1,
                                                           progress_bar=True,
                                                         )

                        if copy_dm.result != 0:
                            return copy_dm.result

                del to_copy # Save memory

            if compress or encryption_password:
                # Compress and/or encrypt using 7zip
                if compress and encryption_password:
                    description = "Compressing and Encrypting data..."
                    compression_level = 9
                    encryption_arg = ' "-p{}"'.format(encryption_password)
                elif compress:
                    description = "Compressing data..."
                    compression_level = 9
                    encryption_arg = ''
                elif encryption_password:
                    description = "Encrypting data..."
                    compression_level = 0
                    encryption_arg = ' "-p{}"'.format(encryption_password)
                else:
                    assert False

                dm.stream.write(description)
                with dm.stream.DoneManager() as zip_dm:
                    temp_dir = working_dir or output_dir + ".tmp"
                    
                    FileSystem.RemoveTree(temp_dir)
                    os.makedirs(temp_dir)

                    zip_dm.stream.write("Creating Instructions...")
                    with zip_dm.stream.DoneManager():
                        filenames_filename = CurrentShell.CreateTempFilename()

                        with open(filenames_filename, 'w') as f:
                            f.write('\n'.join([ os.path.join(output_dir, name) for name in os.listdir(output_dir) ]))

                        with CallOnExit(lambda: FileSystem.RemoveFile(filenames_filename)):
                            zip_dm.stream.write("Executing...")
                            with zip_dm.stream.DoneManager( suffix='\n',
                                                          ) as this_dm:
                                command_line = '7za a -t7z "{output}" -mx{compression_level} -v{chunk_size}b -scsWIN -ssw{encryption_arg} -y "@{filenames_filename}"' \
                                                    .format( output=os.path.join(temp_dir, OFFSITE_BACKUP_FILENAME),
                                                             compression_level=compression_level,
                                                             chunk_size=250 * 1024 * 1024, # MB
                                                             encryption_arg=encryption_arg,
                                                             filenames_filename=filenames_filename,
                                                           )

                                this_dm.result = Process.Execute(command_line, this_dm.stream)
                                if this_dm.result != 0:
                                    return this_dm.result

                    # Swap the output_dir and the temp_dir
                    zip_dm.stream.write("Updating Original Content...")
                    with zip_dm.stream.DoneManager() as update_dm:
                        update_dm.stream.write("Removing...")
                        with update_dm.stream.DoneManager():
                            FileSystem.RemoveTree(output_dir)

                        update_dm.stream.write("Moving...")
                        with update_dm.stream.DoneManager():
                            shutil.move(temp_dir, output_dir)

            dm.stream.write("Writing Pending Data...")
            with dm.stream.DoneManager():
                pending_json_filename = _CreatePendingJsonFilename(json_filename)

                with open(pending_json_filename, 'w') as f:
                    json.dump( [ sfi.ToJson() for sfi in source_file_info ],
                               f,
                             )

            if auto_commit:
                dm.result = CommitOffsite(backup_name, dm.stream)
            else:
                dm.stream.write(textwrap.dedent(
                    """\
                    


                    ***** Pending data has been written, but will not be considered official until it is committed via a call to CommitOffsite. *****



                    """))
                        
            return dm.result

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( backup_name=CommandLine.EntryPoint.Parameter("Name used to uniquely identify the backup"),
                         backup_suffix=CommandLine.EntryPoint.Parameter("Suffix used when making a copy of the committed data; this can be helpful when archiving committed data"),
                       )
@CommandLine.Constraints( backup_name=CommandLine.StringTypeInfo(),
                          backup_suffix=CommandLine.StringTypeInfo(arity='?'),
                          output_stream=None,
                        )
def CommitOffsite( backup_name,
                   backup_suffix=None,
                   output_stream=sys.stdout,
                   preserve_ansi_escape_sequences=False,
                 ):
    """\
    Commits data previously generated by Offsite. This can be useful when
    additional steps must be taken (for example, upload) before a Backup can 
    be considered as successful.
    """

    with StreamDecorator.GenerateAnsiSequenceStream( output_stream,
                                                     preserve_ansi_escape_sequences=preserve_ansi_escape_sequences,
                                                   ) as output_stream:
        with output_stream.DoneManager( line_prefix='',
                                        prefix="\nResults: ",
                                        suffix='\n',
                                      ) as dm:
            json_filename = _CreateJsonFilename(backup_name)
            pending_json_filename = _CreatePendingJsonFilename(json_filename)

            if not os.path.isfile(pending_json_filename):
                dm.stream.write("ERROR: Pending data was not found.\n")
                dm.result = -1

                return dm.result

            FileSystem.RemoveFile(json_filename)
            shutil.move(pending_json_filename, json_filename)

            if backup_suffix:
                shutil.copy2(json_filename, "{}.{}".format(json_filename, backup_suffix))

            dm.stream.write("The pending data has been committed.\n")

            return dm.result

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( source_dir=CommandLine.EntryPoint.Parameter("Directory that contains all offsite backup output, each iteration stored in a subdirectory"),
                         encryption_password=CommandLine.EntryPoint.Parameter("Decrypt the data with this password"),
                         dir_substitution=CommandLine.EntryPoint.Parameter("Destination substitutions to perform if the data to be restored should be restored at a location different from when it was backed up"),
                         display_only=CommandLine.EntryPoint.Parameter("Display the operations that would be taken but does not perform them"),
                         ssd=CommandLine.EntryPoint.Parameter("Leverage optimizations available if the source drive is a Solid-State Drive (SSD)"), 
                       )
@CommandLine.Constraints( source_dir=CommandLine.DirectoryTypeInfo(),
                          encryption_password=CommandLine.StringTypeInfo(arity='?'),
                          dir_substitution=CommandLine.DictTypeInfo(require_exact_match=False, arity='?'),
                          output_stream=None,
                        )
def OffsiteRestore( source_dir,
                    encryption_password=None,
                    dir_substitution=None,
                    display_only=False,
                    ssd=False,
                    output_stream=sys.stdout,
                    preserve_ansi_escape_sequences=False,
                  ):
    """\
    Restores content created by previous Offsite backups.
    """

    dir_substitutions = dir_substitution; del dir_substitution

    with StreamDecorator.GenerateAnsiSequenceStream( output_stream,
                                                     preserve_ansi_escape_sequences=preserve_ansi_escape_sequences,
                                                   ) as output_stream:
        with output_stream.DoneManager( line_prefix='',
                                        prefix="\nResults: ",
                                        suffix='\n',
                                      ) as dm:
            # Get the dirs
            dirs = []

            for item in os.listdir(source_dir):
                fullpath = os.path.join(source_dir, item)
                if not os.path.isdir(fullpath):
                    continue

                dirs.append(fullpath)

            dirs = sorted(dirs)

            # Get the file data
            file_data = OrderedDict()
            hashed_filenames = {}

            dm.stream.write("Reading file data from {}...".format(inflect.no("directory", len(dirs))))
            with dm.stream.DoneManager( suffix='\n',
                                      ) as dir_dm:
                for index, dir in enumerate(dirs):
                    dir_dm.stream.write("'{}' ({} of {})...".format( dir,
                                                                     index + 1,
                                                                     len(dirs),
                                                                   ))
                    with dir_dm.stream.DoneManager() as this_dir_dm:
                        data_filename = os.path.join(dir, DATA_FILENAME)
                        if not os.path.isfile(data_filename):
                            # See if there is compressed data to decompress
                            for zipped_ext in [ '', ".001", ]:
                                potential_filename = os.path.join(dir, "{}{}".format(OFFSITE_BACKUP_FILENAME, zipped_ext))
                                if not os.path.isfile(potential_filename):
                                    continue

                                # Extract the data
                                temp_dir = dir + ".tmp"

                                FileSystem.RemoveTree(temp_dir)
                                FileSystem.MakeDirs(temp_dir)

                                this_dir_dm.stream.write("Decompressing data...")
                                with this_dir_dm.stream.DoneManager( suffix='\n',
                                                                   ) as decompress_dm:
                                    command_line = '7za e -y "-o{dir}"{password} "{input}"' \
                                                        .format( dir=temp_dir,
                                                                 input=potential_filename,
                                                                 password=' "-p{}"'.format(encryption_password) if encryption_password else '',
                                                               )
                                    decompress_dm.result = Process.Execute(command_line, decompress_dm.stream)
                                    if decompress_dm.result != 0:
                                        return decompress_dm.result

                                this_dir_dm.stream.write("Removing original data...")
                                with this_dir_dm.stream.DoneManager():
                                    FileSystem.RemoveTree(dir)

                                this_dir_dm.stream.write("Restoring compressed data...")
                                with this_dir_dm.stream.DoneManager():
                                    shutil.move(temp_dir, dir)

                                break
                            
                            if not os.path.isfile(data_filename):
                                this_dir_dm.stream.write("INFO: The file '{}' was not found in the directory '{}'.\n".format(DATA_FILENAME, dir))
                                this_dir_dm.result = 1

                                continue

                        try:
                            with open(data_filename) as f:
                                data = json.load(f)
                        except:
                            this_dir_dm.stream.write("ERROR: The data in '{}' is corrupt.\n".format(data_filename))
                            this_dir_dm.result = -1

                            continue

                        for file_info_index, file_info in enumerate(data):
                            operation = file_info["operation"]

                            if operation not in [ "add", "modify", "remove", ]:
                                this_dir_dm.stream.write("ERROR: The file info operation '{}' is not valid (Index: {}).\n".format(operation, file_info_index))
                                this_dir_dm.result = -1

                                continue

                            filename = file_info["filename"]

                            # Check if the data is in the expected state
                            if operation == "add":
                                if filename in file_data:
                                    this_dir_dm.stream.write("ERROR: Information for the file '{}' has already been added and cannot be added again (Index: {}).\n".format(filename, file_info_index))
                                    this_dir_dm.result = -1

                                    continue

                            elif operation in [ "modify", "remove", ]:
                                if filename not in file_data:
                                    this_dir_dm.stream.write("ERROR: Information for the file '{}' was not previously provided (Index: {}).\n".format(filename, file_info_index))
                                    this_dir_dm.result = -1

                                    continue

                            else:
                                assert False, operation

                            # Add or remove the data
                            if operation in [ "add", "modify", ]:
                                hash = file_info["hash"]

                                if hash not in hashed_filenames:
                                    hashed_filename = os.path.join(dir, hash)
                                    if not os.path.isfile(hashed_filename):
                                        this_dir_dm.stream.write("ERROR: Contents for the file '{}' were not found at '{}' (Index: {}).\n".format( filename,
                                                                                                                                                   hasehd_filename,
                                                                                                                                                   file_info_index,
                                                                                                                                                 ))
                                        this_dir_dm.result = -1

                                        continue

                                    hashed_filenames[hash] = hashed_filename

                                file_data[filename] = hashed_filenames[hash]

                            elif operation == "remove":
                                del file_data[filename]

                            else:
                                assert False, operation

            keys = sorted(six.iterkeys(file_data))

            # Perform destination substitutions (if necessary)
            if dir_substitutions:
                for key in keys:
                    for k, v in six.iteritems(dir_substitutions):
                        new_key = key.replace(k, v)

                        file_data[new_key] = file_data[key]
                        del file_data[key]

                keys = sorted(six.iterkeys(file_data))

            if display_only:
                dm.stream.write("{} to restore...\n\n".format(inflect.no("file", len(keys))))

                for key in keys:
                    dm.stream.write("  - {0:<100} <- {1}\n".format(key, file_data[key]))

                return dm.result

            with dm.stream.SingleLineDoneManager( "Copying Files...",
                                                ) as copy_dm:
                # ----------------------------------------------------------------------
                def Execute(task_index, on_status_update):
                    dest = keys[task_index]
                    source = file_data[dest]

                    on_status_update(FileSystem.GetSizeDisplay(os.path.getsize(source)))

                    dest_dir = os.path.dirname(dest)
                    if not os.path.isdir(dest_dir):
                        try:
                            os.makedirs(dest_dir)
                        except:
                            # This can happen when attempting to create the dir from
                            # multiple threads simultaneously. If the error is something
                            # else, the copy statement below will raise an exception.
                            pass 

                    shutil.copy2(source, dest)

                # ----------------------------------------------------------------------

                copy_dm.result = TaskPool.Execute( [ TaskPool.Task( "'{}' -> '{}'".format(file_data[key], key),
                                                                    Execute,
                                                                  )
                                                     for key in keys
                                                   ],
                                                   optional_output_stream=copy_dm.stream,
                                                   progress_bar=True,
                                                   num_concurrent_tasks=None if ssd else 1,
                                                 )
                if copy_dm.result != 0:
                    return copy_dm.result

            return dm.result

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
class _FileInfo(object):
    # ----------------------------------------------------------------------
    @classmethod
    def FromJson(cls, item):
        return cls( item["name"],
                    item["size"],
                    item["last_modified"],
                    item["hash"],
                  )

    # ----------------------------------------------------------------------
    def __init__( self,
                  name,
                  size,
                  last_modified,
                  hash=None,
                ):
        self.Name                           = name
        self.Size                           = size
        self.LastModified                   = last_modified
        self.Hash                           = hash

    # ----------------------------------------------------------------------
    def ToJson(self):
        return { "name" : self.Name,
                 "size" : self.Size,
                 "last_modified" : self.LastModified,
                 "hash" : self.Hash,
               }

    # ----------------------------------------------------------------------
    def __repr__(self):
        return CommonEnvironment.ObjectReprImpl(self)

    # ----------------------------------------------------------------------
    def __hash__(self):
        return hash(( self.Name, self.Size, self.LastModified, self.Hash, ))

    # ----------------------------------------------------------------------
    def AreEqual(self, other, compare_hashes=True):
        return ( self.Size == other.Size and
                 abs(self.LastModified - other.LastModified) <= 0.00001 and
                 (not compare_hashes or self.Hash == other.Hash)
               )

    # ----------------------------------------------------------------------
    def __eq__(self, other):
        return self.AreEqual(other)

    # ----------------------------------------------------------------------
    def __ne__(self, other):
        return not self.__eq__(other)
    
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _CreateJsonFilename(backup_name):
    return CurrentShell.CreateDataFilename("{}.backup".format(backup_name))

# ----------------------------------------------------------------------
def _CreatePendingJsonFilename(json_filename):
    return json_filename + ".pending"

# ----------------------------------------------------------------------
def _GetFileInfo( desc,
                  inputs,
                  includes,
                  excludes,
                  traverse_includes,
                  traverse_excludes,
                  simple_compare,
                  output_stream,
                  is_ssd,
                  no_status,
                  hash_block_size=None,
                ):
    """Returns file info objects for all files in the specified inputs"""

    hash_block_size = hash_block_size or 65536

    output_stream.write("Processing '{}'...".format(desc))
    with output_stream.DoneManager() as dm:
        input_files = []

        dm.stream.write("Processing Content...")
        with dm.stream.DoneManager( done_suffix=lambda: "{} found".format(inflect.no("file", len(input_files))),
                                  ) as this_dm:
            input_dirs = []

            for i in inputs:
                if os.path.isfile(i):
                    input_files.append(i)
                elif os.path.isdir(i):
                    input_dirs.append(i)
                else:
                    raise CommandLine.UsageException("'{}' is not a valid file or directory".format(i))

            if input_dirs:
                this_dm.stream.write("Processing Directories...")
                with this_dm.stream.DoneManager() as dir_dm:
                    for index, input_dir in enumerate(input_dirs):
                        dir_dm.stream.write("'{}' ({} of {})...".format( input_dir,
                                                                         index + 1,
                                                                         len(input_dirs),
                                                                       ))
                        prev_len_input_files = len(input_files)

                        with dir_dm.stream.DoneManager( done_suffix=lambda: "{} found".format(inflect.no("file", len(input_files) - prev_len_input_files)),
                                                      ):
                            input_files += FileSystem.WalkFiles( input_dir,
                                                                 traverse_include_dir_names=traverse_includes,
                                                                 traverse_exclude_dir_names=traverse_excludes,
                                                                 include_generated=True,
                                                               )
        if includes or excludes:
            # ----------------------------------------------------------------------
            def ToRegexes(items):
                results = []

                for item in items:
                    try:
                        results.append(re.compile("^.*{sep}{expr}{sep}.*$".format( sep=re.escape(os.path.sep),
                                                                                   expr=item,
                                                                                 )))    
                    except:
                        raise CommandLine.UsageException("'{}' is not a valid regular expression".format(item))

                return results

            # ----------------------------------------------------------------------
             
            dm.stream.write("Filtering Files...")
            with dm.stream.DoneManager( lambda: "{} to process".format(inflect.no("file", len(input_files))),
                                      ):
                if includes:
                    include_regexes = ToRegexes(includes)
                    include_checker_func = lambda input_file: any(include_regex for include_regex in include_regexes if include_regex.match(input_file))
                else:
                    include_checker_func = lambda input_file: True

                if excludes:
                    exclude_regexes = ToRegexes(excludes)
                    exclude_checker_func = lambda input_file: any(exclude_regex for exclude_regex in exclude_regexes if exclude_regex.match(input_file))
                else:
                    exclude_checker_func = lambda input_file: False

                valid_files = []

                for input_file in input_files:
                    if not exclude_checker_func(input_file) and include_checker_func(input_file):
                        valid_files.append(input_file)

                input_files[:] = valid_files

        file_info = []

        if input_files:
            with dm.stream.SingleLineDoneManager( "Calculating Info...",
                                                ) as this_dm:
                # ----------------------------------------------------------------------
                def CreateFileInfo(filename):
                    return _FileInfo( filename,
                                      os.path.getsize(filename),
                                      os.path.getmtime(filename),
                                    )

                # ----------------------------------------------------------------------
                def CreateFileInfoWithHash(filename, info=None):
                    if info is None:
                        info = CreateFileInfo(filename)

                    sha = hashlib.sha256()

                    with open(filename, 'rb') as f:
                        while True:
                            block = f.read(hash_block_size)
                            if not block:
                                break

                            sha.update(block)

                    info.Hash = sha.hexdigest()

                    return info

                # ----------------------------------------------------------------------

                if is_ssd:
                    # If we are working with a SSD drive, read and calculate within the same
                    # thread. Note however, that multiple files will be processed concurrently.

                    # ----------------------------------------------------------------------
                    def Cleanup():
                        pass
                    
                    # ----------------------------------------------------------------------

                else:
                    # Read and calculate in different threads, but only process one file at a 
                    # time.
                    block_queue = six.moves.queue.Queue(100)
                    quit_event = threading.Event()

                    nonlocals = CommonEnvironment.Nonlocals( sha=None,
                                                           )

                    # ----------------------------------------------------------------------
                    def WorkerProc():
                        while True:
                            if quit_event.is_set():
                                break

                            try:
                                block = block_queue.get(True, 0.25) # Seconds

                                assert nonlocals.sha
                                nonlocals.sha.update(block)

                                block_queue.task_done()

                            except six.moves.queue.Empty:
                                pass

                    # ----------------------------------------------------------------------

                    worker_thread = threading.Thread(target=WorkerProc)
                    worker_thread.start()

                    original_create_file_info_with_hash_func = CreateFileInfoWithHash

                    # ----------------------------------------------------------------------
                    def Cleanup():
                        quit_event.set()
                        worker_thread.join()

                    # ----------------------------------------------------------------------
                    def CreateFileInfoWithHash(filename):
                        info = CreateFileInfo(filename)

                        # Don't calculate the hash in a different thread if the file size is small
                        if info.Size <= hash_block_size * 5:
                            return original_create_file_info_with_hash_func(filename, info=info)

                        nonlocals.sha = hashlib.sha256()

                        with open(filename, 'rb') as f:
                            while True:
                                block = f.read(hash_block_size)
                                if not block:
                                    break

                                block_queue.put(block)

                        block_queue.join()

                        info.Hash = nonlocals.sha.hexdigest()

                        return info

                    # ----------------------------------------------------------------------

                with CallOnExit(Cleanup):
                    create_func = CreateFileInfo if simple_compare else CreateFileInfoWithHash

                    # ----------------------------------------------------------------------
                    def CalculateHash(filename, on_status_update):
                        if not no_status:
                            on_status_update(FileSystem.GetSizeDisplay(os.path.getsize(filename)))

                        return create_func(filename)

                    # ----------------------------------------------------------------------

                    file_info += TaskPool.Transform( input_files,
                                                     CalculateHash,
                                                     this_dm.stream,
                                                     num_concurrent_tasks=None if is_ssd else 1,
                                                     name_functor=lambda index, item: item,
                                                   )

        return file_info

# ----------------------------------------------------------------------
def _CreateWork( source_file_info,
                 dest_file_info,
                 optional_local_destination_dir,
                 simple_compare,
                 output_stream,
                 verbose,
               ):
    """\
    Returns a dict in the following format:

        - Added files will have a key that is _FileInfo (source) and value that is the destination filename
        - Modified files will have a key that is _FileInfo (source) and value that is _FileInfo (destination)
        - Removed files will have a key that is None and a value that is a list of _FileInfo objects (destination)
    """

    results = OrderedDict()

    output_stream.write("Processing File Information...")
    with output_stream.DoneManager( suffix='\n',
                                  ) as dm:
        verbose_stream = StreamDecorator(dm.stream if verbose else None, "INFO: ")

        source_map = { sfi.Name : sfi for sfi in source_file_info }
        dest_map = { dfi.Name : dfi for dfi in dest_file_info }

        # Create functions that will map to and from source/dest filenames

        if optional_local_destination_dir is None:
            # ----------------------------------------------------------------------
            def ToDest(filename):
                return filename

            # ----------------------------------------------------------------------
            def FromDest(filename):
                return filename

            # ----------------------------------------------------------------------
        
        else:    
            # ----------------------------------------------------------------------
            def IsMultiDrive():
                drive = None

                for file_info in source_file_info:
                    this_drive = os.path.splitdrive(file_info.Name)[0]
                    if this_drive != drive:
                        if drive is None:
                            drive = this_drive
                        else:
                            return True

                return False

            # ----------------------------------------------------------------------

            if IsMultiDrive():
                # ----------------------------------------------------------------------
                def ToDest(filename):
                    drive, suffix = os.path.splitdrive(filename)
                    drive = drive.replace(':', '_')

                    suffix = FileSystem.RemoveInitialSep(suffix)

                    return os.path.join(optional_local_destination_dir, drive, suffix)

                # ----------------------------------------------------------------------
                def FromDest(filename):
                    assert filename.startswith(optional_local_destination_dir), (filename, optional_local_destination_dir)
                    filename = filename[len(optional_local_destination_dir):]
                    filename = FileSystem.RemoveInitialSep(filename)

                    parts = filename.split(os.path.sep)
                    parts[0] = parts[0].replace('_', ':')

                    return os.path.join(*parts)

                # ----------------------------------------------------------------------

            else:
                if len(source_file_info) == 1:
                    common_path = os.path.dirname(source_file_info[0].Name)
                else:
                    common_path = FileSystem.GetCommonPath(*source_map.keys())
                    assert common_path

                common_path = FileSystem.AddTrailingSep(common_path)

                # ----------------------------------------------------------------------
                def ToDest(filename):
                    assert filename.startswith(common_path), (filename, common_path)
                    filename = filename[len(common_path):]
                    filename = os.path.join(optional_local_destination_dir, filename)

                    return filename

                # ----------------------------------------------------------------------
                def FromDest(filename):
                    assert filename.startswith(optional_local_destination_dir), (filename, optional_local_destination_dir)
                    filename = filename[len(optional_local_destination_dir):]
                    filename = FileSystem.RemoveInitialSep(filename)

                    return os.path.join(common_path, filename)

                # ----------------------------------------------------------------------

        # Process the files
        added = 0
        modified = 0
        removed = 0
        matched = 0

        for sfi in six.itervalues(source_map):
            dest_filename = ToDest(sfi.Name)
            
            if dest_filename not in dest_map:
                verbose_stream.write("[Add] '{}' does not exist.\n".format(sfi.Name))

                results[sfi] = dest_filename
                added += 1
            elif sfi.AreEqual(dest_map[dest_filename], compare_hashes=not simple_compare):
                matched += 1
            else:
                verbose_stream.write("[Modify] '{}' has changed.\n".format(sfi.Name))

                results[sfi] = dest_map[dest_filename]
                modified += 1

        for dfi in six.itervalues(dest_map):
            source_filename = FromDest(dfi.Name)

            if source_filename not in source_map:
                verbose_stream.write("[Remove] '{}' will be removed.\n".format(dfi.Name))

                results.setdefault(None, []).append(dfi)
                removed += 1

        total = added + modified + removed + matched
        if total == 0:
            percentage_func = lambda value: 0.0
        else:
            percentage_func = lambda value: (float(value) / total) * 100

        dm.stream.write(textwrap.dedent(
            """\
            - {add} to add ({add_percent:.04f}%)
            - {modify} to modify ({modify_percent:.04f}%)
            - {remove} to remove ({remove_percent:.04f}%)
            - {match} matched ({match_percent:.04f}%)
            """).format( add=inflect.no("file", added),
                         add_percent=percentage_func(added),
                         modify=inflect.no("file", modified),
                         modify_percent=percentage_func(modified),
                         remove=inflect.no("file", removed),
                         remove_percent=percentage_func(removed),
                         match=inflect.no("file", matched),
                         match_percent=percentage_func(matched),
                       ))

    return results

# ----------------------------------------------------------------------
def _Display(work, output_stream, show_dest=False):
    added = OrderedDict()
    modified = OrderedDict()
    removed = []

    for sfi, dfi in six.iteritems(work):
        if sfi is None:
            continue

        if isinstance(dfi, six.string_types):
            added[sfi.Name] = dfi
        else:
            modified[sfi.Name] = dfi.Name

    removed = [ item.Name for item in work.get(None, []) ]

    if show_dest:
        template = "    {source:<100} -> {dest}\n"
    else:
        template = "    {source}\n"

    # ----------------------------------------------------------------------
    def WriteHeader(header):
        output_stream.write(textwrap.dedent(
            """\
            {}
            {}
            """).format(header, '-' * len(header)))

    # ----------------------------------------------------------------------

    # Added
    WriteHeader("Files to Add ({})".format(len(added)))

    for source, dest in six.iteritems(added):
        output_stream.write(template.format( source=source,
                                             dest=dest,
                                           ))

    output_stream.write('\n')

    # Modified
    WriteHeader("Files to Modify ({})".format(len(modified)))

    for source, dest in six.iteritems(modified):
        output_stream.write(template.format( source=source,
                                             dest=dest,
                                           ))

    output_stream.write('\n')

    # Removed
    WriteHeader("Files to Remove ({})".format(len(removed)))

    for item in removed:
        output_stream.write("    {}\n".format(item))

    output_stream.write('\n')

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try: sys.exit(CommandLine.Main())
    except KeyboardInterrupt: pass
