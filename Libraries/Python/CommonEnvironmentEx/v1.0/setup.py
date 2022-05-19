# ----------------------------------------------------------------------
# |
# |  setup.py
# |
# |  David Brownell <db@DavidBrownell.com>
# |      2018-08-15 1:28:37
# |
# ----------------------------------------------------------------------
# |
# |  Copyright David Brownell 2018-22.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |
# ----------------------------------------------------------------------
from setuptools import setup, find_packages

# Do the setup
setup(
    name="CommonEnvironmentEx",
    version="0.0.2",
    packages=find_packages(),
    install_requires=[
        "CommonEnvironment >= 1.0.7",
    ],
    author="David Brownell",
    author_email="pypi@DavidBrownell.com",
    description="Foundational Python libraries used across a variety of different projects and environments.",
    long_description=open("Readme.rst").read(),
    license="Boost Software License",
    keywords=[
        "Python",
        "Library",
        "Development",
        "Foundation",
    ],
    url="https://github.com/davidbrownell/Common_EnvironmentEx",
    project_urls={
        "Bug Tracker" : "https://github.com/davidbrownell/Common_EnvironmentEx/issues",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Boost Software License 1.0 (BSL-1.0)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
