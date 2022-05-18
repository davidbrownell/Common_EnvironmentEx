# ----------------------------------------------------------------------
# |
# |  Build.py
# |
# |  David Brownell <db@DavidBrownell.com>
# |      2018-08-15 16:09:30
# |
# ----------------------------------------------------------------------
# |
# |  Copyright David Brownell 2018-22.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |
# ----------------------------------------------------------------------
"""Builds the CommonEnvironmentEx Python distribution"""

import os
import sys

import CommonEnvironment
from CommonEnvironment import BuildImpl
from CommonEnvironment.BuildImpl import PyPiBuildImpl

# ----------------------------------------------------------------------
_script_fullpath                            = CommonEnvironment.ThisFullpath()
_script_dir, _script_name                   = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

APPLICATION_NAME                            = "Python_CommonEnvironmentEx"

# ----------------------------------------------------------------------
Build                                       = PyPiBuildImpl.CreateBuildFunc(_script_dir)
Clean                                       = PyPiBuildImpl.CreateCleanFunc(_script_dir)
Deploy                                      = PyPiBuildImpl.CreateDeployFunc(_script_dir)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try:
        sys.exit(
            BuildImpl.Main(
                BuildImpl.Configuration(
                    name=APPLICATION_NAME,
                    requires_output_dir=False,
                ),
            ),
        )
    except KeyboardInterrupt:
        pass
