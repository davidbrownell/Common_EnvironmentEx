# ----------------------------------------------------------------------
# |  
# |  DenterHelper.py
# |  
# |  David Brownell <db@DavidBrownell.com>
# |      2018-07-09 13:42:27
# |  
# ----------------------------------------------------------------------
# |  
# |  Copyright David Brownell 2018-20.
# |  Distributed under the Boost Software License, Version 1.0.
# |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
# |  
# ----------------------------------------------------------------------
"""Contains the DenterHelper object"""

import os
import sys

from collections import deque

from antlr4.Token import Token, CommonToken

import CommonEnvironment

# ----------------------------------------------------------------------
_script_fullpath = CommonEnvironment.ThisFullpath()
_script_dir, _script_name = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
class DenterHelper(object):
    """\
    Helps with grammars that treat initial whitspace as significant. This code is based on
    Yuval Shavit's antlr-denter, which implements that functionality for Java-based lexers
    and parsers.
    """

    # ----------------------------------------------------------------------
    # |  
    # |  Public Methods
    # |  
    # ----------------------------------------------------------------------
    def __init__( self,
                  pull_token_func,
                  newline_token_id,
                  indent_token_id,
                  dedent_token_id,
                ):
        self.PullToken                      = pull_token_func
        self._newline_token_id              = newline_token_id
        self._indent_token_id               = indent_token_id
        self._dedent_token_id               = dedent_token_id

        self._indentation_stack             = []
        self._pending_tokens                = deque()
        self._processed_eof                 = False

    # ----------------------------------------------------------------------
    def nextToken(self):
        if not self._indentation_stack:
            # We are in a first-run scenario; prime the pump
            self._indentation_stack.append(0)

            # Get the first non-newline token
            while True:
                token = self.PullToken()
                
                if token.type != self._newline_token_id:
                    break

            if token.column > 0:
                self._pending_tokens.append(self._CloneToken(token, self._indent_token_id))
                self._indentation_stack.append(token.column)

            self._pending_tokens.append(token)

        if not self._pending_tokens:
            token = self.PullToken()

            if token.type == self._newline_token_id:
                self._ProcessNewline(token)
            else:
                self._pending_tokens.append(token)

        assert self._pending_tokens

        while True:
            token = self._pending_tokens.popleft()

            if token.type == Token.EOF and not self._processed_eof:
                self._ProcessEOF(token)
                continue

            return token

    # ----------------------------------------------------------------------
    # |  
    # |  Private Types
    # |  
    # ----------------------------------------------------------------------
    class InjectedToken(CommonToken):
        # ----------------------------------------------------------------------
        def __init__(self, original, name, type_):
            super(DenterHelper.InjectedToken, self).__init__( original.source,
                                                              type=type_,
                                                            )
            self.Text                       = name

    # ----------------------------------------------------------------------
    # |  
    # |  Private Methods
    # |  
    # ----------------------------------------------------------------------
    def _CloneToken(self, original, token_type):
        lookup = { self._newline_token_id : u"newline",
                   self._indent_token_id : u"indent",
                   self._dedent_token_id : u"dedent",
                 }

        assert token_type in lookup, token_type
        return self.InjectedToken(original, lookup[token_type], token_type)

    # ----------------------------------------------------------------------
    def _ProcessNewline(self, token):
        self._pending_tokens.append(self._CloneToken(token, self._newline_token_id))

        # Get the newline token that falls immediately before the next valid token
        newline_token = token
        while True:
            token = self.PullToken()
            if token.type != self._newline_token_id:
                break

            newline_token = token

        # Get the whitespace associated with the newline token
        s = newline_token.text

        start_index = 0
        while start_index < len(s) and s[start_index] in [ '\r', '\n', ]:
            start_index += 1

        if start_index != 0:
            s = s[start_index:]

        s = s.replace('\t', "    ")
        assert not s or s.isspace(), s

        whitespace = len(s)

        if whitespace != self._indentation_stack[-1]:
            if whitespace > self._indentation_stack[-1]:
                self._pending_tokens.append(self._CloneToken(token, self._indent_token_id))
                self._indentation_stack.append(whitespace)
            elif whitespace < self._indentation_stack[-1]:
                self._Unwind(token, whitespace)

        self._pending_tokens.append(token)

    # ----------------------------------------------------------------------
    def _ProcessEOF(self, token):
        # Insert a newline so that all dedent statements are newline terminated, just like any other statement.
        self._pending_tokens.append(self._CloneToken(token, self._newline_token_id))

        self._Unwind(token, 0)
        self._pending_tokens.append(token)

        assert not self._processed_eof
        self._processed_eof = True

    # ----------------------------------------------------------------------
    def _Unwind(self, token, desired_indentation_level):
        while True:
            assert self._indentation_stack

            if desired_indentation_level == self._indentation_stack[-1]:
                break

            self._pending_tokens += [ self._CloneToken(token, self._dedent_token_id),
                                      self._CloneToken(token, self._newline_token_id),
                                    ]

            if desired_indentation_level > self._indentation_stack[-1]:
                # This is the strange state where the next line is indented at a level
                # that is different from the expected level (see below for examples). This
                # is most likely a syntax error, but that will be handled by the grammar.
                #
                #   Example                 Indentation Level
                #   ----------------------  -----------------
                #   baseline                0
                #       foo                 4
                #           bar             8
                #     strange_level         2

                self._pending_tokens.append(self._CloneToken(token, self._indent_token_id))
                self._indentation_stack.append(desired_indentation_level)

                break

            self._indentation_stack.pop()
