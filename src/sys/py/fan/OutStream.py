#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class OutStream(Obj):
    """
    OutStream base class for writing bytes and characters.
    """

    # XML escape flags (as static methods for transpiler compatibility)
    @staticmethod
    def xml_esc_newlines():
        return 0x01

    @staticmethod
    def xml_esc_quotes():
        return 0x02

    @staticmethod
    def xml_esc_unicode():
        return 0x04

    def __init__(self, out=None):
        self._out = out
        self._charset = None
        self._endian = None

    def write(self, b):
        """Write a single byte. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write(b)
            return self
        raise NotImplementedError("OutStream.write not implemented")

    def write_buf(self, buf, n=None):
        """Write bytes from buffer. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_buf(buf, n)
            return self
        raise NotImplementedError("OutStream.writeBuf not implemented")

    def write_char(self, c):
        """Write a single character using current charset. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_char(c)
            return self
        raise NotImplementedError("OutStream.writeChar not implemented")

    def write_chars(self, s, off=0, length=None):
        """Write characters from string. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_chars(s, off, length)
            return self
        raise NotImplementedError("OutStream.writeChars not implemented")

    def print_(self, obj):
        """Print object as string. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.print_(obj)
            return self
        raise NotImplementedError("OutStream.print not implemented")

    print = print_

    def print_line(self, obj=None):
        """Print object followed by newline. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.print_line(obj)
            return self
        raise NotImplementedError("OutStream.printLine not implemented")

    def write_i2(self, x):
        """Write 16-bit integer. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_i2(x)
            return self
        raise NotImplementedError("OutStream.writeI2 not implemented")

    def write_i4(self, x):
        """Write 32-bit integer. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_i4(x)
            return self
        raise NotImplementedError("OutStream.writeI4 not implemented")

    def write_i8(self, x):
        """Write 64-bit integer. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_i8(x)
            return self
        raise NotImplementedError("OutStream.writeI8 not implemented")

    def write_f4(self, x):
        """Write 32-bit float. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_f4(x)
            return self
        raise NotImplementedError("OutStream.writeF4 not implemented")

    def write_f8(self, x):
        """Write 64-bit float. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_f8(x)
            return self
        raise NotImplementedError("OutStream.writeF8 not implemented")

    def write_bool(self, x):
        """Write boolean. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_bool(x)
            return self
        raise NotImplementedError("OutStream.writeBool not implemented")

    def write_utf(self, s):
        """Write UTF-8 string with length prefix. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write_utf(s)
            return self
        raise NotImplementedError("OutStream.writeUtf not implemented")

    def flush(self):
        """Flush the stream."""
        if self._out is not None:
            return self._out.flush()
        return self

    def sync(self):
        """Sync the stream."""
        return self.flush()

    def close(self):
        """Close the stream."""
        if self._out is not None:
            return self._out.close()
        return True

    def charset(self, val=None):
        """Get or set charset."""
        if val is None:
            if self._charset is None:
                from .Charset import Charset
                self._charset = Charset.utf8()
            return self._charset
        self._charset = val
        return self

    def endian(self, val=None):
        """Get or set endian."""
        if val is None:
            if self._endian is None:
                from .Endian import Endian
                self._endian = Endian.big()
            return self._endian
        self._endian = val
        return self

    def write_xml(self, s, mask=0):
        """Write XML-escaped string.

        Args:
            s: String to write
            mask: Bitmask (xmlEscNewlines=0x01, xmlEscQuotes=0x02, xmlEscUnicode=0x04)

        Returns:
            self for chaining
        """
        if self._out is not None:
            self._out.write_xml(s, mask)
            return self

        # Default implementation
        xml_esc_newlines = 0x01
        xml_esc_quotes = 0x02
        escNewlines = (mask & xml_esc_newlines) != 0
        escQuotes = (mask & xml_esc_quotes) != 0

        for i, ch in enumerate(str(s)):
            code = ord(ch)
            if ch == '<':
                self.write_chars("&lt;")
            elif ch == '&':
                self.write_chars("&amp;")
            elif ch == '"' and escQuotes:
                self.write_chars("&quot;")
            elif ch == "'" and escQuotes:
                self.write_chars("&#39;")
            elif (ch == '\n' or ch == '\r') and escNewlines:
                self.write_chars(f"&#x{code:x};")
            else:
                self.write_char(code)
        return self

    def write_obj(self, obj, options=None):
        """Write serialized object representation using Fantom serialization format.

        Args:
            obj: Object to serialize
            options: Optional Map with encoding options

        Returns:
            self for chaining
        """
        from fanx.ObjEncoder import ObjEncoder
        ObjEncoder(self, options).write_obj(obj)
        return self

    def write_props(self, props, close=True):
        """Write map as props file format.

        Args:
            props: Map of string key/value pairs
            close: Whether to close the stream when done (default True)

        Returns:
            self for chaining
        """
        if self._out is not None:
            self._out.write_props(props, close)
            return self
        # Default implementation for streams without delegation
        from .Charset import Charset

        for key, val in props.items():
            # Escape key
            escaped_key = self._escape_props_key(str(key))
            # Escape value
            escaped_val = self._escape_props_val(str(val))
            # Write line
            self.write_chars(f"{escaped_key}={escaped_val}\n")

        if close:
            self.close()
        return self

    def _escape_props_key(self, s):
        """Escape special characters in props key."""
        result = []
        for ch in s:
            if ch == '=':
                result.append('\\u003d')
            elif ch == ':':
                result.append('\\u003a')
            elif ch == '\\':
                result.append('\\\\')
            elif ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            elif ord(ch) > 127:
                result.append(f'\\u{ord(ch):04x}')
            else:
                result.append(ch)
        return ''.join(result)

    def _escape_props_val(self, s):
        """Escape special characters in props value."""
        result = []
        for ch in s:
            if ch == '\\':
                result.append('\\\\')
            elif ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            elif ch == '/':
                result.append('\\u002f')
            elif ord(ch) > 127:
                result.append(f'\\u{ord(ch):04x}')
            else:
                result.append(ch)
        return ''.join(result)

    def typeof(self):
        from .Type import Type
        return Type.find("sys::OutStream")
