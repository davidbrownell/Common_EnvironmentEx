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

from contextlib import contextmanager

from CommonEnvironment.CallOnExit import CallOnExit

# ----------------------------------------------------------------------
_script_fullpath = os.path.abspath(__file__) if "python" in sys.executable.lower() else sys.executable
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
def CreatePackageName(package, name, file):
    """\
    Creates a package name.

    Usage:
        __package__ = CreatePackageName(__package__, __name__, __file__)
    """

    if package:
        return package

    name_parts = name.split('.')
    if len(name_parts) > 1:
        # If the name already has dots, it means that the current module
        # is part of an actual package and we can use it directly.
        #
        # By default, the name includes the current filename. However, the
        # filename shouldn't be a part of the returned package name.
        name = '.'.join(name_parts[:-1])
        assert name in sys.modules, name

        return name

    # Ensure that relative imports work as expected by inserting the current dir
    # at the head of the path.
    original_dir = os.path.dirname(os.path.realpath(file))

    if original_dir in sys.path:
        sys.path.remove(original_dir)

    sys.path.insert(0, original_dir)
    with CallOnExit(lambda: sys.path.pop(0)):
        # Walk up all directories while there is an __init__ file
        name_parts = []

        directory = original_dir
        while os.path.isfile(os.path.join(directory, "__init__.py")):
            directory, name = os.path.split(directory)
            name_parts.append(name)

        if not name_parts:
            # If we didn't find any __init__ files, it means that this isn't a
            # file that is part of (any) package. Hoever, we still want to simulate
            # that it is part of a package so that relative imports work as 
            # expected.
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
                if name_part in sys.modules:
                    original_mod = sys.modules.pop(name_part)

                    # ----------------------------------------------------------------------
                    def Cleanup():
                        sys.modules[name_part] = original_mod

                    # ----------------------------------------------------------------------
                
                elif index != 0:
                    # ----------------------------------------------------------------------
                    def Cleanup():
                        sys.modules[fully_qualified_name] = sys.modules[name_part]
                        del sys.modules[name_part]

                    # ----------------------------------------------------------------------

                else:
                    # ----------------------------------------------------------------------
                    def Cleanup():
                        # Nothing to do here; keep the module
                        pass

                    # ----------------------------------------------------------------------

                with CallOnExit(Cleanup):
                    # Load this part
                    sys.path.insert(0, directory)
                    with CallOnExit(lambda: sys.path.pop(0)):
                        # Importing a module will add its name to sys.modules
                        mod = __import__(name_part)

            directory = os.path.join(directory, name_part)

        return fully_qualified_name

# ----------------------------------------------------------------------
@contextmanager
def ApplyRelativePackage():
    """\
    Temporarily applies a new package name.

    Example:
        with ApplyRelativePackage():
            from .Here.Is.A.Relative.Import import File
    """

    frame = inspect.stack()[2][0]           # 1 for ctor, 1 for contextmanager
    mod = inspect.getmodule(frame)

    original_value = frame.f_locals["__package__"]
    
    frame.f_locals["__package__"] = CreatePackageName(original_value, mod.__name__, mod.__file__)

    # ----------------------------------------------------------------------
    def Restore():
        frame.f_locals["__package__"] = original_value

    # ----------------------------------------------------------------------

    with CallOnExit(Restore):
        yield
