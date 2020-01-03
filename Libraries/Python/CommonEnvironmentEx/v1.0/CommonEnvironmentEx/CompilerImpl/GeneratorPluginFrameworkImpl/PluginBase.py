# ----------------------------------------------------------------------
# |  
# |  PluginBase.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-07-06 07:47:52
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018-20.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""Contains the PluginBase object"""

import datetime
import os
import sys
import textwrap

import CommonEnvironment
from CommonEnvironment.Interface import *

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
class PluginBase(Interface):
    """\
    Abstract base class for plugins that are used by concrete CodeGeneratorBase objects
    to perform generation activities.
    """

    # ----------------------------------------------------------------------
    # |  Public Properties
    @abstractproperty
    def Name(self):
        """The name used on the command line to specify the plugin"""
        raise Exception("Abstract property")

    @abstractproperty
    def Description(self):
        raise Exception("Abstract property")

    # ----------------------------------------------------------------------
    # |  Public Methods
    @staticmethod
    @abstractmethod
    def IsValidEnvironment():
        """Returns a bool that indicates if the plugin is valid for the current environment"""
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def GenerateCustomSettingsAndDefaults():
        # Generator that yield key/value pairs"""
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    @staticmethod
    @extensionmethod
    def PreprocessMetadata(metadata):
        """Opportunity to modify metadata before it is converted into context."""

        # No conversion by default
        return metadata

    # ----------------------------------------------------------------------
    @staticmethod
    @extensionmethod
    def PreprocessContext(context):
        """
        Opportunity to modify context before it is consumed. This is called BEFORE output_filenames
        has been populated.
        """

        # No conversion by default
        return context

    # ----------------------------------------------------------------------
    @staticmethod
    @extensionmethod
    def PostprocessContext(context):
        """
        Opportunity to modify context before it is consumed. This is called AFTER output_filenames
        has been populated.
        """

        # No conversion by default
        return context

    # ----------------------------------------------------------------------
    @staticmethod
    @extensionmethod
    def GetAdditionalGeneratorItems(context):
        """\
        Return a list of python files used in the generation process. These files
        will be used to determine when output should be regenerated based on changes
        in these files.
        """
        return []

    # ----------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def GenerateOutputFilenames(context):
        """Yields output filenames generated for the given context."""
        raise Exception("Abstract method")

    # ----------------------------------------------------------------------
    # |  Protected Methods
    @classmethod
    def _GenerateFileHeader( cls,
                             prefix='',
                             line_break="--------------------------------------------------------------------------------",
                             filename_parts=3,          # Number of filename parts to display
                             filename_prefix=None,
                             callstack_offset=0,
                           ):
        """Returns a string that should be included at the top of output files generated"""

        import inspect

        frame = inspect.stack()[callstack_offset + 1][0]
        filename = frame.f_code.co_filename

        filename = '/'.join(filename.split(os.path.sep)[-filename_parts:])

        return textwrap.dedent(
            """\
            {prefix}{line_break}
            {prefix}|
            {prefix}|  WARNING:
            {prefix}|  This file was generated; any local changes will be overwritten during
            {prefix}|  future invocations of the generator!
            {prefix}|
            {prefix}|  Generated by: {by}
            {prefix}|  Generated on: {now}
            {prefix}|
            {prefix}{line_break}
            """).format( prefix=prefix,
                         line_break=line_break,
                         by="{}{}".format(filename_prefix or '', filename),
                         now=str(datetime.datetime.now()),
                       )
