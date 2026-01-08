#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

"""
Token defines the token type constants and provides
associated utility methods for the serialization parser.
"""


class Token:
    """Token type constants for Fantom serialization."""

    # Token Type IDs
    EOF = -1
    ID = 0
    BOOL_LITERAL = 1
    STR_LITERAL = 2
    INT_LITERAL = 3
    FLOAT_LITERAL = 4
    DECIMAL_LITERAL = 5
    DURATION_LITERAL = 6
    URI_LITERAL = 7
    NULL_LITERAL = 8
    DOT = 9              # .
    SEMICOLON = 10       # ;
    COMMA = 11           # ,
    COLON = 12           # :
    DOUBLE_COLON = 13    # ::
    LBRACE = 14          # {
    RBRACE = 15          # }
    LPAREN = 16          # (
    RPAREN = 17          # )
    LBRACKET = 18        # [
    RBRACKET = 19        # ]
    LRBRACKET = 20       # []
    EQ = 21              # =
    POUND = 22           # #
    QUESTION = 23        # ?
    AT = 24              # @
    DOLLAR = 25          # $
    AS = 26              # as
    USING = 27           # using
    JAVA_FFI = 28        # [java]

    @staticmethod
    def is_literal(type_):
        """Check if token type is a literal value."""
        return Token.BOOL_LITERAL <= type_ <= Token.NULL_LITERAL

    @staticmethod
    def keyword(type_):
        """Get keyword string for keyword tokens."""
        if Token.AS <= type_ <= Token.USING:
            return Token.to_string(type_)
        return None

    @staticmethod
    def to_string(type_):
        """Get string representation of token type."""
        names = {
            Token.EOF: "end of file",
            Token.ID: "identifier",
            Token.BOOL_LITERAL: "Bool literal",
            Token.STR_LITERAL: "String literal",
            Token.INT_LITERAL: "Int literal",
            Token.FLOAT_LITERAL: "Float literal",
            Token.DECIMAL_LITERAL: "Decimal literal",
            Token.DURATION_LITERAL: "Duration literal",
            Token.URI_LITERAL: "Uri literal",
            Token.NULL_LITERAL: "null",
            Token.DOT: ".",
            Token.SEMICOLON: ";",
            Token.COMMA: ",",
            Token.COLON: ":",
            Token.DOUBLE_COLON: "::",
            Token.LBRACE: "{",
            Token.RBRACE: "}",
            Token.LPAREN: "(",
            Token.RPAREN: ")",
            Token.LBRACKET: "[",
            Token.RBRACKET: "]",
            Token.LRBRACKET: "[]",
            Token.EQ: "=",
            Token.POUND: "#",
            Token.QUESTION: "?",
            Token.AT: "@",
            Token.DOLLAR: "$",
            Token.AS: "as",
            Token.USING: "using",
        }
        return names.get(type_, f"Token[{type_}]")
