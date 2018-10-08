# ----------------------------------------------------------------------
# |  
# |  GeneratorFactory.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-07-06 13:23:00
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""Functional that helps when writing generators that support plugin frameworks"""

import imp
import inspect
import os
import sys

from collections import OrderedDict, namedtuple

import six

import CommonEnvironment
from CommonEnvironment.CallOnExit import CallOnExit
from CommonEnvironment import CommandLine
from CommonEnvironment import FileSystem
from CommonEnvironment.Interface import staticderived, override, DerivedProperty
from CommonEnvironment.StreamDecorator import StreamDecorator

from CommonEnvironment.TypeInfo.FundamentalTypes.FilenameTypeInfo import FilenameTypeInfo
from CommonEnvironment.TypeInfo.FundamentalTypes.All import CreateFromPythonType
from CommonEnvironment.TypeInfo.FundamentalTypes.Serialization.StringSerialization import StringSerialization

from CommonEnvironment.CompilerImpl import CodeGenerator as CodeGeneratorMod
from CommonEnvironment.CompilerImpl.InputProcessingMixin.AtomicInputProcessingMixin import AtomicInputProcessingMixin
from CommonEnvironment.CompilerImpl.InvocationQueryMixin.ConditionalInvocationQueryMixin import ConditionalInvocationQueryMixin
from CommonEnvironment.CompilerImpl.OutputMixin.MultipleOutputMixin import MultipleOutputMixin

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

CommandLineGenerate                         = CodeGeneratorMod.CommandLineGenerate
CommandLineClean                            = CodeGeneratorMod.CommandLineClean

# ----------------------------------------------------------------------
PluginInfo                                  = namedtuple( "PluginInfo",
                                                          [ "Mod",
                                                            "Plugin",
                                                          ],
                                                        )

# ----------------------------------------------------------------------
def CreatePluginMap( dynamic_plugin_architecture_environment_key,
                     plugins_dir,
                     output_stream,
                   ):
    """
    Loads all plugins specified by the given environment key or that
    reside in the provided plugins_dir.

    Returns dict: { "<plugin name>" : PluginInfo(), ... }
    """

    plugin_mods = []

    if os.getenv(dynamic_plugin_architecture_environment_key):
        assert os.getenv("DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL")

        sys.path.insert(0, os.getenv("DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL"))
        with CallOnExit(lambda: sys.path.pop(0)):
            from RepositoryBootstrap.SetupAndActivate import DynamicPluginArchitecture

        plugin_mods = list(DynamicPluginArchitecture.EnumeratePlugins(dynamic_plugin_architecture_environment_key))

    elif os.path.isdir(plugins_dir):
        for filename in FileSystem.WalkFiles( plugins_dir,
                                              include_file_base_names=[ lambda name: name.endswith("Plugin"), ],
                                              include_file_extensions=[ ".py", ],
                                              recurse=True,
                                            ):
            name = os.path.splitext(os.path.basename(filename))[0]
            plugin_mods.append(imp.load_source(name, filename))

    else:
        raise Exception("'{}' is not a valid environment variable and '{}' is not a valid directory".format( dynamic_plugin_architecture_environment_key,
                                                                                                             plugins_dir,
                                                                                                           ))

    plugins = OrderedDict()

    # ----------------------------------------------------------------------
    def GetPluginImpl(plugin_name, raise_on_error=True):
        if plugin_name not in plugins:
            if raise_on_error:
                raise Exception("'{}' is not a valid plugin".format(plugin_name))

            return None

        return plugins[plugin_name]

    # ----------------------------------------------------------------------

    warning_stream = StreamDecorator( output_stream,
                                      line_prefix="WARNING: ",
                                      suffix='\n',
                                    )

    with CallOnExit(lambda: warning_stream.flush(force_suffix=True)):
        if not plugin_mods:
            warning_stream.write("No plugins were found.\n")

        for plugin_mod in plugin_mods:
            obj = getattr(plugin_mod, "Plugin", None)
            if obj is None:
                warning_stream.write("The module defined at '{}' does not contain a 'Plugin' class.\n".format(plugin_mod.__file__))
                continue

            # Dynamically add the method GetPlugin to the plugin object; this will allow
            # a plugin to query for other plugins. This is a bit wonky, but it works with
            # the plugin architecture where most of the plugins are static objects.
            obj.GetPlugin = staticmethod(GetPluginImpl)

            obj = obj()

            if not obj.IsValidEnvironment():
                warning_stream.write("The plugin '{}' is not valid within this environment ({}).\n".format( obj.Name,
                                                                                                            plugin_mod.__file__,
                                                                                                          ))
                continue

            plugins[obj.Name] = PluginInfo(plugin_mod, obj)

    return plugins

# ----------------------------------------------------------------------
def CodeGeneratorFactory( plugin_map,
                          name,
                          description,
                          filename_validation_expression,
                          get_optional_metadata_func,                       # def Func() -> [ (k, v), ... ]
                          create_context_func,                              # def Func(metadata, plugin) -> context
                          invoke_func,                                      # def Func(invoke_reason, context, status_stream, verbose_stream, verbose) -> result code
                          is_supported_content_func=None,                   # def Func(item) -> bool
                          postprocess_context_func=None,                    # def Func(context, plugin) -> context
                          requires_output_name=True,
                        ):
    """Returns a CodeGenerator object"""

    assert get_optional_metadata_func
    assert create_context_func
    assert invoke_func
    
    calling_frame = inspect.stack()[1]
    calling_mod_filename = os.path.realpath(inspect.getmodule(calling_frame[0]).__file__)

    # ----------------------------------------------------------------------
    @staticderived
    class CodeGenerator( AtomicInputProcessingMixin,
                         ConditionalInvocationQueryMixin,
                         MultipleOutputMixin,
                         CodeGeneratorMod.CodeGenerator,
                       ):
        # ----------------------------------------------------------------------
        # |  
        # |  Public Properties
        # |  
        # ----------------------------------------------------------------------
        Name                                = DerivedProperty(name)
        Description                         = DerivedProperty(description)
        InputTypeInfo                       = DerivedProperty(FilenameTypeInfo(validation_expression=filename_validation_expression))

        OriginalModuleFilename              = calling_mod_filename
        RequiresOutputName                  = requires_output_name

        # ----------------------------------------------------------------------
        # |  
        # |  Public Methods
        # |  
        # ----------------------------------------------------------------------
        @staticmethod
        @override
        def IsSupportedContent(filename):
            return is_supported_content_func is None or is_supported_content_func(filename)

        # ----------------------------------------------------------------------
        # |  
        # |  Protected Methods
        # |  
        # ----------------------------------------------------------------------
        @classmethod
        @override
        def _GetOptionalMetadata(cls):
            return get_optional_metadata_func() + \
                   [ ( "plugin_settings", {} ),
                   ] + \
                   super(CodeGenerator, cls)._GetOptionalMetadata()

        # ----------------------------------------------------------------------
        @classmethod
        @override
        def _GetRequiredMetadataNames(cls):
            names = [ "plugin_name",
                    ]

            if cls.RequiresOutputName:
                names += [ "output_name", 
                         ]

            names += super(CodeGenerator, cls)._GetRequiredMetadataNames()

            return names

        # ----------------------------------------------------------------------
        @classmethod
        @override
        def _CreateContext(cls, metadata):
            if metadata["plugin_name"] not in plugin_map:
                raise CommandLine.UsageException("'{}' is not a valid plugin".format(metadata["plugin_name"]))

            plugin = plugin_map[metadata["plugin_name"]].Plugin

            # Ensure that all plugin settings are present and that they
            # are the expected type.
            custom_settings = OrderedDict([ (k, v) for k, v in plugin.GenerateCustomSettingsAndDefaults() ])

            plugin_settings = metadata["plugin_settings"]

            for k, v in six.iteritems(plugin_settings):
                if k not in custom_settings:
                    raise CommandLine.UsageException("'{}' is not a valid plugin setting".format(k))

                desired_type = type(custom_settings[k])

                if type(v) != desired_type:
                    assert isinstance(v, (str, UnicodeDecodeError)), (v, type(v))
                    plugin_settings[k] = StringSerialization(CreateFromPythonType(desired_type), v)

            for k, v in six.iteritems(custom_settings):
                if k not in plugin_settings:
                    plugin_settings[k] = v

            metadata["plugin_settings"] = plugin.PreprocessMetadata(plugin_settings)

            # Invoke custom functionality
            context = create_context_func(metadata, plugin)
            context = plugin.PreprocessContext(context)

            context["output_filenames"] = [ os.path.join(context["output_dir"], filename) for filename in plugin.GenerateOutputFilenames(context) ]

            context = plugin.PostprocessContext(context)

            if postprocess_context_func:
                context = postprocess_context_func(context, plugin)

            return super(CodeGenerator, cls)._CreateContext(context)

        # ----------------------------------------------------------------------
        @classmethod
        @override
        def _InvokeImpl( cls,
                         invoke_reason,
                         context,
                         status_stream, 
                         verbose_stream, 
                         verbose,
                       ):
            return invoke_func( cls,
                                invoke_reason,
                                context,
                                status_stream,
                                verbose_stream,
                                verbose,
                                plugin_map[context["plugin_name"]].Plugin,
                              )

        # ----------------------------------------------------------------------
        @classmethod
        @override
        def _GetAdditionalGeneratorItems(cls, context):
            # ----------------------------------------------------------------------
            def ProcessorGeneratorItem(item):
                if isinstance(item, six.string_types) and item in plugin_map:
                    return plugin_map[item].Plugin

                return item

            # ----------------------------------------------------------------------

            plugin = plugin_map[context["plugin_name"]].Plugin

            return [ cls,
                     cls.OriginalModuleFilename,
                     plugin,
                   ] + \
                   [ ProcessGeneratorItem(item) for item in plugin.GetAdditionalGeneratorItems(context) ] + \
                   super(CodeGenerator, cls)._GetAdditionalGeneratorItems(context)

    # ----------------------------------------------------------------------

    return CodeGenerator
