# ----------------------------------------------------------------------
# |  
# |  Backup.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-09-19 21:31:45
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""Processes files for offsite or mirrored backup"""

import hashlib
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
from CommonEnvironment.StreamDecorator import StreamDecorator
from CommonEnvironment import TaskPool

# ----------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

inflect                                     = inflect_mod.engine()

StreamDecorator.InitAnsiSequenceStreams()

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( # TODO
                       )
@CommandLine.Constraints( output_stream=None,
                        )
def Offsite( output_stream=sys.stdout,
           ):
    raise Exception("TODO")

# ----------------------------------------------------------------------
@CommandLine.EntryPoint( # TODO
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
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
class _FileInfo(object):
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
                    original_create_file_info_with_hash_func = CreateFileInfoWithHash

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

                return os.path.join(optional_local_destination_dir, filename)

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
