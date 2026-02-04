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

    def _r_char(self):
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

    def read_buf(self, buf, n):
        """Binary read - not supported on string stream"""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary read on Str.in")

    def unread(self, b):
        """Binary unread - not supported on string stream"""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary read on Str.in")

    def read_char(self):
        """Read a single character as Int code point, or None at end"""
        c = self._r_char()
        return None if c < 0 else c

    def unread_char(self, c):
        """Push back a character to be read again"""
        self._pushback.append(int(c))
        return self

    def peek_char(self):
        """Peek at next character without consuming"""
        c = self._r_char()
        if c >= 0:
            self._pushback.append(c)
        return None if c < 0 else c

    def read_chars(self, n):
        """Read n characters as a string"""
        if n < 0:
            from .Err import ArgErr
            raise ArgErr.make(f"readChars n < 0: {n}")
        if n == 0:
            return ""
        chars = []
        for _ in range(int(n)):
            c = self._r_char()
            if c < 0:
                from .Err import IOErr
                raise IOErr.make("Unexpected end of stream")
            chars.append(chr(c))
        return ''.join(chars)

    def read_line(self, max_chars=None):
        """Read a line of text"""
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        # Read first char
        c = self._r_char()
        if c < 0:
            return None

        chars = []
        while True:
            # Check for newlines
            if c == 10:  # \n
                break
            if c == 13:  # \r
                # Check for \r\n
                next_c = self._r_char()
                if next_c >= 0 and next_c != 10:
                    self._pushback.append(next_c)
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self._r_char()
            if c < 0:
                break

        return ''.join(chars)

    def read_all_str(self, normalizeNewlines=True):
        """Read all remaining characters as a string"""
        chars = []
        last = -1
        while True:
            c = self._r_char()
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

    def read_all_lines(self):
        """Read all lines"""
        from .List import List
        lines = []
        while True:
            line = self.read_line()
            if line is None:
                break
            lines.append(line)
        return List.from_literal(lines, "sys::Str")

    def each_line(self, f):
        """Iterate each line"""
        while True:
            line = self.read_line()
            if line is None:
                break
            f.call(line)

    def read_str_token(self, max_chars=None, func=None):
        """Read string token until whitespace or func returns true"""
        from .Int import Int

        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        c = self._r_char()
        if c < 0:
            return None

        chars = []
        while True:
            if func is None:
                terminate = Int.is_space(c)
            else:
                terminate = func.call(c)

            if terminate:
                self._pushback.append(c)
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self._r_char()
            if c < 0:
                break

        return ''.join(chars)

    def read_null_terminated_str(self, max_chars=None):
        """Read until null byte or max chars"""
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        c = self._r_char()
        if c < 0:
            return None

        chars = []
        while True:
            if c == 0:
                break
            chars.append(chr(c))
            if len(chars) >= max_len:
                break
            c = self._r_char()
            if c < 0:
                break

        return ''.join(chars)

    def read_props(self):
        """Read properties file format and return as Map[Str:Str]"""
        from .Map import Map
        from .Type import Type, MapType

        # Create properly typed [Str:Str] map
        strType = Type.find("sys::Str")
        props = Map.make_with_type(strType, strType)
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
            c = self._r_char()
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
                peek = self._r_char()
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
                peek = self._r_char()
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
                        peek = self._r_char()
                        if peek != 10:
                            self._pushback.append(peek)
                    # Skip leading whitespace on next line
                    while True:
                        peek = self._r_char()
                        if peek == 32 or peek == 9:  # space or tab - keep skipping
                            continue
                        if peek >= 0:
                            self._pushback.append(peek)
                        break
                    continue
                elif peek == 117:  # u - unicode escape
                    n3 = self._hex(self._r_char())
                    n2 = self._hex(self._r_char())
                    n1 = self._hex(self._r_char())
                    n0 = self._hex(self._r_char())
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

    def r_char(self):
        """Read character as int code point for Tokenizer compatibility.

        Returns: int code point or None at end of stream
        """
        c = self.read_char()
        return c if c is not None else None

    def read_obj(self, options=None):
        """Read a serialized object from this stream.

        Args:
            options: Optional decode options map

        Returns:
            Deserialized object
        """
        from fanx.ObjDecoder import ObjDecoder
        return ObjDecoder(self, options).read_obj()

    def typeof(self):
        """Return Type for this InStream (or subclass)"""
        from fan.sys.Type import Type
        # Get the actual class name and map to Fantom type
        cls = type(self)
        module = cls.__module__
        class_name = cls.__name__
        # Extract pod name from module (e.g., 'fan.web.MultiPartInStream' -> 'web')
        if module.startswith('fan.'):
            parts = module.split('.')
            if len(parts) >= 2:
                pod_name = parts[1]  # 'web', 'sys', etc.
                return Type.find(f"{pod_name}::{class_name}")
        return Type.find(f"sys::{class_name}")


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

    def read_all_str(self, normalizeNewlines=True):
        """Read entire stream as a string.

        For wrapped streams, read character by character using THIS stream's charset,
        not the wrapped stream's charset. This ensures proper charset isolation.
        """
        # Read all chars using this stream's charset
        chars = []
        while True:
            c = self.read_char()
            if c is None:
                break
            chars.append(chr(c))
        content = ''.join(chars)

        if normalizeNewlines:
            content = content.replace('\r\n', '\n').replace('\r', '\n')
        return content

    def read_all_lines(self):
        """Read all lines from stream"""
        if hasattr(self, '_stream'):
            content = self._stream.read()
        elif self._in is not None:
            # Check if wrapped stream has readAllLines (it's an InStream)
            if hasattr(self._in, 'read_all_lines'):
                return self._in.read_all_lines()
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

    def read_line(self, max_chars=None):
        """Read a single line from stream.

        Uses self.read_char() to respect subclass overrides (e.g., ChunkInStream).
        Handles both \n and \r\n line endings, stripping the terminator.
        Returns None at end of stream.
        """
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        # Read first character
        c = self.read_char()
        if c is None:
            return None

        chars = []
        while True:
            # Check for newlines
            if c == ord('\n'):  # \n
                break
            if c == ord('\r'):  # \r
                # Check for \r\n
                next_c = self.read_char()
                if next_c is not None and next_c != ord('\n'):
                    self.unread_char(next_c)
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self.read_char()
            if c is None:
                break

        return ''.join(chars)

    def read_char(self):
        """Read a single character, return as Int (unicode code point) or None at end.

        IMPORTANT: Uses self.read() not self._in.read() so that subclasses which
        override read() (like ChunkInStream, FixedInStream) work correctly with
        read_char(), read_all_str(), etc.
        """
        # Check if wrapped stream is a character stream (StrInStream)
        if self._in is not None and isinstance(self._in, StrInStream):
            return self._in.read_char()

        # For binary streams, use self.read() to get bytes (respects overrides)
        charset_name = self._get_python_encoding()

        if 'utf-16' in charset_name.lower():
            # UTF-16 is 2 bytes per char
            b1 = self.read()
            if b1 is None:
                return None
            b2 = self.read()
            if b2 is None:
                return None
            data = bytes([b1, b2])
            try:
                ch = data.decode(charset_name)
                return ord(ch[0]) if ch else None
            except:
                return None
        else:
            # UTF-8 and others: variable length
            b = self.read()
            if b is None:
                return None
            # For UTF-8, handle multi-byte chars
            if b < 0x80:
                return b
            elif b < 0xE0:
                b2 = self.read()
                if b2 is None:
                    return None
                data = bytes([b, b2])
            elif b < 0xF0:
                b2 = self.read()
                b3 = self.read()
                if b2 is None or b3 is None:
                    return None
                data = bytes([b, b2, b3])
            else:
                b2 = self.read()
                b3 = self.read()
                b4 = self.read()
                if b2 is None or b3 is None or b4 is None:
                    return None
                data = bytes([b, b2, b3, b4])
            try:
                ch = data.decode(charset_name)
                return ord(ch[0]) if ch else None
            except:
                return None

    def _get_python_encoding(self):
        """Get Python encoding name for this stream's charset."""
        name = self._get_charset().name()
        encoding_map = {
            'UTF-8': 'utf-8',
            'UTF-16BE': 'utf-16-be',
            'UTF-16LE': 'utf-16-le',
            'UTF-16': 'utf-16',
            'US-ASCII': 'ascii',
            'ISO-8859-1': 'iso-8859-1',
        }
        return encoding_map.get(name, name.lower().replace('-', '_'))

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

    def read_buf(self, buf, n):
        """Read up to n bytes into buf, return bytes read or None at end.

        Uses self.read() to respect subclass overrides.
        """
        n = int(n)
        if n <= 0:
            return 0

        bytes_read = 0
        for _ in range(n):
            b = self.read()
            if b is None:
                break
            buf.write(b)
            bytes_read += 1

        return bytes_read if bytes_read > 0 else None

    def read_buf_fully(self, buf, n):
        """Read exactly n bytes into buf, then flip buf for reading.

        Throws IOErr if fewer than n bytes available.
        """
        from .Err import IOErr
        n = int(n)
        if buf is None:
            from .Buf import Buf
            buf = Buf.make(n)

        bytes_read = 0
        for _ in range(n):
            b = self.read()
            if b is None:
                raise IOErr.make("Unexpected end of stream")
            buf.write(b)
            bytes_read += 1

        buf.flip()
        return buf

    def read_all_buf(self):
        """Read all remaining bytes as a new Buf."""
        from .Buf import Buf
        buf = Buf.make()
        while True:
            b = self.read()
            if b is None:
                break
            buf.write(b)
        buf.flip()
        return buf

    def read_u1(self):
        """Read unsigned 8-bit."""
        b = self.read()
        if b is None:
            from .Err import IOErr
            raise IOErr.make("Unexpected end of stream")
        return b

    def read_s1(self):
        """Read signed 8-bit."""
        b = self.read_u1()
        return b if b < 128 else b - 256

    def read_u2(self):
        """Read unsigned 16-bit."""
        import struct
        b1 = self.read()
        b2 = self.read()
        if b1 is None or b2 is None:
            from .Err import IOErr
            raise IOErr.make("Unexpected end of stream")
        # Big endian by default
        return (b1 << 8) | b2

    def read_s2(self):
        """Read signed 16-bit."""
        val = self.read_u2()
        return val if val < 32768 else val - 65536

    def read_u4(self):
        """Read unsigned 32-bit."""
        b1 = self.read()
        b2 = self.read()
        b3 = self.read()
        b4 = self.read()
        if b1 is None or b2 is None or b3 is None or b4 is None:
            from .Err import IOErr
            raise IOErr.make("Unexpected end of stream")
        return (b1 << 24) | (b2 << 16) | (b3 << 8) | b4

    def read_s4(self):
        """Read signed 32-bit."""
        val = self.read_u4()
        return val if val < 0x80000000 else val - 0x100000000

    def read_s8(self):
        """Read signed 64-bit."""
        b1 = self.read_u4()
        b2 = self.read_u4()
        val = (b1 << 32) | b2
        return val if val < 0x8000000000000000 else val - 0x10000000000000000

    def unread(self, b):
        """Push back a byte"""
        if self._in is not None:
            return self._in.unread(b)
        # Default implementation - may not be supported
        return self

    def peek(self):
        """Peek at the next byte without consuming it.

        Returns the byte value as Int, or None at end of stream.
        """
        b = self.read()
        if b is not None:
            self.unread(b)
        return b

    def peek_char(self):
        """Peek at the next character without consuming it.

        Returns the character code point as Int, or None at end of stream.
        """
        c = self.read_char()
        if c is not None:
            self.unread_char(c)
        return c

    def read_str_token(self, max_chars=None, func=None):
        """Read a string token terminated when func returns true.

        Args:
            max_chars: Maximum characters to read (default unlimited)
            func: Function |Int ch->Bool| that returns true for terminator char.
                  If null, terminates on whitespace (Int.isSpace).

        Returns:
            Token string, or None at end of stream.
        """
        from .Int import Int

        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        # Read first char
        c = self.read_char()
        if c is None:
            return None

        chars = []
        while True:
            # Check termination
            if func is None:
                terminate = Int.is_space(c)
            else:
                terminate = func.call(c) if hasattr(func, 'call') else func(c)

            if terminate:
                # Push back the terminator
                self.unread_char(c)
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self.read_char()
            if c is None:
                break

        return ''.join(chars)

    def unread_char(self, c):
        """Push back a character"""
        if self._in is not None and hasattr(self._in, 'unread_char'):
            return self._in.unread_char(c)
        # Default implementation - may not be supported
        return self

    def read_props(self):
        """Read a properties file format and return as a Map."""
        from .Map import Map
        result = Map()

        if hasattr(self, '_stream'):
            content = self._stream.read()
        elif self._in is not None:
            return self._in.read_props()
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
                result.set_(key, value)

        return result

    def pipe(self, out, n=None, close=True):
        """Pipe data from this InStream to an OutStream.

        Args:
            out: The OutStream to write to
            n: Number of bytes to pipe (None = all remaining)
            close: Whether to close this stream when done

        Returns:
            Number of bytes piped
        """
        from .Err import IOErr

        try:
            total = 0
            if n is None:
                # Pipe all remaining
                while True:
                    b = self.read()
                    if b is None:
                        break
                    out.write(b)
                    total += 1
            else:
                # Pipe exactly n bytes
                for _ in range(int(n)):
                    b = self.read()
                    if b is None:
                        raise IOErr.make("Unexpected end of stream")
                    out.write(b)
                    total += 1
            return total
        finally:
            if close:
                self.close()

    def close(self):
        """Close the stream"""
        if self._in is not None and hasattr(self._in, 'close'):
            return self._in.close()
        if hasattr(self, '_stream') and hasattr(self._stream, 'close'):
            self._stream.close()
        return True

    def r_char(self):
        """Read character as int code point for Tokenizer compatibility.

        Returns: int code point or None at end of stream
        """
        c = self.read_char()
        return c if c is not None else None

    def read_obj(self, options=None):
        """Read a serialized object from this stream.

        Args:
            options: Optional decode options map

        Returns:
            Deserialized object
        """
        from fanx.ObjDecoder import ObjDecoder
        return ObjDecoder(self, options).read_obj()

    # NOTE: InStream intentionally does NOT define typeof() so that
    # Type.of() uses the class-based fallback which correctly identifies
    # subclasses like web::MultiPartInStream from their module path.
