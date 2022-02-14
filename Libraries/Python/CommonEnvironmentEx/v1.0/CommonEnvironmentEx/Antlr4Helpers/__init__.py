# ----------------------------------------------------------------------
# |  
# |  __init__.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-07-09 13:22:09
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018-22.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""Functionality useful when working with ANTLR4-generated code"""

import importlib
import os
import sys

import antlr4
import six

import CommonEnvironment
from CommonEnvironment.CallOnExit import CallOnExit
from CommonEnvironment.Constraints import Constraints
from CommonEnvironment.TypeInfo.FundamentalTypes.All import *

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
def GetLiteral(parser, name):
    """Returns the literal with the given name, removing any single quotes if they exist"""

    value = parser.literalNames[name]

    if value.startswith("'"):
        value = value[1:]

    if value.endswith("'"):
        value = value[:-1]

    return value

# ----------------------------------------------------------------------
@Constraints( antlr_generated_dir=DirectoryTypeInfo(),
              name_prefix=StringTypeInfo(),
              root_rule_name=StringTypeInfo(),
            )
def CreateParser( antlr_generated_dir,
                  name_prefix,
                  root_rule_name,
                ):
    from .ErrorListener import ErrorListener

    classes = {}
    mods = []

    sys.path.insert(0, antlr_generated_dir)
    with CallOnExit(lambda: sys.path.pop(0)):
        for suffix in [ "Lexer",
                        "Parser",
                        "Visitor",
                      ]:
            name = "{}{}".format(name_prefix, suffix)

            mod = importlib.import_module(name)
            assert mod

            cls = getattr(mod, name)
            assert cls

            classes[suffix] = cls
            mods.append(mod)

    # ----------------------------------------------------------------------
    class ParserBase(object):
        # ----------------------------------------------------------------------
        @staticmethod
        def Parse( visitor,
                   s,
                   source=None,
                 ):
            lexer = classes["Lexer"](antlr4.InputStream(s))
            tokens = antlr4.CommonTokenStream(lexer)

            tokens.fill()

            parser = classes["Parser"](tokens)
            parser.addErrorListener(ErrorListener(source or "<input>"))

            ast = getattr(parser, root_rule_name)()
            assert ast

            ast.accept(visitor)

        # ----------------------------------------------------------------------
        @classmethod
        def GetLiteral(cls, value):
            return GetLiteral(cls, value)

    # ----------------------------------------------------------------------
    class Meta(type):

        # ----------------------------------------------------------------------
        def __init__(cls, *args, **kwargs):
            # Augment the Parser class with the antlr4 objects
            for k, v in six.iteritems(classes):
                setattr(cls, k, v)

        # ----------------------------------------------------------------------
        def __getattr__(cls, name):
            # Most of the time, this will be called when referencing a token
            # by name to get its numerical value.
            return getattr(cls.Parser, name)

    # ----------------------------------------------------------------------
    class Parser(six.with_metaclass(Meta, ParserBase)):
        
        # ----------------------------------------------------------------------
        def __repr__(self):
            return CommonEnvironment.ObjectReprImpl(self)

    # ----------------------------------------------------------------------

    return Parser
