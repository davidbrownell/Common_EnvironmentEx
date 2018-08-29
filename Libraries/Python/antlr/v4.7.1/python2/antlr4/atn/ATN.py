# Copyright (c) 2012-2017 The ANTLR Project. All rights reserved.
# Use of this file is governed by the BSD 3-clause license that
# can be found in the LICENSE.txt file in the project root.
#/
from antlr4.IntervalSet import IntervalSet
from antlr4.Token import Token


class ATN(object):

    INVALID_ALT_NUMBER = 0

    # Used for runtime deserialization of ATNs from strings#/
    def __init__(self, grammarType , maxTokenType ):
        # The type of the ATN.
        self.grammarType = grammarType
        # The maximum value for any symbol recognized by a transition in the ATN.
        self.maxTokenType = maxTokenType
        self.states = []
        # Each subrule/rule is a decision point and we must track them so we
        #  can go back later and build DFA predictors for them.  This includes
        #  all the rules, subrules, optional blocks, ()+, ()* etc...
        self.decisionToState = []
        # Maps from rule index to starting state number.
        self.ruleToStartState = []
        # Maps from rule index to stop state number.
        self.ruleToStopState = None
        self.modeNameToStartState = dict()
        # For lexer ATNs, this maps the rule index to the resulting token type.
        # For parser ATNs, this maps the rule index to the generated bypass token
        # type if the
        # {@link ATNDeserializationOptions#isGenerateRuleBypassTransitions}
        # deserialization option was specified; otherwise, this is {@code null}.
        self.ruleToTokenType = None
        # For lexer ATNs, this is an array of {@link LexerAction} objects which may
        # be referenced by action transitions in the ATN.
        self.lexerActions = None
        self.modeToStartState = []

    # Compute the set of valid tokens that can occur starting in state {@code s}.
    #  If {@code ctx} is null, the set of tokens will not include what can follow
    #  the rule surrounding {@code s}. In other words, the set will be
    #  restricted to tokens reachable staying within {@code s}'s rule.
    def nextTokensInContext(self, s, ctx):
        from antlr4.LL1Analyzer import LL1Analyzer
        anal = LL1Analyzer(self)
        return anal.LOOK(s, ctx=ctx)

    # Compute the set of valid tokens that can occur starting in {@code s} and
    # staying in same rule. {@link Token#EPSILON} is in set if we reach end of
    # rule.
    def nextTokensNoContext(self, s):
        if s.nextTokenWithinRule is not None:
            return s.nextTokenWithinRule
        s.nextTokenWithinRule = self.nextTokensInContext(s, None)
        s.nextTokenWithinRule.readonly = True
        return s.nextTokenWithinRule

    def nextTokens(self, s, ctx = None):
        if ctx==None:
            return self.nextTokensNoContext(s)
        else:
            return self.nextTokensInContext(s, ctx)

    def addState(self, state):
        if state is not None:
            state.atn = self
            state.stateNumber = len(self.states)
        self.states.append(state)

    def removeState(self, state):
        self.states[state.stateNumber] = None # just free mem, don't shift states in list

    def defineDecisionState(self, s):
        self.decisionToState.append(s)
        s.decision = len(self.decisionToState)-1
        return s.decision

    def getDecisionState(self, decision):
        if len(self.decisionToState)==0:
            return None
        else:
            return self.decisionToState[decision]

    # Computes the set of input symbols which could follow ATN state number
    # {@code stateNumber} in the specified full {@code context}. This method
    # considers the complete parser context, but does not evaluate semantic
    # predicates (i.e. all predicates encountered during the calculation are
    # assumed true). If a path in the ATN exists from the starting state to the
    # {@link RuleStopState} of the outermost context without matching any
    # symbols, {@link Token#EOF} is added to the returned set.
    #
    # <p>If {@code context} is {@code null}, it is treated as
    # {@link ParserRuleContext#EMPTY}.</p>
    #
    # @param stateNumber the ATN state number
    # @param context the full parse context
    # @return The set of potentially valid input symbols which could follow the
    # specified state in the specified context.
    # @throws IllegalArgumentException if the ATN does not contain a state with
    # number {@code stateNumber}
    #/
    def getExpectedTokens(self, stateNumber, ctx ):
        if stateNumber < 0 or stateNumber >= len(self.states):
            raise Exception("Invalid state number.")
        s = self.states[stateNumber]
        following = self.nextTokens(s)
        if Token.EPSILON not in following:
            return following
        expected = IntervalSet()
        expected.addSet(following)
        expected.removeOne(Token.EPSILON)
        while (ctx != None and ctx.invokingState >= 0 and Token.EPSILON in following):
            invokingState = self.states[ctx.invokingState]
            rt = invokingState.transitions[0]
            following = self.nextTokens(rt.followState)
            expected.addSet(following)
            expected.removeOne(Token.EPSILON)
            ctx = ctx.parentCtx
        if Token.EPSILON in following:
            expected.addOne(Token.EOF)
        return expected