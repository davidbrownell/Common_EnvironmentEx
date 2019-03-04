# ----------------------------------------------------------------------
# |
# |  Jinja2CodeGenerator.py
# |
# |  David Brownell <db@DavidBrownell.com>
# |      2019-03-04 11:14:24
# |
# ----------------------------------------------------------------------
# |
# |  Copyright David Brownell 2019
# |  Distributed under the Boost Software License, Version 1.0. See
# |  accompanying file LICENSE_1_0.txt or copy at
# |  http://www.boost.org/LICENSE_1_0.txt.
# |
# ----------------------------------------------------------------------
"""Invokes the Jinja2 code generator"""

import hashlib
import importlib
import os
import sys
import textwrap

from collections import OrderedDict, namedtuple

from jinja2 import DebugUndefined, Environment, exceptions, FileSystemLoader, make_logging_undefined, StrictUndefined, Undefined
import six

import CommonEnvironment
from CommonEnvironment.CallOnExit import CallOnExit
from CommonEnvironment import CommandLine
from CommonEnvironment import FileSystem
from CommonEnvironment import Interface
from CommonEnvironment.StreamDecorator import StreamDecorator

from CommonEnvironment.CompilerImpl.CodeGenerator import CodeGenerator as CodeGeneratorBase, CommandLineGenerate, CommandLineClean
from CommonEnvironment.CompilerImpl.InputProcessingMixin.AtomicInputProcessingMixin import AtomicInputProcessingMixin
from CommonEnvironment.CompilerImpl.InvocationQueryMixin.ConditionalInvocationQueryMixin import ConditionalInvocationQueryMixin
from CommonEnvironment.CompilerImpl.OutputMixin.MultipleOutputMixin import MultipleOutputMixin

# ----------------------------------------------------------------------
_script_fullpath                            = CommonEnvironment.ThisFullpath()
_script_dir, _script_name                   = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
@Interface.staticderived
class CodeGenerator(
    AtomicInputProcessingMixin,
    ConditionalInvocationQueryMixin,
    MultipleOutputMixin,
    CodeGeneratorBase,
):
    # ----------------------------------------------------------------------
    # |  Types
    ContextCode                             = namedtuple("ContextCode", ["filename", "var_name"]) 

    # ----------------------------------------------------------------------
    # |  Properties
    Name                                                                    = Interface.DerivedProperty("Jinja2CodeGenerator")
    Description                                                             = Interface.DerivedProperty("Processes a Jinja2 template and produces output")
    InputTypeInfo                                                           = Interface.DerivedProperty(
        CommandLine.FilenameTypeInfo(
            validation_expression=".+?\.jinja2(?:\..+)?",
        ),
    )

    # ----------------------------------------------------------------------
    # |  Methods

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    @classmethod
    @Interface.override
    def _GetOptionalMetadata(cls):
        return [("jinja2_context", {}), ("jinja2_context_code", []), ("preserve_dir_structure", False), ("ignore_errors", False), ("debug", False)] + super(
            CodeGenerator,
            cls,
        )._GetOptionalMetadata()

    # ----------------------------------------------------------------------
    @classmethod
    @Interface.override
    def _GetRequiredMetadataNames(cls):
        return ["output_dir"] + super(CodeGenerator, cls)._GetRequiredMetadataNames()

    # ----------------------------------------------------------------------
    @classmethod
    @Interface.override
    def _CreateContext(cls, metadata):
        jinja2_context = {}

        # Load the custom context defined in code
        for context_code in metadata["jinja2_context_code"]:
            dirname, basename = os.path.split(contet_code)
            basename = os.path.splitext(basename)[0]

            sys.path.insert(0, dirname)
            with CallOnExit(lambda: sys.path.pop(0)):
                mod = importlib.import_module(basename)

            var = getattr(mod, context_code.var_name)
            del mod

            if isinstance(var, dict):
                for k, v in six.iteritems(var):
                    jinja2_context[k] = v
            else:
                jinja2_context[context_code.var_name] = var

        del metadata["jinja2_context_code"]

        # Load the custom context
        for k, v in six.iteritems(metadata["jinja2_context"]):
            if len(v) == 1:
                jinja2_context[k] = v[0]
            else:
                jinja2_context[k] = v

        metadata["jinja2_context"] = jinja2_context

        # Calculate the hashes of the input filenames. We will use this information
        # during comparison to determine if an input file has changed. It appears
        # that this value isn't used, but it is actually used when comparing the
        # context of two different invocations.
        
        # ----------------------------------------------------------------------
        def CalculateHash(input_filename):
            with open(input_filename, "rb") as f:
                return hashlib.sha256(f.read()).digest()

        # ----------------------------------------------------------------------

        metadata["hashes"] = [CalculateHash(input_filename) for input_filename in metadata["inputs"]]

        # Get the output filenames
        if not metadata["preserve_dir_structure"]:
            # ----------------------------------------------------------------------
            def GetBaseDir(input_filename):
                return ''

            # ----------------------------------------------------------------------

        else:
            if len(metadata["inputs"]) == 1:
                common_prefix = os.path.dirname(metadata["inputs"][0])
            else:
                common_prefix = FileSystem.GetCommonPath(*metadata["inputs"])

            # ----------------------------------------------------------------------
            def GetBaseDir(input_filename):
                return FileSystem.TrimPath(input_Filename, common_prefix)

            # ----------------------------------------------------------------------

        output_filenames = []

        for input_filename in metadata["inputs"]:
            output_filenames.append(
                os.path.join(
                    metadata["output_dir"],
                    GetBaseDir(input_filename),
                    '.'.join([part for part in os.path.basename(input_filename).split(".") if part != "jinja2"]),
                ),
            )

        metadata["output_filenames"] = output_filenames

        return super(CodeGenerator, cls)._CreateContext(metadata)

    # ----------------------------------------------------------------------
    @classmethod
    @Interface.override
    def _InvokeImpl(cls, invoke_reason, context, status_stream, verbose_stream, verbose):
        # ----------------------------------------------------------------------
        class RelativeFileSystemLoader(FileSystemLoader):
            
            # ----------------------------------------------------------------------
            def __init__(
                self,
                input_filename,
                searchpath=None,
                *args,
                **kwargs,
            ):
                super(RelativeFileSystemLoader, self).__init__(
                    searchpath=[os.path.dirname(input_filename)] + (searchpath or []),
                    *args,
                    **kwargs
                )

            # ----------------------------------------------------------------------
            def get_source(self, environment, template):
                method = super(RelativeFileSystemLoader, self).get_source

                try:
                    return method(environment, template)

                except exceptions.TemplateNotFound:
                    for searchpath in reversed(self.searchpath):
                        potential_template = os.path.normpath(os.path.join(searchpath, template).replace('/', os.path.sep))
                        if os.path.isfile(potential_template):
                            dirname, basename = os.path.split(potential_template)

                            self.searchpath.append(dirname)
                            return method(environment, template)

                    raise

        # ----------------------------------------------------------------------

        with status_stream.DoneManager(
            display=False,
        ) as dm:
            for index, (input_filename, output_filename) in enumerate(zip(
                context["inputs"],
                context["output_filenames"],
            )):
                status_stream.write(
                    "Processing '{}' ({} of {})...".format(
                        input_filename,
                        index + 1,
                        len(context["inputs"]),
                    ),
                )
                with dm.stream.DoneManager(
                    suppress_exceptions=True,
                ) as this_dm:
                    try:
                        # ----------------------------------------------------------------------
                        def ReadFileFilter(value):
                            potential_filename = os.path.join(os.path.dirname(input_filename), value)
                            if not os.path.isfile(potential_filename):
                                return "<< '{}' was not found >>".format(potential_filename)

                            with open(potential_filename) as f:
                                return f.read()

                        # ----------------------------------------------------------------------

                        loader = RelativeFileSystemLoader(input_filename)

                        if context["debug"]:
                            from jinja2 import meta

                            env = Environment(
                                loader=loader,
                            )

                            with open(input_filename) as f:
                                content = env.parse(f.read())
                                
                            this_dm.stream.write("Variables:\n{}\n".format("\n".join(["    - {}".format(var) for var in meta.find_undeclared_variables(content)])))

                            continue

                        if context["ignore_errors"]:
                            undef = Undefined
                        else:
                            undef = StrictUndefined

                        env = Environment(
                            trim_blocks=True,
                            lstrip_blocks=True,
                            loader=loader,
                            undefined=undef,
                        )

                        env.tests["valid_file"] = lambda value: os.path.isfile(os.path.dirname(input_filename), value)
                        env.filters["doubleslash"] = lambda value: value.replace("\\", "\\\\")

                        # Technically speaking, this isn't required as Jinja's import/include/extend functionality
                        # superseeds this functionality. However, it remains in the name of backwards compatibility.
                        env.filters["read_file"] = ReadFileFilter
                        
                        with open(input_filename) as f:
                            template = env.from_string(f.read())

                        try:
                            content = template.render(**context["jinja2_context"])
                        except exceptions.UndefinedError as ex:
                            this_dm.stream.write("ERROR: {}\n".format(str(ex)))
                            this_dm.result = -1

                            continue

                        with open(output_filename, "w") as f:
                            f.write(content)

                    except:
                        this_dm.result = -1
                        raise

            return dm.result


# ----------------------------------------------------------------------
@CommandLine.EntryPoint(
    context=CommandLine.EntryPoint.Parameter("Jinja2 context passed to the generator."),
    context_code=CommandLine.EntryPoint.Parameter("Jinja2 context defined in a python file. The argument should be in the form `<python_filename>:<var_name>`."),
    preserve_dir_structure=CommandLine.EntryPoint.Parameter("Preserve the input's directory structure when generating output."),
    ignore_errors=CommandLine.EntryPoint.Parameter("Populate context values not specified with an empty string rather than generating errors."),
    debug=CommandLine.EntryPoint.Parameter("Display context rather than generating output."),
)
@CommandLine.Constraints(
    output_dir=CommandLine.DirectoryTypeInfo(
        ensure_exists=False,
    ),
    input=CommandLine.FilenameTypeInfo(
        match_any=True,
        arity="+",
    ),
    context=CommandLine.DictTypeInfo(
        require_exact_match=False,
        arity="?",
    ),
    context_code=CommandLine.StringTypeInfo(
        validation_expression="^.+:.+$",
        arity="*",
    ),
    output_stream=None,
)
def Generate(
    output_dir,
    input,
    context=None,
    context_code=None,
    preserve_dir_structure=False,
    ignore_errors=False,
    debug=False,
    force=False,
    output_stream=sys.stdout,
    verbose=False,
):
    context_code = [CodeGenerator.ContextCode(*item.rsplit(":", 1)) for item in context_code]

    # Standard args
    args = [CodeGenerator, input]
    kwargs = {
        "output_stream": output_stream,
        "verbose": verbose,
    }

    # CodeGenerator args
    kwargs["output_dir"] = output_dir
    kwargs["force"] = force

    # Jinja2 args
    kwargs["jinja2_context"] = context
    kwargs["jinja2_context_code"] = context_code
    kwargs["preserve_dir_structure"] = preserve_dir_structure
    kwargs["ignore_errors"] = ignore_errors
    kwargs["debug"] = debug

    return CommandLineGenerate(*args, **kwargs)


# ----------------------------------------------------------------------
@CommandLine.EntryPoint
@CommandLine.Constraints(
    output_dir=CommandLine.DirectoryTypeInfo(),
    output_stream=None,
)
def Clean(
    output_dir,
    output_stream=sys.stdout,
):
    return CommandLineClean(output_dir, output_stream)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try:
        sys.exit(CommandLine.Main())
    except KeyboardInterrupt:
        pass
