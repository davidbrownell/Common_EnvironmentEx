# ----------------------------------------------------------------------
# |  
# |  Package.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-07-09 22:18:47
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""\
Python packages are notoriously fickle - using relative imports within a file may or
may not works as expected depending on the way in which the file was invoked. This
code ensures that relative imports always work as expected through some pretty
extreme manipulation of the packaging internals.
"""

import inspect
import os
import sys
import traceback

import six

from contextlib import contextmanager

from CommonEnvironment.CallOnExit import CallOnExit

# ----------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
@contextmanager
def InitRelativeImports():
    """\
    Temporarily applies a new package name to facilitate relative imports.

    Example:
        with InitRelativeImports():
            from .Here.Is.A.Relative.Import import AFile
    """

    frame = inspect.stack()[2][0]           # 1 for ctor, 1 for contextmanager
    mod = inspect.getmodule(frame)

    temporary_modules = {}

    # ----------------------------------------------------------------------
    def CreatePackageName():
        # Continue traversing parent dirs as long as there is an __init__.py file.
        name_parts = []

        directory = os.path.dirname(os.path.realpath(mod.__file__))
        while os.path.isfile(os.path.join(directory, "__init__.py")):
            directory, name = os.path.split(directory)
            name_parts.append(name)

        if not name_parts:
            # If we didn't find any __init__ files, it means that this isn't a file
            # that is part of a package. However, we still want to simulate package
            # behavior so that relative imports work as expected.
            if name == "__main__" or getattr(sys, "frozen", False):
                name = "___EntryPoint___"
            else:
                name = "___{}Lib___".format(name)

            assert name not in sys.modules
            sys.modules[name] = None

            return name

        # If here, we are looking at a file in a package. Ensure that the entire
        # package is included with fully qualified names.
        name_parts.reverse()

        for index, name_part in enumerate(name_parts):
            fully_qualified_name = '.'.join(name_parts[:index + 1])

            if fully_qualified_name not in sys.modules:
                # When we load this module, it will be loaded under 'name_part'.
                # Preserve the original module (if it exists).
                temporary_modules[name_part] = sys.modules.pop(name_part, None)
                
                sys.path.insert(0, directory)
                with CallOnExit(lambda: sys.path.pop(0)):
                    # This will add the module name to sys.modules
                    __import__(name_part)

                sys.modules[fully_qualified_name] = sys.modules[name_part]
                
            directory = os.path.join(directory, name_part)

        return fully_qualified_name

    # ----------------------------------------------------------------------
    
    original_package_name = frame.f_locals["__package__"]

    # ----------------------------------------------------------------------
    def Restore():
        frame.f_locals["__package__"] = original_package_name

        for k, v in six.iteritems(temporary_modules):
            if v is None:
                sys.modules.pop(k)
            else:
                sys.modules[k] = v

    # ----------------------------------------------------------------------

    frame.f_locals["__package__"] = CreatePackageName()

    with CallOnExit(Restore):
        yield


