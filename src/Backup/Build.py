# ----------------------------------------------------------------------
# |  
# |  Build.py
# |      Builds Backup.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-09-21 18:43:00
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

import CommonEnvironment
from CommonEnvironment import BuildImpl
from CommonEnvironment import CommandLine
from CommonEnvironment import FileSystem
from CommonEnvironment import Process
from CommonEnvironment.Shell.All import CurrentShell
from CommonEnvironment.StreamDecorator import StreamDecorator

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.Constraints( output_dir=CommandLine.DirectoryTypeInfo(ensure_exists=False),
                          output_stream=None,
                        )
def Build( output_dir,
           output_stream=sys.stdout,
         ):
    paths = []
    includes = []
    excludes = []

    command_line = '"{script}" Compile "/input={input}" "/output_dir={output_dir}" /no_bundle /no_optimize {paths}{includes}{excludes}' \
                        .format( script=CurrentShell.CreateScriptName("CxFreezeCompiler"),
                                 input=os.path.join(_script_dir, "Backup.py"),
                                 output_dir=output_dir,
                                 paths='' if not paths else " {}".format(' '.join([ '"/path={}"'.format(path) for path in paths ])),
                                 includes='' if not includes else " {}".format(' '.join([ '"/include={}"'.format(include) for include in includes ])),
                                 excludes='' if not excludes else " {}".format(' '.join([ '"/exclude={}"'.format(exclude) for exclude in excludes ])),
                               )

    return Process.Execute(command_line, output_stream)

# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.Constraints( output_dir=CommandLine.DirectoryTypeInfo(ensure_exists=False),
                          output_stream=None,
                        )
def Clean( output_dir,
           output_stream=sys.stdout,
         ):
    if not os.path.isdir(output_dir):
        output_stream.write("'{}' does not exist.\n".format(output_dir))
        return 0

    output_stream.write("Removing '{}'...".format(output_dir))
    with StreamDecorator(output_stream).DoneManager():
        FileSystem.RemoveTree(output_dir)

    return 0

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try: sys.exit(BuildImpl.Main(BuildImpl.Configuration( "Backup",
                                                        )))
    except KeyboardInterrupt: pass
