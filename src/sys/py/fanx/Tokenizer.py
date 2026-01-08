#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

"""
Tokenizer inputs a stream of Unicode characters and outputs tokens
for the Fantom serialization grammar.
"""

from decimal import Decimal as PyDecimal
from .Token import Token


class Tokenizer:
    """Tokenizer for Fantom serialization format."""

    # Character classification constants
    SPACE = 1
    ALPHA = 2
    DIGIT = 3

    # Character map for quick classification (ASCII only)
    _char_map = [0] * 128

    @classmethod
    def _init_char_map(cls):
        """Initialize the character classification map."""
        if cls._char_map[ord(' ')] != 0:
            return  # Already initialized

        # Space characters
        cls._char_map[ord(' ')] = cls.SPACE
        cls._char_map[ord('\n')] = cls.SPACE
        cls._char_map[ord('\r')] = cls.SPACE
        cls._char_map[ord('\t')] = cls.SPACE

        # Alpha characters
        for c in range(ord('a'), ord('z') + 1):
            cls._char_map[c] = cls.ALPHA
        for c in range(ord('A'), ord('Z') + 1):
            cls._char_map[c] = cls.ALPHA
        cls._char_map[ord('_')] = cls.ALPHA

        # Digit characters
        for c in range(ord('0'), ord('9') + 1):
            cls._char_map[c] = cls.DIGIT

    def __init__(self, in_stream):
        """Create tokenizer for input stream.

        Args:
            in_stream: InStream to read from
        """
        Tokenizer._init_char_map()

        self.in_stream = in_stream
        self.type = None       # Current token type
        self.val = None        # Token value (str for ID, literal value)
        self.line = 1          # Current line number
        self._undo = None      # Pushed-back token state

        # Character state
        self.cur = -1          # Current character
        self.curt = 0          # Current char type
        self.peek = -1         # Lookahead character
        self.peekt = 0         # Lookahead char type

        # Initialize with two characters
        self._consume()
        self._consume()

    def next(self):
        """Read next token and return its type.

        Returns:
            Token type constant
        """
        if self._undo is not None:
            self.type, self.val, self.line = self._undo
            self._undo = None
            return self.type

        self.val = None
        self.type = self._do_next()
        return self.type

    def _do_next(self):
        """Internal method to read next token."""
        while True:
            # Skip whitespace
            while self.curt == self.SPACE:
                self._consume()

            if self.cur < 0:
                return Token.EOF

            # Alpha means identifier
            if self.curt == self.ALPHA:
                return self._id()

            # Number
            if self.curt == self.DIGIT:
                return self._number(False)

            # Symbol
            c = self.cur

            if c == ord('+'):
                self._consume()
                return self._number(False)

            if c == ord('-'):
                self._consume()
                return self._number(True)

            if c == ord('"'):
                return self._str()

            if c == ord("'"):
                return self._ch()

            if c == ord('`'):
                return self._uri()

            if c == ord('('):
                self._consume()
                return Token.LPAREN

            if c == ord(')'):
                self._consume()
                return Token.RPAREN

            if c == ord(','):
                self._consume()
                return Token.COMMA

            if c == ord(';'):
                self._consume()
                return Token.SEMICOLON

            if c == ord('='):
                self._consume()
                return Token.EQ

            if c == ord('{'):
                self._consume()
                return Token.LBRACE

            if c == ord('}'):
                self._consume()
                return Token.RBRACE

            if c == ord('#'):
                self._consume()
                return Token.POUND

            if c == ord('?'):
                self._consume()
                return Token.QUESTION

            if c == ord('@'):
                self._consume()
                return Token.AT

            if c == ord('$'):
                self._consume()
                return Token.DOLLAR

            if c == ord('.'):
                if self.peekt == self.DIGIT:
                    return self._number(False)
                self._consume()
                return Token.DOT

            if c == ord('['):
                self._consume()
                if self.cur == ord(']'):
                    self._consume()
                    return Token.LRBRACKET
                return Token.LBRACKET

            if c == ord(']'):
                self._consume()
                return Token.RBRACKET

            if c == ord(':'):
                self._consume()
                if self.cur == ord(':'):
                    self._consume()
                    return Token.DOUBLE_COLON
                return Token.COLON

            if c == ord('*'):
                if self.peek == ord('*'):
                    self._skip_comment_sl()
                    continue

            if c == ord('/'):
                if self.peek == ord('/'):
                    self._skip_comment_sl()
                    continue
                if self.peek == ord('*'):
                    self._skip_comment_ml()
                    continue

            # Invalid character
            raise self._err(f"Unexpected symbol: {chr(c)} (0x{c:x})")

    def _id(self):
        """Parse identifier: alpha (alpha|digit)*"""
        s = []
        first = self.cur
        while (self.curt == Tokenizer.ALPHA or self.curt == Tokenizer.DIGIT) and self.cur > 0:
            s.append(chr(self.cur))
            self._consume()

        val = ''.join(s)

        # Check for keywords
        if first == ord('a'):
            if val == "as":
                return Token.AS
        elif first == ord('f'):
            if val == "false":
                self.val = False
                return Token.BOOL_LITERAL
        elif first == ord('n'):
            if val == "null":
                self.val = None
                return Token.NULL_LITERAL
        elif first == ord('t'):
            if val == "true":
                self.val = True
                return Token.BOOL_LITERAL
        elif first == ord('u'):
            if val == "using":
                return Token.USING

        self.val = val
        return Token.ID

    def _number(self, neg):
        """Parse number literal."""
        # Check for hex
        if self.cur == ord('0') and self.peek == ord('x'):
            return self._hex()

        # Read whole part
        s = None
        whole = 0
        whole_count = 0

        while self.curt == self.DIGIT:
            if s is not None:
                s.append(chr(self.cur))
            else:
                whole = whole * 10 + (self.cur - ord('0'))
                whole_count += 1
                if whole_count >= 18:
                    s = []
                    if neg:
                        s.append('-')
                    s.append(str(whole))
            self._consume()
            if self.cur == ord('_'):
                self._consume()

        # Fraction part
        floating = False
        if self.cur == ord('.') and self.peekt == self.DIGIT:
            floating = True
            if s is None:
                s = []
                if neg:
                    s.append('-')
                s.append(str(whole))
            s.append('.')
            self._consume()
            while self.curt == self.DIGIT:
                s.append(chr(self.cur))
                self._consume()
                if self.cur == ord('_'):
                    self._consume()

        # Exponent
        if self.cur == ord('e') or self.cur == ord('E'):
            floating = True
            if s is None:
                s = []
                if neg:
                    s.append('-')
                s.append(str(whole))
            s.append('e')
            self._consume()
            if self.cur == ord('-') or self.cur == ord('+'):
                s.append(chr(self.cur))
                self._consume()
            if self.curt != self.DIGIT:
                raise self._err("Expected exponent digits")
            while self.curt == self.DIGIT:
                s.append(chr(self.cur))
                self._consume()
                if self.cur == ord('_'):
                    self._consume()

        # Check for suffixes
        float_suffix = False
        decimal_suffix = False
        dur = -1

        if ord('d') <= self.cur <= ord('s'):
            if self.cur == ord('n') and self.peek == ord('s'):
                self._consume()
                self._consume()
                dur = 1  # nanoseconds
            if self.cur == ord('m') and self.peek == ord('s'):
                self._consume()
                self._consume()
                dur = 1000000  # milliseconds
            if self.cur == ord('s') and self.peek == ord('e'):
                self._consume()
                self._consume()
                if self.cur != ord('c'):
                    raise self._err("Expected 'sec' in Duration literal")
                self._consume()
                dur = 1000000000  # seconds
            if self.cur == ord('m') and self.peek == ord('i'):
                self._consume()
                self._consume()
                if self.cur != ord('n'):
                    raise self._err("Expected 'min' in Duration literal")
                self._consume()
                dur = 60000000000  # minutes
            if self.cur == ord('h') and self.peek == ord('r'):
                self._consume()
                self._consume()
                dur = 3600000000000  # hours
            if self.cur == ord('d') and self.peek == ord('a'):
                self._consume()
                self._consume()
                if self.cur != ord('y'):
                    raise self._err("Expected 'day' in Duration literal")
                self._consume()
                dur = 86400000000000  # days

        if self.cur == ord('f') or self.cur == ord('F'):
            self._consume()
            float_suffix = True
        elif self.cur == ord('d') or self.cur == ord('D'):
            self._consume()
            decimal_suffix = True

        if neg:
            whole = -whole

        try:
            # Float literal
            if float_suffix:
                if s is None:
                    self.val = float(whole)
                else:
                    self.val = float(''.join(s))
                return Token.FLOAT_LITERAL

            # Decimal literal (or duration)
            if decimal_suffix or floating:
                if s is None:
                    num = PyDecimal(whole)
                else:
                    num = PyDecimal(''.join(s))
                if dur > 0:
                    from fan.sys.Duration import Duration
                    self.val = Duration.make(int(num * dur))
                    return Token.DURATION_LITERAL
                else:
                    # Wrap with Fantom Decimal
                    from fan.sys.Decimal import Decimal as FanDecimal
                    self.val = FanDecimal.make(num)
                    return Token.DECIMAL_LITERAL

            # Int literal (or duration)
            if s is None:
                num = whole
            else:
                num = int(PyDecimal(''.join(s)))
            if dur > 0:
                from fan.sys.Duration import Duration
                self.val = Duration.make(num * dur)
                return Token.DURATION_LITERAL
            else:
                self.val = num
                return Token.INT_LITERAL

        except Exception as e:
            raise self._err(f"Invalid numeric literal: {''.join(s) if s else whole}")

    def _hex(self):
        """Parse hex int/long literal starting with 0x."""
        self._consume()  # 0
        self._consume()  # x

        # Read first hex digit
        val = self._hex_digit(self.cur)
        if val < 0:
            raise self._err("Expecting hex number")
        self._consume()

        nib_count = 1
        while True:
            nib = self._hex_digit(self.cur)
            if nib < 0:
                if self.cur == ord('_'):
                    self._consume()
                    continue
                break
            nib_count += 1
            if nib_count > 16:
                raise self._err("Hex literal too big")
            val = (val << 4) + nib
            self._consume()

        self.val = val
        return Token.INT_LITERAL

    @staticmethod
    def _hex_digit(c):
        """Convert hex character to int value."""
        if ord('0') <= c <= ord('9'):
            return c - ord('0')
        if ord('a') <= c <= ord('f'):
            return c - ord('a') + 10
        if ord('A') <= c <= ord('F'):
            return c - ord('A') + 10
        return -1

    def _str(self):
        """Parse string literal."""
        self._consume()  # opening quote
        s = []

        while True:
            if self.cur == ord('"'):
                self._consume()
                break
            if self.cur < 0:
                raise self._err("Unexpected end of string")
            if self.cur == ord('$'):
                raise self._err("Interpolated strings unsupported")
            if self.cur == ord('\\'):
                s.append(self._escape())
            elif self.cur == ord('\r'):
                s.append('\n')
                self._consume()
            else:
                s.append(chr(self.cur))
                self._consume()

        self.val = ''.join(s)
        return Token.STR_LITERAL

    def _ch(self):
        """Parse char literal as Int literal."""
        self._consume()  # opening quote

        if self.cur == ord('\\'):
            c = self._escape()
        else:
            c = chr(self.cur)
            self._consume()

        if self.cur != ord("'"):
            raise self._err("Expecting ' close of char literal")
        self._consume()

        self.val = ord(c)
        return Token.INT_LITERAL

    def _escape(self):
        """Parse escape sequence starting with backslash."""
        if self.cur != ord('\\'):
            raise self._err("Internal error")
        self._consume()

        c = self.cur
        if c == ord('b'):
            self._consume()
            return '\b'
        if c == ord('f'):
            self._consume()
            return '\f'
        if c == ord('n'):
            self._consume()
            return '\n'
        if c == ord('r'):
            self._consume()
            return '\r'
        if c == ord('t'):
            self._consume()
            return '\t'
        if c == ord('$'):
            self._consume()
            return '$'
        if c == ord('"'):
            self._consume()
            return '"'
        if c == ord("'"):
            self._consume()
            return "'"
        if c == ord('`'):
            self._consume()
            return '`'
        if c == ord('\\'):
            self._consume()
            return '\\'

        # Check for \uxxxx
        if c == ord('u'):
            self._consume()
            n3 = self._hex_digit(self.cur)
            self._consume()
            n2 = self._hex_digit(self.cur)
            self._consume()
            n1 = self._hex_digit(self.cur)
            self._consume()
            n0 = self._hex_digit(self.cur)
            self._consume()
            if n3 < 0 or n2 < 0 or n1 < 0 or n0 < 0:
                raise self._err("Invalid hex value for \\uxxxx")
            return chr((n3 << 12) | (n2 << 8) | (n1 << 4) | n0)

        raise self._err("Invalid escape sequence")

    def _uri(self):
        """Parse URI literal."""
        self._consume()  # opening tick
        s = []

        while True:
            if self.cur < 0:
                raise self._err("Unexpected end of uri")
            if self.cur == ord('\\'):
                s.append(self._escape())
            elif self.cur == ord('`'):
                self._consume()
                break
            else:
                s.append(chr(self.cur))
                self._consume()

        from fan.sys.Uri import Uri
        self.val = Uri.from_str(''.join(s))
        return Token.URI_LITERAL

    def _skip_comment_sl(self):
        """Skip single line comment (// or **)."""
        self._consume()  # first char
        self._consume()  # second char
        while True:
            if self.cur == ord('\n') or self.cur == ord('\r'):
                self._consume()
                break
            if self.cur < 0:
                break
            self._consume()

    def _skip_comment_ml(self):
        """Skip multi-line comment (/* */). Supports nesting."""
        self._consume()  # /
        self._consume()  # *
        depth = 1
        while True:
            if self.cur == ord('*') and self.peek == ord('/'):
                self._consume()
                self._consume()
                depth -= 1
                if depth <= 0:
                    break
            if self.cur == ord('/') and self.peek == ord('*'):
                self._consume()
                self._consume()
                depth += 1
                continue
            if self.cur < 0:
                break
            self._consume()

    def _consume(self):
        """Consume current char and advance to next."""
        # Track line numbers
        if self.cur == ord('\n') or self.cur == ord('\r'):
            self.line += 1

        # Read next character, normalize \r\n
        c = self.in_stream.r_char()
        if c == ord('\n') and self.peek == ord('\r'):
            c = self.in_stream.r_char()

        # Roll cur to peek, peek to new char
        self.cur = self.peek
        self.curt = self.peekt
        self.peek = c if c is not None else -1
        if self.peek is not None and 0 < self.peek < 128:
            self.peekt = self._char_map[self.peek]
        else:
            self.peekt = Tokenizer.ALPHA if self.peek > 0 else 0

    def _err(self, msg):
        """Create error with line number context."""
        from fan.sys.Err import IOErr
        return IOErr.make(f"{msg} [Line {self.line}]")

    def undo(self, type_, val, line):
        """Push back a token to be returned by next call to next()."""
        if self._undo is not None:
            raise ValueError("Only one pushback supported")
        self._undo = (type_, val, line)

    def reset(self, type_, val, line):
        """Reset current token state."""
        self.type = type_
        self.val = val
        self.line = line
        return type_
