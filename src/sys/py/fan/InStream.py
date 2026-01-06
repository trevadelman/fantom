#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class StrInStream:
    """InStream implementation for reading characters from a string.

    Binary read operations (read, readBuf, unread) throw UnsupportedErr.
    Character read operations work directly on the string.
    """

    def __init__(self, s):
        self._str = s
        self._size = len(s)
        self._pos = 0
        self._pushback = []
        self._charset = None  # Lazy init

    def _get_charset(self):
        """Lazily get charset, defaulting to UTF-8"""
        if self._charset is None:
            from fan.sys.Charset import Charset
            self._charset = Charset.utf8()
        return self._charset

    def charset(self, val=None):
        """Get or set charset (mainly for API compatibility)"""
        if val is None:
            return self._get_charset()
        else:
            self._charset = val
            return self

    def _rChar(self):
        """Read char as int code point, or -1 at end"""
        if self._pushback:
            return self._pushback.pop()
        if self._pos >= self._size:
            return -1
        c = ord(self._str[self._pos])
        self._pos += 1
        return c

    def read(self):
        """Binary read - not supported on string stream"""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary read on Str.in")

    def readBuf(self, buf, n):
        """Binary read - not supported on string stream"""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary read on Str.in")

    def unread(self, b):
        """Binary unread - not supported on string stream"""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary read on Str.in")

    def readChar(self):
        """Read a single character as Int code point, or None at end"""
        c = self._rChar()
        return None if c < 0 else c

    def unreadChar(self, c):
        """Push back a character to be read again"""
        self._pushback.append(int(c))
        return self

    def peekChar(self):
        """Peek at next character without consuming"""
        c = self._rChar()
        if c >= 0:
            self._pushback.append(c)
        return None if c < 0 else c

    def readChars(self, n):
        """Read n characters as a string"""
        if n < 0:
            from .Err import ArgErr
            raise ArgErr.make(f"readChars n < 0: {n}")
        if n == 0:
            return ""
        chars = []
        for _ in range(int(n)):
            c = self._rChar()
            if c < 0:
                from .Err import IOErr
                raise IOErr.make("Unexpected end of stream")
            chars.append(chr(c))
        return ''.join(chars)

    def readLine(self, max_chars=None):
        """Read a line of text"""
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        # Read first char
        c = self._rChar()
        if c < 0:
            return None

        chars = []
        while True:
            # Check for newlines
            if c == 10:  # \n
                break
            if c == 13:  # \r
                # Check for \r\n
                next_c = self._rChar()
                if next_c >= 0 and next_c != 10:
                    self._pushback.append(next_c)
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self._rChar()
            if c < 0:
                break

        return ''.join(chars)

    def readAllStr(self, normalizeNewlines=True):
        """Read all remaining characters as a string"""
        chars = []
        last = -1
        while True:
            c = self._rChar()
            if c < 0:
                break
            if normalizeNewlines:
                if c == 13:  # \r -> \n
                    chars.append(chr(10))
                elif last == 13 and c == 10:
                    pass  # skip \n after \r
                else:
                    chars.append(chr(c))
                last = c
            else:
                chars.append(chr(c))
        return ''.join(chars)

    def readAllLines(self):
        """Read all lines"""
        from .List import List
        lines = []
        while True:
            line = self.readLine()
            if line is None:
                break
            lines.append(line)
        return List.fromLiteral(lines, "sys::Str")

    def eachLine(self, f):
        """Iterate each line"""
        while True:
            line = self.readLine()
            if line is None:
                break
            f.call(line)

    def readStrToken(self, max_chars=None, func=None):
        """Read string token until whitespace or func returns true"""
        from .Int import Int

        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        c = self._rChar()
        if c < 0:
            return None

        chars = []
        while True:
            if func is None:
                terminate = Int.isSpace(c)
            else:
                terminate = func.call(c)

            if terminate:
                self._pushback.append(c)
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self._rChar()
            if c < 0:
                break

        return ''.join(chars)

    def readNullTerminatedStr(self, max_chars=None):
        """Read until null byte or max chars"""
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        c = self._rChar()
        if c < 0:
            return None

        chars = []
        while True:
            if c == 0:
                break
            chars.append(chr(c))
            if len(chars) >= max_len:
                break
            c = self._rChar()
            if c < 0:
                break

        return ''.join(chars)

    def readProps(self):
        """Read properties file format and return as Map[Str:Str]"""
        from .Map import Map
        from .Type import Type, MapType

        # Create properly typed [Str:Str] map
        strType = Type.find("sys::Str")
        props = Map.makeWithType(strType, strType)
        name = ""
        v = None
        in_block_comment = 0
        in_eol_comment = False
        c = 32
        last = 32
        line_num = 1
        col_num = 0

        while True:
            last = c
            c = self._rChar()
            col_num += 1
            if c < 0:
                break

            # End of line
            if c == 10 or c == 13:
                col_num = 0
                in_eol_comment = False
                if last == 13 and c == 10:
                    continue
                n = name.strip()
                if v is not None:
                    props.add(n, v.strip())
                    name = ""
                    v = None
                elif len(n) > 0:
                    from .Err import IOErr
                    raise IOErr.make(f"Invalid name/value pair [Line {line_num}]")
                line_num += 1
                continue

            # If in comment
            if in_eol_comment:
                continue

            # Block comment
            if in_block_comment > 0:
                if last == 47 and c == 42:  # /*
                    in_block_comment += 1
                if last == 42 and c == 47:  # */
                    in_block_comment -= 1
                continue

            # Equal sign
            if c == 61 and v is None:  # =
                v = ""
                continue

            # Line comment at start of line
            if c == 35 and col_num == 1:  # #
                in_eol_comment = True
                continue

            # End of line comment (//) or block comment (/*)
            if c == 47 and self._is_space_char(last):  # /
                peek = self._rChar()
                if peek < 0:
                    break
                if peek == 47:  # //
                    in_eol_comment = True
                    continue
                if peek == 42:  # /*
                    in_block_comment += 1
                    continue
                self._pushback.append(peek)

            # Escape or line continuation
            if c == 92:  # \
                peek = self._rChar()
                if peek < 0:
                    break
                elif peek == 110:  # n
                    c = 10
                elif peek == 114:  # r
                    c = 13
                elif peek == 116:  # t
                    c = 9
                elif peek == 92:  # \
                    c = 92
                elif peek == 13 or peek == 10:
                    # Line continuation
                    line_num += 1
                    if peek == 13:
                        peek = self._rChar()
                        if peek != 10:
                            self._pushback.append(peek)
                    # Skip leading whitespace on next line
                    while True:
                        peek = self._rChar()
                        if peek == 32 or peek == 9:  # space or tab - keep skipping
                            continue
                        if peek >= 0:
                            self._pushback.append(peek)
                        break
                    continue
                elif peek == 117:  # u - unicode escape
                    n3 = self._hex(self._rChar())
                    n2 = self._hex(self._rChar())
                    n1 = self._hex(self._rChar())
                    n0 = self._hex(self._rChar())
                    if n3 < 0 or n2 < 0 or n1 < 0 or n0 < 0:
                        from .Err import IOErr
                        raise IOErr.make(f"Invalid hex value for \\uxxxx [Line {line_num}]")
                    c = (n3 << 12) | (n2 << 8) | (n1 << 4) | n0
                else:
                    from .Err import IOErr
                    raise IOErr.make(f"Invalid escape sequence [Line {line_num}]")

            # Normal character
            if v is None:
                name += chr(c)
            else:
                v += chr(c)

        # Handle final line without newline
        n = name.strip()
        if v is not None:
            props.add(n, v.strip())
        elif len(n) > 0:
            from .Err import IOErr
            raise IOErr.make(f"Invalid name/value pair [Line {line_num}]")

        return props

    def _is_space_char(self, c):
        """Check if character is whitespace"""
        return c == 32 or c == 9 or c == 10 or c == 13

    def _hex(self, c):
        """Convert hex char to value, or -1 if invalid"""
        if 48 <= c <= 57:    # 0-9
            return c - 48
        if 97 <= c <= 102:   # a-f
            return c - 97 + 10
        if 65 <= c <= 70:    # A-F
            return c - 65 + 10
        return -1

    def close(self):
        """Close the stream"""
        return True

    def rChar(self):
        """Read character as int code point for Tokenizer compatibility.

        Returns: int code point or None at end of stream
        """
        c = self.readChar()
        return c if c is not None else None

    def readObj(self, options=None):
        """Read a serialized object from this stream.

        Args:
            options: Optional decode options map

        Returns:
            Deserialized object
        """
        from fanx.ObjDecoder import ObjDecoder
        return ObjDecoder(self, options).readObj()

    def typeof(self):
        """Return Type for InStream"""
        from fan.sys.Type import Type
        return Type.find("sys::InStream")


class InStream(Obj):
    """Input stream for reading text/binary data"""

    def __init__(self, in_stream=None):
        """
        Initialize InStream.
        If in_stream is provided, this wraps another stream.
        """
        self._in = in_stream
        self._charset = None  # Will be initialized lazily to Charset.utf8()

        # If wrapping another InStream, copy its charset
        if in_stream is not None and hasattr(in_stream, 'charset'):
            try:
                self._charset = in_stream.charset()
            except:
                pass

    def _get_charset(self):
        """Lazily get charset, defaulting to UTF-8"""
        if self._charset is None:
            from fan.sys.Charset import Charset
            self._charset = Charset.utf8()
        return self._charset

    def charset(self, val=None):
        """
        Get or set the charset used for character encoding.
        If val is provided, sets the charset and returns self.
        If val is None, returns the current charset.
        """
        if val is None:
            return self._get_charset()
        else:
            self._charset = val
            return self

    def readAllStr(self, normalizeNewlines=True):
        """Read entire stream as a string"""
        if hasattr(self, '_stream'):
            content = self._stream.read()
        elif self._in is not None:
            # Check if wrapped stream has readAllStr (it's an InStream)
            if hasattr(self._in, 'readAllStr'):
                return self._in.readAllStr(normalizeNewlines)
            # Otherwise it's a raw Python stream
            content = self._in.read()
        else:
            return ""

        if isinstance(content, bytes):
            content = content.decode('utf-8')
        if normalizeNewlines:
            content = content.replace('\r\n', '\n').replace('\r', '\n')
        return content

    def readAllLines(self):
        """Read all lines from stream"""
        if hasattr(self, '_stream'):
            content = self._stream.read()
        elif self._in is not None:
            # Check if wrapped stream has readAllLines (it's an InStream)
            if hasattr(self._in, 'readAllLines'):
                return self._in.readAllLines()
            # Otherwise it's a raw Python stream
            content = self._in.read()
        else:
            content = ""

        if isinstance(content, bytes):
            content = content.decode('utf-8')
        if not content:
            return []

        # Split on both \n and \r\n, matching Fantom behavior
        lines = content.splitlines()
        return lines if lines else []

    def readLine(self, max=None):
        """Read a single line from stream"""
        if self._in is not None:
            return self._in.readLine(max)

        if hasattr(self, '_stream'):
            line = self._stream.readline()
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            if line.endswith('\n'):
                line = line[:-1]
            if line.endswith('\r'):
                line = line[:-1]
            return line if line else None
        return None

    def readChar(self):
        """Read a single character, return as Int (unicode code point) or None at end"""
        if self._in is not None and hasattr(self._in, 'readChar'):
            return self._in.readChar()

        if hasattr(self, '_stream'):
            c = self._stream.read(1)
            if not c:
                return None
            if isinstance(c, bytes):
                c = c.decode('utf-8')
            return ord(c) if c else None
        return None

    def read(self):
        """Read a single byte, return as Int or None at end"""
        if self._in is not None:
            return self._in.read()

        if hasattr(self, '_stream'):
            b = self._stream.read(1)
            if not b:
                return None
            if isinstance(b, str):
                return ord(b)
            return b[0] if b else None
        return None

    def unread(self, b):
        """Push back a byte"""
        if self._in is not None:
            return self._in.unread(b)
        # Default implementation - may not be supported
        return self

    def unreadChar(self, c):
        """Push back a character"""
        if self._in is not None and hasattr(self._in, 'unreadChar'):
            return self._in.unreadChar(c)
        # Default implementation - may not be supported
        return self

    def readProps(self):
        """Read a properties file format and return as a Map."""
        from .Map import Map
        result = Map()

        if hasattr(self, '_stream'):
            content = self._stream.read()
        elif self._in is not None:
            return self._in.readProps()
        else:
            return result

        if isinstance(content, bytes):
            content = content.decode('utf-8')

        for line in content.splitlines():
            # Skip empty lines and comments
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue

            # Find the = separator
            eq_pos = line.find('=')
            if eq_pos > 0:
                key = line[:eq_pos].strip()
                value = line[eq_pos + 1:].strip()
                result.set(key, value)

        return result

    def close(self):
        """Close the stream"""
        if self._in is not None and hasattr(self._in, 'close'):
            return self._in.close()
        if hasattr(self, '_stream') and hasattr(self._stream, 'close'):
            self._stream.close()
        return True

    def rChar(self):
        """Read character as int code point for Tokenizer compatibility.

        Returns: int code point or None at end of stream
        """
        c = self.readChar()
        return c if c is not None else None

    def readObj(self, options=None):
        """Read a serialized object from this stream.

        Args:
            options: Optional decode options map

        Returns:
            Deserialized object
        """
        from fanx.ObjDecoder import ObjDecoder
        return ObjDecoder(self, options).readObj()

    def typeof(self):
        """Return Type for InStream"""
        from fan.sys.Type import Type
        return Type.find("sys::InStream")
