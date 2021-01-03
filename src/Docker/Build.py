# ----------------------------------------------------------------------
# |  
# |  Build.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-06-25 20:12:13
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018-21.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
# """Builds the Common_EnvironmentEx Docker image"""

import os
import sys

import CommonEnvironment
from CommonEnvironment import BuildImpl
from CommonEnvironment.BuildImpl import DockerBuildImpl
from CommonEnvironment import CommandLine

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

APPLICATION_NAME                            = "Docker_CommonEnvironmentEx"

Build                                       = DockerBuildImpl.CreateRepositoryBuildFunc( "Common_EnvironmentEx",
                                                                                         os.path.join(_script_dir, "..", ".."),
                                                                                         "dbrownell",
                                                                                         "common_environmentex",
                                                                                         "dbrownell/common_environment:base",
                                                                                         "David Brownell <db@DavidBrownell.com>",
                                                                                         repository_source_excludes=[],
                                                                                         repository_activation_configurations=[ "python36",
                                                                                                                                "python27",
                                                                                                                              ],
                                                                                       )

Clean                                       = DockerBuildImpl.CreateRepositoryCleanFunc()


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try:
        sys.exit(BuildImpl.Main(BuildImpl.Configuration( name=APPLICATION_NAME,
                                                         requires_output_dir=False,
                                                       )))
    except KeyboardInterrupt:
        pass
