# ----------------------------------------------------------------------
# |  
# |  InvokeBackup.template.py
# |      Script that invokes backup functionality for common scenarios on Windows
# |      machines.
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-09-21 17:23:00
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
import os
import sys

from CommonEnvironment import CommandLine
from CommonEnvironment import Process
from CommonEnvironment.StreamDecorator import StreamDecorator

# ----------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

StreamDecorator.InitAnsiSequenceStreams()

# ----------------------------------------------------------------------
# User account names to backup
USERS_TO_BACKUP                             = [ "brownell"
                                              ]

ACCOUNT_DIRECTORIES_TO_BACKUP               = [ "Desktop",
                                                "Documents",
                                              ]

# Directories to backup
ADDITIONAL_DIRECTORIES_TO_BACKUP            = [
                                              ]

# Individual files to backup
ADDITIONAL_FILES_TO_BACKUP                  = [
                                              ]

OUTPUT_DIR                                  = os.path.join("Z:\\", "Backup", os.getenv("COMPUTERNAME"))

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.Constraints( output_stream=None,
                        )
def EntryPoint( print_command_line=False,
                no_status=False,
                force=False,
                output_stream=sys.stdout,
                verbose=False,
              ):
    inputs = []

    user_root = os.path.dirname(os.getenv("USERPROFILE"))

    for user in USERS_TO_BACKUP:
        inputs += [ os.path.join(user_root, user, folder) for folder in ACCOUNT_DIRECTORIES_TO_BACKUP ]

    inputs += ADDITIONAL_DIRECTORIES_TO_BACKUP
    inputs += ADDITIONAL_FILES_TO_BACKUP

    for input in inputs:
        if not os.path.exists(input):
            raise Exception("'{}' is not a valid file or directory".format(input))

    backup_script = os.path.join( os.getenv("DEVELOPMENT_ENVIRONMENT_REPOSITORY"),
                                  "src",
                                  "Backup",
                                  "Backup.py",
                                )
    assert os.path.isfile(backup_script), backup_script

    command_line = 'python "{script}" Mirror "{output_dir}" {input}{no_status}{force}{verbose} /preserve_ansi_escape_sequences' \
                        .format( script=backup_script,
                                 output_dir=OUTPUT_DIR,
                                 input=' '.join([ '"/input={}"'.format(input) for input in inputs ]),
                                 no_status='' if not no_status else " /no_status",
                                 force='' if not force else " /force",
                                 verbose='' if not verbose else " /verbose",
                               )

    if print_command_line:
        output_stream.write(command_line)
        return

    return Process.Execute(command_line, output_stream)

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try: sys.exit(CommandLine.Main())
    except KeyboardInterrupt: pass