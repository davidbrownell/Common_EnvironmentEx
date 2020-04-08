# ----------------------------------------------------------------------
# |
# |  glade.py
# |
# |  David Brownell <db@DavidBrownell.com>
# |      2020-04-06 18:57:47
# |
# ----------------------------------------------------------------------
# |
# |  Copyright David Brownell 2020
# |  Distributed under the Boost Software License, Version 1.0. See
# |  accompanying file LICENSE_1_0.txt or copy at
# |  http://www.boost.org/LICENSE_1_0.txt.
# |
# ----------------------------------------------------------------------
"""Launches wxGlade"""

import os
import sys

import wxglade

import CommonEnvironment
from CommonEnvironment import CommandLine
from CommonEnvironment import Process
from CommonEnvironment.StreamDecorator import StreamDecorator

# ----------------------------------------------------------------------
_script_fullpath                            = CommonEnvironment.ThisFullpath()
_script_dir, _script_name                   = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

@CommandLine.EntryPoint
@CommandLine.Constraints(
    arg=CommandLine.StringTypeInfo(
        arity="*",
    ),
    output_stream=None,
)
def EntryPoint(
    arg,
    output_stream=sys.stdout,
):
    args = arg; del arg

    with StreamDecorator(output_stream).DoneManager(
        line_prefix="",
        prefix="\nResults: ",
        suffix="\n",
    ) as dm:
        python_script = os.path.join(
            os.path.dirname(wxglade.__file__),
            "wxglade.py",
        )
        assert os.path.isfile(python_script), python_script

        dm.result = Process.Execute(
            'python "{}" {}'.format(
                python_script,
                ' '.join(['"{}"'.format(arg) for arg in args]),
            ),
            dm.stream,
        )

        return dm.result

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try:
        sys.exit(
            CommandLine.Main()
        )
    except KeyboardInterrupt:
        pass
