# ----------------------------------------------------------------------
# |  
# |  ErrorListener.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-07-09 13:30:17
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018-22.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""Contains the ErrorListener object"""

import os
import sys

import antlr4

import CommonEnvironment

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
class ErrorListener(antlr4.error.ErrorListener.ErrorListener):

    # ----------------------------------------------------------------------
    # |  Public Types
    class AntlrException(Exception):

        # ----------------------------------------------------------------------
        @classmethod
        def Create( cls,
                    symbol,
                    msg=None,
                    source=None,
                  ):
            while not isinstance(symbol, antlr4.Token) and hasattr(symbol, "start"):
                symbol = symbol.start

            return cls( msg or str(symbol),
                        source or '',
                        symbol.line,
                        symbol.column + 1,
                      )

        # ----------------------------------------------------------------------
        def __init__( self,
                      msg,
                      source,
                      line,
                      column,
                    ):
            super(ErrorListener.AntlrException, self).__init__("{msg} ({source} [{line} <{column}>])".format(**locals()))

    # ----------------------------------------------------------------------
    # |  Public Methods
    def __init__(self, source, *args, **kwargs):
        super(ErrorListener, self).__init__(*args, **kwargs)
        self._source                        = source

    # ----------------------------------------------------------------------
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise ErrorListener.AntlrException( msg,
                                            self._source,
                                            line,
                                            column + 1,
                                          )
