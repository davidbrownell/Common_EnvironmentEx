# ----------------------------------------------------------------------
# |
# |  VsCodeCogger.py
# |
# |  David Brownell <db@DavidBrownell.com>
# |      2021-08-03 12:10:30
# |
# ----------------------------------------------------------------------
# |
# |  Copyright David Brownell 2021
# |  Distributed under the Boost Software License, Version 1.0. See
# |  accompanying file LICENSE_1_0.txt or copy at
# |  http://www.boost.org/LICENSE_1_0.txt.
# |
# ----------------------------------------------------------------------
"""Functionality to support the use of Cog in the generation and configuration of vscode's launch.json file"""

import importlib
import os
import sys
import textwrap

from collections import OrderedDict

import cog

import CommonEnvironment
from CommonEnvironment.CallOnExit import CallOnExit
from CommonEnvironment import FileSystem

# ----------------------------------------------------------------------
_script_fullpath                            = CommonEnvironment.ThisFullpath()
_script_dir, _script_name                   = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

_CONFIGURATIONS                             = OrderedDict(
    [
        (
            "Pytest",
            textwrap.dedent(
                """\
                {{
                    // {filename}
                    "name": "{name}",

                    "presentation": {{
                        "hidden": false,
                        "group": "{group}",
                    }},

                    "type": "python",
                    "request": "launch",
                    "justMyCode": false,
                    "console": "integratedTerminal",

                    "module": "pytest",

                    "args": [
                        "-o",
                        "python_files=*Test.py",
                        "--verbose",
                        "-W",
                        "ignore::DeprecationWarning:pywintypes",
                        "{basename}",

                        "--capture=no", // Do not capture stderr/stdout
                        "-vv",
                        // "-k", "test_name", // To run a specific test

                        // Insert custom program args here
                    ],

                    "cwd": "{dirname}",
                }},
                """,
            ),
        ),

        (
            "PyUnittest",
            textwrap.dedent(
                """\
                {{
                    // {filename}
                    "name": "{name}",

                    "type": "python",
                    "request": "launch",
                    "justMyCode": false,
                    "console": "integratedTerminal",

                    // "module": "<module name>",

                    "program": "{filename}",

                    "args": [
                        // Insert custom program args here
                    ]

                    "cwd": "{dirname}",
                }}
                """,
            ),
        ),
    ],
)


# ----------------------------------------------------------------------
def Execute():
    """\
    Uses cog (https://nedbatchelder.com/code/cog/) to update vscode's launch.json file.

    Example:

        Within 'launch.json':

            // [[[cog from CommonEnvironmentEx import VsCodeCogger; VsCodeCogger.Execute() ]]]
            // [[[end]]]

        From the command line:

            cog -r "<launch.json filename>"

    """

    # Get the files
    cog_filename = os.path.realpath(cog.inFile)
    assert os.path.isfile(cog_filename), cog_filename

    dirname = os.path.realpath(os.path.join(os.path.dirname(cog_filename), ".."))
    assert os.path.isdir(dirname), dirname

    filenames = FileSystem.WalkFiles(
        dirname,
        include_dir_names=lambda name: name.endswith("Tests") and name != "Tests",
        include_file_extensions=".py",
        exclude_file_names="__init__.py",
    )

    # Organize the files
    groups = OrderedDict()
    test_names_ctr = {}

    for filename in filenames:
        test_name = os.path.basename(filename)

        if test_name in test_names_ctr:
            test_names_ctr[test_name] += 1
        else:
            test_names_ctr[test_name] = 1

        assert filename.startswith(dirname), (filename, dirname)
        group = os.path.dirname(FileSystem.TrimPath(filename, dirname)).replace(os.path.sep, "/")

        groups.setdefault(group, []).append(filename)

    if not groups:
        return

    # Load the test parsers
    dynamic_test_parser_filename = os.getenv("DEVELOPMENT_ENVIRONMENT_TEST_PARSERS")
    assert os.path.isfile(dynamic_test_parser_filename), dynamic_test_parser_filename

    with open(dynamic_test_parser_filename) as f:
        test_parser_filenames = f.readlines()

    test_parsers = []

    for test_parser_filename in test_parser_filenames:
        test_parser_filename = test_parser_filename.strip()
        if not test_parser_filename:
            continue

        assert test_parser_filename, test_parser_filename
        assert os.path.isfile(test_parser_filename), test_parser_filename

        dirname, basename = os.path.split(test_parser_filename)
        basename = os.path.splitext(basename)[0]

        sys.path.insert(0, dirname)
        with CallOnExit(lambda: sys.path.pop(0)):
            mod = importlib.import_module(basename)

            parser = getattr(mod, "TestParser", None)
            assert parser is not None, test_parser_filename

            assert parser.Name in _CONFIGURATIONS, parser.Name

            test_parsers.append(parser)

    # Write the output
    cog.out(
        textwrap.dedent(
            """\

            // ----------------------------------------------------------------------
            // |
            // |  Cog Output
            // |
            // ----------------------------------------------------------------------

            // To regenerate this content:
            //
            //    cog -r "{}"

            // ----------------------------------------------------------------------
            // ----------------------------------------------------------------------
            // ----------------------------------------------------------------------

            """,
        ).format(cog.inFile.replace("\\", "\\\\")),
    )

    for group, filenames in groups.items():
        cog.out(
            textwrap.dedent(
                """\
                // ----------------------------------------------------------------------
                // |
                // |  {}
                // |
                // ----------------------------------------------------------------------
                """,
            ).format(group),
        )

        for filename in filenames:
            for parser in test_parsers:
                if parser.IsSupportedTestItem(filename):
                    dirname, basename = os.path.split(filename)

                    cog.out(
                        _CONFIGURATIONS[parser.Name].format(
                            filename=filename.replace(os.path.sep, "/"),
                            dirname=dirname.replace(os.path.sep, "/"),
                            basename=basename,
                            group=group,
                            name="{}{}".format(
                                os.path.splitext(basename)[0],
                                "" if test_names_ctr[basename] == 1 else " --- {}".format(group),
                            ),
                        ),
                    )

                    break

        cog.out("\n")
