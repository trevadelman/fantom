#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

import io
import struct
import random
import hashlib
import base64
from .Obj import Obj
from .OutStream import OutStream
from .InStream import InStream


class Buf(Obj):
    """Buf models a block of bytes with random access."""

    def __init__(self, data=None, capacity=1024):
        if data is not None:
            if isinstance(data, bytes):
                self._bytes = io.BytesIO(data)
                self._bytes.seek(0, 2)  # seek to end
                self._size = len(data)
                self._capacity = max(capacity, len(data))
            else:
                self._bytes = io.BytesIO()
                self._size = 0
                self._capacity = int(capacity)
        else:
            self._bytes = io.BytesIO()
            self._size = 0
            self._capacity = int(capacity)
        self._pos = 0
        self._charset = None  # Lazy init to avoid circular import
        self._endian = None   # Lazy init
        self._in = None
        self._out = None
        self._unread_stack = []  # Stack for unread bytes
        self._unread_char_stack = []  # Stack for unread characters

    @staticmethod
    def make(capacity=1024):
        """Create empty Buf with capacity."""
        return Buf(capacity=int(capacity))

    @staticmethod
    def random(size):
        """Create Buf with random bytes."""
        data = bytes([random.randint(0, 255) for _ in range(int(size))])
        return Buf(data)

    @staticmethod
    def from_hex(s):
        """Create Buf from hex string."""
        # Filter non-hex chars
        hex_chars = ''.join(c for c in str(s) if c in '0123456789abcdefABCDEF')
        if len(hex_chars) % 2 != 0:
            from .Err import IOErr
            raise IOErr.make("Invalid hex str")
        data = bytes.fromhex(hex_chars)
        return Buf(data)

    @staticmethod
    def from_base64(s):
        """Create Buf from base64 string."""
        s = str(s)
        # Filter to only valid base64 characters (strip whitespace, non-ASCII, etc.)
        valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=-_')
        s = ''.join(c for c in s if c in valid_chars)
        # Handle URL-safe base64
        s = s.replace('-', '+').replace('_', '/')
        # Add padding if needed
        missing = len(s) % 4
        if missing:
            s += '=' * (4 - missing)
        data = base64.b64decode(s)
        return Buf(data)

    @staticmethod
    def from_bytes(data):
        """Create Buf from bytes."""
        return Buf(data)

    #################################################################
    # Identity
    #################################################################

    def typeof(self):
        from .Type import Type
        return Type.find("sys::Buf")

    def to_str(self):
        return f"Buf(pos={self._pos} size={self._size})"

    def __str__(self):
        return self.to_str()

    def equals(self, other):
        return self is other

    def bytes_equal(self, other):
        """Compare bytes content."""
        if self is other:
            return True
        if not isinstance(other, Buf):
            return False
        if self._size != other._size:
            return False
        self_data = self._get_data()
        other_data = other._get_data()
        return self_data == other_data

    #################################################################
    # Access
    #################################################################

    def is_empty(self):
        return self._size == 0

    def size(self, val=None):
        """Get or set size."""
        if val is None:
            return self._size
        val = int(val)
        # Expand capacity if needed
        if val > self._capacity:
            self._capacity = val
        self._size = val
        return self

    def pos(self, val=None):
        """Get or set position."""
        if val is None:
            return self._pos
        self._pos = int(val)
        return self

    def capacity(self, val=None):
        """Get or set capacity.

        For file-backed Bufs, capacity is always Int.maxVal and cannot be set.
        """
        # File-backed Bufs have unlimited capacity
        is_file_backed = hasattr(self, '_file') and self._file is not None

        if val is None:
            if is_file_backed:
                from .Int import Int
                return Int.max_val()
            return self._capacity

        # Ignore capacity changes for file-backed Bufs
        if is_file_backed:
            return self

        val = int(val)
        if val < 0:
            from .Err import ArgErr
            raise ArgErr.make(f"capacity < 0: {val}")
        if val < self._size:
            from .Err import ArgErr
            raise ArgErr.make(f"capacity < size: {val} < {self._size}")
        self._capacity = val
        return self

    def remaining(self):
        """Bytes remaining from pos to size."""
        return self._size - self._pos

    def more(self):
        """Return true if more bytes to read."""
        return self._size - self._pos > 0

    def seek(self, pos):
        """Seek to position. Negative seeks from end.

        Clears any unread byte/char stacks to ensure clean read state.
        """
        pos = int(pos)
        if pos < 0:
            pos = self._size + pos
        if pos < 0 or pos > self._size:
            from .Err import IndexErr
            raise IndexErr.make(str(pos))
        self._pos = pos
        # Clear unread stacks - seeking invalidates any pushed-back bytes/chars
        self._unread_stack = []
        self._unread_char_stack = []
        return self

    def flip(self):
        """Flip buffer - set size to pos, pos to 0."""
        self._size = self._pos
        self._pos = 0
        return self

    def get(self, pos):
        """Get byte at position."""
        pos = int(pos)
        if pos < 0:
            pos = self._size + pos
        if pos < 0 or pos >= self._size:
            from .Err import IndexErr
            raise IndexErr.make(str(pos))
        self._bytes.seek(pos)
        b = self._bytes.read(1)
        return b[0] if b else 0

    def __getitem__(self, pos):
        return self.get(pos)

    def get_range(self, r):
        """Get slice as new Buf."""
        s = r.start_(self._size)
        e = r.end_(self._size)
        n = e - s + 1
        if n < 0:
            from .Err import IndexErr
            raise IndexErr.make(str(r))
        self._bytes.seek(s)
        data = self._bytes.read(n)
        result = Buf(data)
        # Copy charset from parent buffer
        result._charset = self._charset
        return result

    def dup(self):
        """Duplicate buffer."""
        data = self._get_data()
        return Buf(data)

    def to_immutable(self):
        """Return an immutable ConstBuf, stealing content from this Buf.

        After this call, this Buf will be cleared (size=0, capacity=0).
        This is the expected "steal" semantic - the immutable buffer
        takes ownership of the data.
        """
        from .ConstBuf import ConstBuf
        data = self._get_data()
        result = ConstBuf(data)
        # Clear the original buffer (steal semantic)
        self.clear()
        self._capacity = 0
        return result

    def is_immutable(self):
        """Return true if this Buf is immutable."""
        return getattr(self, '_immutable', False)

    #################################################################
    # Modification
    #################################################################

    def set_(self, pos, b):
        """Set byte at position."""
        pos = int(pos)
        if pos < 0:
            pos = self._size + pos
        if pos < 0 or pos >= self._size:
            from .Err import IndexErr
            raise IndexErr.make(str(pos))
        self._bytes.seek(pos)
        self._bytes.write(bytes([int(b) & 0xFF]))
        return self

    def __setitem__(self, pos, b):
        self.set_(pos, b)

    def clear(self):
        """Clear buffer."""
        self._pos = 0
        self._size = 0
        self._bytes = io.BytesIO()
        return self

    def trim(self):
        """Trim to size."""
        return self

    def flush(self):
        """Flush (alias for sync)."""
        return self.sync()

    def sync(self):
        """Sync buffer."""
        return self

    def close(self):
        """Close buffer. If opened from a file, sync back to file."""
        # Check if this Buf was opened from a File
        if hasattr(self, '_file') and self._file is not None:
            # Write buffer content to file
            data = self._get_data()
            self._file._path.write_bytes(data)
        return True

    def fill(self, b, times):
        """Fill with byte value."""
        b = int(b) & 0xFF
        self._bytes.seek(self._pos)
        for _ in range(int(times)):
            self._bytes.write(bytes([b]))
        self._pos += int(times)
        if self._pos > self._size:
            self._size = self._pos
        return self

    #################################################################
    # Charset/Endian
    #################################################################

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

    #################################################################
    # OutStream Operations (write)
    #################################################################

    def out(self):
        """Get OutStream for writing."""
        if self._out is None:
            self._out = BufOutStream(self)
        return self._out

    def write(self, b):
        """Write single byte."""
        # Check read-only mode (set by File.open_("r"))
        if getattr(self, '_mode', None) == 'r':
            from .Err import IOErr
            raise IOErr.make("Buf is read-only")
        # Grow capacity if needed (double when exceeded)
        if self._pos >= self._capacity:
            new_capacity = max(self._capacity * 2, self._pos + 1)
            self._capacity = new_capacity
        self._bytes.seek(self._pos)
        self._bytes.write(bytes([int(b) & 0xFF]))
        self._pos += 1
        if self._pos > self._size:
            self._size = self._pos
        return self

    def write_buf(self, other, n=None):
        """Write from another Buf.

        For immutable source buffers (ConstBuf), always read from position 0
        since they present their full content regardless of internal state.
        """
        if n is None:
            n = other.remaining()
        n = int(n)

        # For immutable buffers, always read from start
        if other.is_immutable():
            other._bytes.seek(0)
            data = other._bytes.read(n)
            # Don't modify other._pos for immutable bufs
        else:
            other._bytes.seek(other._pos)
            data = other._bytes.read(n)
            other._pos += len(data)

        self._bytes.seek(self._pos)
        self._bytes.write(data)
        self._pos += len(data)
        if self._pos > self._size:
            self._size = self._pos
        return self

    def write_i2(self, x):
        """Write 16-bit int (handles full unsigned range)."""
        x = int(x) & 0xFFFF  # Mask to 16-bit
        if self._is_big_endian():
            self.write((x >> 8) & 0xFF)
            self.write(x & 0xFF)
        else:
            self.write(x & 0xFF)
            self.write((x >> 8) & 0xFF)
        return self

    def write_i4(self, x):
        """Write 32-bit int (handles full unsigned range)."""
        x = int(x) & 0xFFFFFFFF  # Mask to 32-bit
        if self._is_big_endian():
            self.write((x >> 24) & 0xFF)
            self.write((x >> 16) & 0xFF)
            self.write((x >> 8) & 0xFF)
            self.write(x & 0xFF)
        else:
            self.write(x & 0xFF)
            self.write((x >> 8) & 0xFF)
            self.write((x >> 16) & 0xFF)
            self.write((x >> 24) & 0xFF)
        return self

    def write_i8(self, x):
        """Write 64-bit signed int."""
        x = int(x)
        # First mask to 64 bits to handle arbitrary precision Python ints
        x = x & 0xFFFFFFFFFFFFFFFF
        # Convert unsigned representation to signed for struct.pack
        if x >= 0x8000000000000000:
            x = x - 0x10000000000000000
        fmt = '>q' if self._is_big_endian() else '<q'
        self._write_struct(fmt, x)
        return self

    def write_f4(self, x):
        """Write 32-bit float."""
        fmt = '>f' if self._is_big_endian() else '<f'
        self._write_struct(fmt, float(x))
        return self

    def write_f8(self, x):
        """Write 64-bit float."""
        fmt = '>d' if self._is_big_endian() else '<d'
        self._write_struct(fmt, float(x))
        return self

    def write_bool(self, x):
        """Write boolean as byte."""
        return self.write(1 if x else 0)

    def write_decimal(self, x):
        """Write decimal as string (Fantom serialization)."""
        s = str(float(x))
        return self.write_utf(s)

    def write_utf(self, s):
        """Write modified UTF-8 string."""
        data = str(s).encode('utf-8')
        self.write_i2(len(data))
        self._bytes.seek(self._pos)
        self._bytes.write(data)
        self._pos += len(data)
        if self._pos > self._size:
            self._size = self._pos
        return self

    def write_char(self, c):
        """Write character using charset."""
        ch = chr(int(c))
        charset_name = self._get_python_encoding()
        data = ch.encode(charset_name)
        self._bytes.seek(self._pos)
        self._bytes.write(data)
        self._pos += len(data)
        if self._pos > self._size:
            self._size = self._pos
        return self

    def write_chars(self, s, off=0, length=None):
        """Write string chars."""
        s = str(s)
        if length is None:
            s = s[int(off):]
        else:
            s = s[int(off):int(off)+int(length)]
        charset_name = self._get_python_encoding()
        data = s.encode(charset_name)
        self._bytes.seek(self._pos)
        self._bytes.write(data)
        self._pos += len(data)
        if self._pos > self._size:
            self._size = self._pos
        return self

    def print_(self, obj):
        """Print object as string."""
        from .ObjUtil import ObjUtil
        s = "null" if obj is None else ObjUtil.to_str(obj)
        return self.write_chars(s)

    # Alias for transpiled code
    print = print_

    def print_line(self, obj=None):
        """Print with newline."""
        if obj is not None:
            self.print_(obj)
        return self.write_char(ord('\n'))

    def write_xml(self, s, mask=0):
        """Write XML-escaped string.

        Args:
            s: The string to write
            mask: Bitmask of OutStream.xmlEscNewlines/xmlEscQuotes/xmlEscUnicode

        Returns:
            This Buf for chaining
        """
        s = str(s)
        escNewlines = (mask & 0x01) != 0  # xmlEscNewlines
        escQuotes = (mask & 0x02) != 0    # xmlEscQuotes
        escUnicode = (mask & 0x04) != 0   # xmlEscUnicode

        for i, ch in enumerate(s):
            code = ord(ch)

            # Control chars (except tab=9, lf=10, cr=13)
            if code < 32 and code not in (9, 10, 13):
                self._write_xml_esc(code)
            # Newlines
            elif ch == '\n' or ch == '\r':
                if not escNewlines:
                    self.write_char(code)
                else:
                    self._write_xml_esc(code)
            # XML special chars
            elif ch == '<':
                self.write_chars("&lt;")
            elif ch == '>':
                if i > 0 and s[i-1] != ']':
                    self.write_char(code)
                else:
                    self.write_chars("&gt;")
            elif ch == '&':
                self.write_chars("&amp;")
            elif ch == '"':
                if not escQuotes:
                    self.write_char(code)
                else:
                    self.write_chars("&quot;")
            elif ch == "'":
                if not escQuotes:
                    self.write_char(code)
                else:
                    self.write_chars("&#39;")
            # Unicode chars > 0xf7
            elif code > 0xf7 and escUnicode:
                self._write_xml_esc(code)
            # Normal chars
            else:
                self.write_char(code)

        return self

    def _write_xml_esc(self, ch):
        """Write XML numeric character escape."""
        hex_chars = "0123456789abcdef"
        self.write_chars("&#x")
        if ch > 0xff:
            self.write_char(ord(hex_chars[(ch >> 12) & 0xf]))
            self.write_char(ord(hex_chars[(ch >> 8) & 0xf]))
        self.write_char(ord(hex_chars[(ch >> 4) & 0xf]))
        self.write_char(ord(hex_chars[ch & 0xf]))
        self.write_chars(";")

    def write_props(self, props):
        """Write map as props file format.

        Props files are always UTF-8 encoded.
        Keys and values are escaped for special characters.
        """
        from .Charset import Charset

        # Props files are always UTF-8
        origCharset = self.charset()
        self.charset(Charset.utf8())

        try:
            for key, val in props.items():
                # Escape key
                escaped_key = self._escape_props_key(str(key))
                # Escape value
                escaped_val = self._escape_props_val(str(val))
                # Write line
                self.write_chars(f"{escaped_key}={escaped_val}\n")
        finally:
            self.charset(origCharset)

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

    def write_obj(self, obj, options=None):
        """Write serialized object representation using Fantom serialization format.

        Args:
            obj: Object to serialize
            options: Optional Map with encoding options

        Returns:
            self for chaining
        """
        from fanx.ObjEncoder import ObjEncoder
        ObjEncoder(self.out(), options).write_obj(obj)
        return self

    def read_obj(self, options=None):
        """Read a serialized object from this buffer.

        Args:
            options: Optional decode options map

        Returns:
            Deserialized object
        """
        from fanx.ObjDecoder import ObjDecoder
        return ObjDecoder(self.in_(), options).read_obj()

    #################################################################
    # InStream Operations (read)
    #################################################################

    def in_(self):
        """Get InStream for reading.

        Returns the cached InStream, creating it if needed.
        This matches Fantom's behavior where Buf.in returns the same stream.
        """
        if self._in is None:
            self._in = BufInStream(self)
        return self._in

    def read(self):
        """Read single byte or null at end."""
        # Check unread stack first
        if self._unread_stack:
            return self._unread_stack.pop()
        if self._pos >= self._size:
            return None
        self._bytes.seek(self._pos)
        b = self._bytes.read(1)
        if not b:
            return None
        self._pos += 1
        return b[0]

    def read_buf(self, other, n):
        """Read into another Buf."""
        n = int(n)
        avail = self._size - self._pos
        to_read = min(n, avail)
        if to_read <= 0:
            return None
        self._bytes.seek(self._pos)
        data = self._bytes.read(to_read)
        self._pos += len(data)
        other._bytes.seek(other._pos)
        other._bytes.write(data)
        other._pos += len(data)
        if other._pos > other._size:
            other._size = other._pos
        return len(data)

    def unread(self, b):
        """Push byte to be read next (stack behavior)."""
        self._unread_stack.append(int(b) & 0xFF)
        return self

    def read_all_buf(self):
        """Read remaining as new Buf."""
        self._bytes.seek(self._pos)
        data = self._bytes.read(self._size - self._pos)
        self._pos = self._size
        return Buf(data)

    def read_buf_fully(self, buf, n):
        """Read exactly n bytes into buf, then flip buf for reading."""
        n = int(n)
        if buf is None:
            buf = Buf.make(n)
        result = self.read_buf(buf, n)
        if result is None or result < n:
            from .Err import IOErr
            raise IOErr.make("Unexpected end of stream")
        buf.flip()  # Reset pos to 0 so caller can read the bytes
        return buf

    def peek(self):
        """Peek next byte without advancing."""
        # Check unread stack first
        if self._unread_stack:
            return self._unread_stack[-1]  # peek top of stack without pop
        if self._pos >= self._size:
            return None
        self._bytes.seek(self._pos)
        b = self._bytes.read(1)
        return b[0] if b else None

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
        fmt = '>H' if self._is_big_endian() else '<H'
        return self._read_struct(fmt)

    def read_s2(self):
        """Read signed 16-bit."""
        fmt = '>h' if self._is_big_endian() else '<h'
        return self._read_struct(fmt)

    def read_u4(self):
        """Read unsigned 32-bit."""
        fmt = '>I' if self._is_big_endian() else '<I'
        return self._read_struct(fmt)

    def read_s4(self):
        """Read signed 32-bit."""
        fmt = '>i' if self._is_big_endian() else '<i'
        return self._read_struct(fmt)

    def read_s8(self):
        """Read signed 64-bit."""
        fmt = '>q' if self._is_big_endian() else '<q'
        return self._read_struct(fmt)

    def read_f4(self):
        """Read 32-bit float."""
        fmt = '>f' if self._is_big_endian() else '<f'
        return self._read_struct(fmt)

    def read_f8(self):
        """Read 64-bit float."""
        fmt = '>d' if self._is_big_endian() else '<d'
        return self._read_struct(fmt)

    def read_bool(self):
        """Read boolean."""
        return self.read_u1() != 0

    def read_utf(self):
        """Read modified UTF-8 string."""
        length = self.read_u2()
        self._bytes.seek(self._pos)
        data = self._bytes.read(length)
        self._pos += len(data)
        return data.decode('utf-8')

    def read_decimal(self):
        """Read decimal serialized as UTF string."""
        return self.in_().read_decimal()

    def read_str_token(self, max_chars=None, func=None):
        """Read string token until whitespace or func returns true."""
        return self.in_().read_str_token(max_chars, func)

    def read_props(self):
        """Read a properties file format and return as a Map.

        Props files are always UTF-8 encoded.
        """
        return self.in_().read_props()

    def read_char(self):
        """Read character using charset."""
        # Check unread char stack first
        if self._unread_char_stack:
            return self._unread_char_stack.pop()
        if self._pos >= self._size:
            return None
        charset_name = self._get_python_encoding()
        self._bytes.seek(self._pos)
        # For UTF-8, read up to 4 bytes to decode one char
        for byte_count in range(1, 5):
            if self._pos + byte_count > self._size:
                break
            self._bytes.seek(self._pos)
            data = self._bytes.read(byte_count)
            try:
                ch = data.decode(charset_name)
                if len(ch) == 1:
                    self._pos += byte_count
                    return ord(ch)
            except:
                continue
        return None

    def unread_char(self, c):
        """Push character to be read next (stack behavior)."""
        self._unread_char_stack.append(int(c))
        return self

    def peek_char(self):
        """Peek character without advancing."""
        # Check unread char stack first
        if self._unread_char_stack:
            return self._unread_char_stack[-1]  # peek top of stack without pop
        old_pos = self._pos
        ch = self.read_char()
        self._pos = old_pos
        return ch

    def read_chars(self, n):
        """Read exactly n characters.

        Throws IOErr if fewer than n characters are available.
        """
        if n < 0:
            from .Err import ArgErr
            raise ArgErr.make(f"readChars n < 0: {n}")
        chars = []
        for _ in range(int(n)):
            ch = self.read_char()
            if ch is None:
                from .Err import IOErr
                raise IOErr.make("Unexpected end of stream")
            chars.append(chr(ch))
        return ''.join(chars)

    def read_line(self, max_chars=None):
        """Read line of text."""
        if self._pos >= self._size:
            return None
        chars = []
        count = 0
        while self._pos < self._size:
            if max_chars is not None and count >= max_chars:
                break
            ch = self.read_char()
            if ch is None:
                break
            if ch == ord('\n'):
                break
            if ch == ord('\r'):
                # Check for \r\n
                next_ch = self.peek_char()
                if next_ch == ord('\n'):
                    self.read_char()
                break
            chars.append(chr(ch))
            count += 1
        if not chars and self._pos >= self._size:
            return None
        return ''.join(chars)

    def read_all_str(self, normalize=True):
        """Read all remaining as string."""
        self._bytes.seek(self._pos)
        data = self._bytes.read(self._size - self._pos)
        self._pos = self._size
        charset_name = self._get_python_encoding()
        s = data.decode(charset_name)
        if normalize:
            s = s.replace('\r\n', '\n').replace('\r', '\n')
        return s

    def read_all_lines(self):
        """Read all lines."""
        from .List import List
        lines = []
        while True:
            line = self.read_line()
            if line is None:
                break
            lines.append(line)
        return List.from_literal(lines, "sys::Str")

    def each_line(self, f):
        """Iterate each line."""
        while True:
            line = self.read_line()
            if line is None:
                break
            f.call(line)

    #################################################################
    # Conversion
    #################################################################

    def to_hex(self):
        """Convert to hex string."""
        return self._get_data().hex()

    def to_base64(self):
        """Convert to base64 string."""
        return base64.b64encode(self._get_data()).decode('ascii')

    def to_base64_uri(self):
        """Convert to URL-safe base64."""
        return base64.urlsafe_b64encode(self._get_data()).decode('ascii').rstrip('=')

    def to_file(self, uri):
        """Create an in-memory file backed by this buffer's contents.

        Args:
            uri: The Uri or string for the virtual file

        Returns:
            A MemFile backed by this buffer's immutable contents
        """
        from .MemFile import MemFile
        from .Uri import Uri

        if isinstance(uri, str):
            uri = Uri.from_str(uri)
        # Create immutable copy of buffer for the file
        immutable_buf = self.to_immutable()
        return MemFile.make(immutable_buf, uri)

    def to_digest(self, algorithm):
        """Compute digest hash."""
        alg_map = {
            'MD5': 'md5',
            'SHA-1': 'sha1',
            'SHA1': 'sha1',
            'SHA-256': 'sha256',
            'SHA-384': 'sha384',
            'SHA-512': 'sha512',
        }
        alg = alg_map.get(algorithm, algorithm.lower())
        try:
            h = hashlib.new(alg)
            h.update(self._get_data())
            return Buf(h.digest())
        except ValueError:
            from .Err import ArgErr
            raise ArgErr.make(f"Unknown digest algorithm: {algorithm}")

    def hmac(self, algorithm, key):
        """Compute HMAC of buffer content.

        Args:
            algorithm: Hash algorithm (MD5, SHA-1, SHA-256, SHA-384, SHA-512)
            key: Buf containing the secret key

        Returns:
            Buf containing the HMAC digest
        """
        import hmac as hmac_module
        alg_map = {
            'MD5': 'md5',
            'SHA-1': 'sha1',
            'SHA1': 'sha1',
            'SHA-256': 'sha256',
            'SHA-384': 'sha384',
            'SHA-512': 'sha512',
        }
        alg = alg_map.get(algorithm, algorithm.lower().replace('-', ''))
        try:
            key_bytes = key._get_data() if isinstance(key, Buf) else bytes(key)
            h = hmac_module.new(key_bytes, self._get_data(), alg)
            return Buf(h.digest())
        except ValueError:
            from .Err import ArgErr
            raise ArgErr.make(f"Unknown HMAC algorithm: {algorithm}")

    @staticmethod
    def pbk(algorithm, password, salt, iterations, keyLen):
        """PBKDF2 key derivation function.

        Args:
            algorithm: Algorithm name (PBKDF2WithHmacSHA1, PBKDF2WithHmacSHA256)
            password: Buf containing the password (or string)
            salt: Buf containing the salt (or string)
            iterations: Number of iterations
            keyLen: Desired key length in bytes

        Returns:
            Buf containing the derived key
        """
        alg_map = {
            'PBKDF2WithHmacSHA1': 'sha1',
            'PBKDF2WithHmacSHA256': 'sha256',
            'PBKDF2WithHmacSHA384': 'sha384',
            'PBKDF2WithHmacSHA512': 'sha512',
        }
        hash_name = alg_map.get(algorithm)
        if hash_name is None:
            from .Err import ArgErr
            raise ArgErr.make(f"Unknown PBKDF2 algorithm: {algorithm}")

        # Handle Buf, bytes, or string inputs
        if isinstance(password, Buf):
            password_bytes = password._get_data()
        elif isinstance(password, bytes):
            password_bytes = password
        else:
            password_bytes = str(password).encode('utf-8')

        if isinstance(salt, Buf):
            salt_bytes = salt._get_data()
        elif isinstance(salt, bytes):
            salt_bytes = salt
        else:
            salt_bytes = str(salt).encode('utf-8')

        key = hashlib.pbkdf2_hmac(hash_name, password_bytes, salt_bytes,
                                   int(iterations), int(keyLen))
        return Buf(key)

    # CRC-16 odd parity lookup table (from Fantom JS implementation)
    _CRC16_ODD_PARITY = [0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0]

    def crc(self, algorithm):
        """Compute CRC checksum."""
        import zlib
        if algorithm == "CRC-16":
            return self._crc16()
        if algorithm == "CRC-32":
            return zlib.crc32(self._get_data()) & 0xFFFFFFFF
        if algorithm == "CRC-32-Adler":
            return zlib.adler32(self._get_data()) & 0xFFFFFFFF
        from .Err import ArgErr
        raise ArgErr.make(f"Unknown CRC algorithm: {algorithm}")

    def _crc16(self):
        """Compute CRC-16 checksum using standard algorithm."""
        data = self._get_data()
        seed = 0xFFFF
        for byte in data:
            seed = self._do_crc16(byte, seed)
        return seed

    def _do_crc16(self, data_to_crc, seed):
        """Single byte CRC-16 computation."""
        dat = (data_to_crc ^ (seed & 0xFF)) & 0xFF
        seed = (seed & 0xFFFF) >> 8
        index1 = dat & 0x0F
        index2 = dat >> 4
        if (Buf._CRC16_ODD_PARITY[index1] ^ Buf._CRC16_ODD_PARITY[index2]) == 1:
            seed ^= 0xC001
        dat <<= 6
        seed ^= dat
        dat <<= 1
        seed ^= dat
        return seed & 0xFFFF

    #################################################################
    # Python Interop (to_py / from_py)
    #################################################################

    def to_py(self):
        """Convert to native Python bytes.

        Returns:
            The buffer content as Python bytes (from position 0 to size).

        Example:
            >>> buf = Buf.make()
            >>> buf.write(65).write(66).write(67)
            >>> buf.to_py()
            b'ABC'
        """
        return self._get_data()

    @staticmethod
    def from_py(data):
        """Create Buf from native Python bytes or bytearray.

        Args:
            data: Python bytes or bytearray

        Returns:
            Fantom Buf

        Example:
            >>> Buf.from_py(b'hello')
            Buf(pos=0 size=5)
        """
        if isinstance(data, bytearray):
            data = bytes(data)
        return Buf(data)

    #################################################################
    # Internal
    #################################################################

    def _get_data(self):
        """Get bytes from 0 to size."""
        self._bytes.seek(0)
        return self._bytes.read(self._size)

    def _get_python_encoding(self):
        """Get Python encoding name for current charset."""
        name = self.charset().name()
        # Map Fantom charset names to Python encoding names
        encoding_map = {
            'UTF-8': 'utf-8',
            'UTF-16BE': 'utf-16-be',
            'UTF-16LE': 'utf-16-le',
            'UTF-16': 'utf-16',
            'US-ASCII': 'ascii',
            'ISO-8859-1': 'iso-8859-1',
        }
        return encoding_map.get(name, name.lower().replace('-', '_'))

    def _is_big_endian(self):
        """Check if big endian."""
        return self.endian().name == "big"

    def _write_struct(self, fmt, value):
        """Write using struct format."""
        data = struct.pack(fmt, value)
        self._bytes.seek(self._pos)
        self._bytes.write(data)
        self._pos += len(data)
        if self._pos > self._size:
            self._size = self._pos

    def _read_struct(self, fmt):
        """Read using struct format."""
        size = struct.calcsize(fmt)
        if self._pos + size > self._size:
            from .Err import IOErr
            raise IOErr.make("Unexpected end of stream")
        self._bytes.seek(self._pos)
        data = self._bytes.read(size)
        self._pos += size
        return struct.unpack(fmt, data)[0]


class BufOutStream(OutStream):
    """OutStream wrapper for Buf."""

    def __init__(self, buf):
        super().__init__(None)  # No underlying stream - we wrap a Buf
        self._buf = buf
        self._bitsBuf = 0  # Lower 8 bits = buffered byte, bits 8-15 = buffer size

    def write(self, b):
        self._buf.write(b)
        return self

    def write_buf(self, other, n=None):
        self._buf.write_buf(other, n)
        return self

    def write_i2(self, x):
        self._buf.write_i2(x)
        return self

    def write_i4(self, x):
        self._buf.write_i4(x)
        return self

    def write_i8(self, x):
        self._buf.write_i8(x)
        return self

    def write_f4(self, x):
        self._buf.write_f4(x)
        return self

    def write_f8(self, x):
        self._buf.write_f8(x)
        return self

    def write_bool(self, x):
        self._buf.write_bool(x)
        return self

    def write_decimal(self, x):
        self._buf.write_decimal(x)
        return self

    def write_utf(self, s):
        self._buf.write_utf(s)
        return self

    def write_char(self, c):
        self._buf.write_char(c)
        return self

    def write_chars(self, s, off=0, length=None):
        self._buf.write_chars(s, off, length)
        return self

    def print_(self, obj):
        self._buf.print_(obj)
        return self

    print = print_

    def print_line(self, obj=None):
        self._buf.print_line(obj)
        return self

    def write_bits(self, val, num):
        """Write bits to stream.

        Args:
            val: The value containing the bits to write
            num: Number of bits to write (0-64)

        Bits are written most significant first. If the number of bits written
        doesn't fill a complete byte, the remaining bits are buffered until
        flush() is called or more bits are written.
        """
        # Arg checking
        num = int(num)
        if num == 0:
            return self
        if num < 0 or num > 64:
            from .Err import ArgErr
            raise ArgErr.make(f"Bit num not 0 - 64: {num}")

        val = int(val)

        # buffer is stored as: (bufSize << 8) | bufByte
        bitsBuf = self._bitsBuf
        bufByte = bitsBuf & 0xff
        bufSize = (bitsBuf >> 8) & 0xff

        # Write bits, sinking byte once we reach 8 bits
        for i in range(num - 1, -1, -1):
            bit = (val >> i) & 0x1
            bufByte |= bit << (7 - bufSize)
            bufSize += 1
            if bufSize == 8:
                self._buf.write(bufByte)
                bufByte = 0
                bufSize = 0

        # Save buffer
        self._bitsBuf = (bufSize << 8) | bufByte
        return self

    def num_pending_bits(self):
        """Return number of bits buffered but not yet written."""
        return (self._bitsBuf >> 8) & 0xff

    def _flush_bits(self):
        """Flush any pending bits to stream (pads with zeros)."""
        if self._bitsBuf != 0:
            self._buf.write(self._bitsBuf & 0xff)
            self._bitsBuf = 0

    def flush(self):
        self._flush_bits()
        return self

    def write_xml(self, s, mask=0):
        """Write XML-escaped string."""
        self._buf.write_xml(s, mask)
        return self

    def write_props(self, props):
        """Write map as props file format.

        Props files are always UTF-8 encoded.
        Keys and values are escaped for special characters.
        """
        from .Charset import Charset

        # Props files are always UTF-8
        origCharset = self._buf.charset()
        self._buf.charset(Charset.utf8())

        try:
            for key, val in props.items():
                # Escape key
                escaped_key = self._escape_props_key(str(key))
                # Escape value
                escaped_val = self._escape_props_val(str(val))
                # Write line
                self._buf.write_chars(f"{escaped_key}={escaped_val}\n")
        finally:
            self._buf.charset(origCharset)

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
        """Escape special characters in props value.

        Must escape / as \\u002f to avoid // being treated as comment when read back.
        """
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
                # Escape / to avoid // or /* being treated as comments
                result.append('\\u002f')
            elif ord(ch) > 127:
                result.append(f'\\u{ord(ch):04x}')
            else:
                result.append(ch)
        return ''.join(result)

    def close(self):
        return True

    def charset(self, val=None):
        return self._buf.charset(val)

    def endian(self, val=None):
        return self._buf.endian(val)


class BufInStream(InStream):
    """InStream wrapper for Buf."""

    def __init__(self, buf):
        super().__init__(None)  # No underlying stream - we wrap a Buf
        self._buf = buf
        self._charset = None  # Own charset field, lazy init to UTF-8 for isolation
        self._bitsBuf = 0  # Lower 8 bits = buffered byte, bits 8-15 = buffer size

    def avail(self):
        return self._buf.remaining()

    def read(self):
        """Read single byte.

        Checks BufInStream's own unread stack first, then reads directly from
        underlying bytes. This enables reading from immutable ConstBuf.
        """
        if hasattr(self, '_unread_stack') and self._unread_stack:
            return self._unread_stack.pop()
        # Read directly from _bytes to avoid ConstBuf.read() throwing
        if self._buf._pos >= self._buf._size:
            return None
        self._buf._bytes.seek(self._buf._pos)
        b = self._buf._bytes.read(1)
        if not b:
            return None
        self._buf._pos += 1
        return b[0]

    def read_buf(self, other, n):
        """Read into another Buf.

        Direct implementation that reads from underlying _bytes to avoid
        calling ConstBuf.read_buf() which throws ReadonlyErr.
        """
        n = int(n)
        avail = self._buf._size - self._buf._pos
        to_read = min(n, avail)
        if to_read <= 0:
            return None
        self._buf._bytes.seek(self._buf._pos)
        data = self._buf._bytes.read(to_read)
        self._buf._pos += len(data)
        other._bytes.seek(other._pos)
        other._bytes.write(data)
        other._pos += len(data)
        if other._pos > other._size:
            other._size = other._pos
        return len(data)

    def unread(self, n):
        """Push byte to be read next.

        For immutable ConstBuf: only the exact last-read byte can be unread.
        Unreading a different byte would modify the stream data, which is not allowed.
        """
        n = int(n) & 0xFF

        # For ConstBuf, check if we're trying to modify the data
        if self._buf.is_immutable():
            # Get the byte at current position (what would be read next)
            # If unreading would change what's read, throw ReadonlyErr
            if self._buf._pos > 0:
                self._buf._bytes.seek(self._buf._pos - 1)
                expected = self._buf._bytes.read(1)
                if expected and expected[0] != n:
                    from .Err import ReadonlyErr
                    raise ReadonlyErr.make("ConstBuf is immutable")

        if not hasattr(self, '_unread_stack'):
            self._unread_stack = []
        self._unread_stack.append(n)
        return self

    def read_all_buf(self):
        return self._buf.read_all_buf()

    def read_buf_fully(self, buf, n):
        return self._buf.read_buf_fully(buf, n)

    def peek(self):
        """Peek next byte without advancing.

        Checks this stream's unread stack first, then underlying Buf.
        """
        if hasattr(self, '_unread_stack') and self._unread_stack:
            return self._unread_stack[-1]
        return self._buf.peek()

    def read_u1(self):
        return self._buf.read_u1()

    def read_s1(self):
        return self._buf.read_s1()

    def read_u2(self):
        return self._buf.read_u2()

    def read_s2(self):
        return self._buf.read_s2()

    def read_u4(self):
        return self._buf.read_u4()

    def read_s4(self):
        return self._buf.read_s4()

    def read_s8(self):
        return self._buf.read_s8()

    def read_f4(self):
        return self._buf.read_f4()

    def read_f8(self):
        return self._buf.read_f8()

    def read_bool(self):
        return self._buf.read_bool()

    def read_utf(self):
        return self._buf.read_utf()

    def read_decimal(self):
        """Read decimal serialized as UTF string."""
        s = self._buf.read_utf()
        from .Decimal import Decimal
        return Decimal.from_str(s, True)

    def read_bits(self, num):
        """Read bits from stream.

        Args:
            num: Number of bits to read (0-64)

        Returns:
            The value containing the bits read (signed 64-bit)

        Bits are read most significant first.
        """
        # Arg checking
        num = int(num)
        if num == 0:
            return 0
        if num < 0 or num > 64:
            from .Err import ArgErr
            raise ArgErr.make(f"Bit num not 0 - 64: {num}")

        # buffer is stored as: (bufSize << 8) | bufByte
        bitsBuf = self._bitsBuf
        bufByte = bitsBuf & 0xff
        bufSize = (bitsBuf >> 8) & 0xff

        # Read bits, sourcing a new byte once we run out
        result = 0
        for _ in range(num):
            if bufSize == 0:
                b = self._buf.read()
                if b is None:
                    from .Err import IOErr
                    raise IOErr.make("End of stream")
                bufByte = b
                bufSize = 8
            bit = (bufByte >> (bufSize - 1)) & 0x1
            bufSize -= 1
            result = (result << 1) | bit

        # Update buffer
        self._bitsBuf = (bufSize << 8) | bufByte

        # Convert to signed 64-bit if high bit set (Fantom Int is signed 64-bit)
        if num == 64 and result >= 0x8000000000000000:
            result = result - 0x10000000000000000

        return result

    def num_pending_bits(self):
        """Return number of bits buffered but not yet read."""
        return (self._bitsBuf >> 8) & 0xff

    def read_props(self):
        """Read a properties file format and return as a Map.

        Props files are always UTF-8 encoded, so we temporarily switch charset.
        Delegates to StrInStream for full props parsing with escape sequences,
        comments, line continuation, etc.
        """
        from .InStream import StrInStream
        from .Charset import Charset

        # Props files are always UTF-8 - save and restore charset
        origCharset = self._buf.charset()
        self._buf.charset(Charset.utf8())

        try:
            # Read remaining buffer as string (don't normalize - props parser handles newlines)
            content = self.read_all_str(normalize=False)

            # Use StrInStream's full props parser
            return StrInStream(content).read_props()
        finally:
            self._buf.charset(origCharset)

    def read_char(self):
        """Read character using THIS stream's charset (not the underlying Buf's charset).

        This is critical for charset isolation - when the test sets in.charset(UTF-16BE),
        the InStream should read using UTF-16BE, not the underlying Buf's UTF-8.
        """
        # Check unread char stack first
        if hasattr(self, '_unread_char_stack') and self._unread_char_stack:
            return self._unread_char_stack.pop()
        if self._buf._pos >= self._buf._size:
            return None

        # Use THIS stream's charset, not the underlying Buf's charset
        charset_name = self._get_python_encoding()
        self._buf._bytes.seek(self._buf._pos)

        # Determine bytes per char based on encoding
        if 'utf-16' in charset_name.lower():
            # UTF-16 is 2 bytes per char
            if self._buf._pos + 2 > self._buf._size:
                return None
            data = self._buf._bytes.read(2)
            try:
                ch = data.decode(charset_name)
                if len(ch) >= 1:
                    self._buf._pos += 2
                    return ord(ch[0])
            except:
                return None
        else:
            # UTF-8 and others: variable length, read up to 4 bytes
            for byte_count in range(1, 5):
                if self._buf._pos + byte_count > self._buf._size:
                    break
                self._buf._bytes.seek(self._buf._pos)
                data = self._buf._bytes.read(byte_count)
                try:
                    ch = data.decode(charset_name)
                    if len(ch) == 1:
                        self._buf._pos += byte_count
                        return ord(ch)
                except:
                    continue
        return None

    def _get_python_encoding(self):
        """Get Python encoding name for this stream's charset."""
        name = self.charset().name()
        encoding_map = {
            'UTF-8': 'utf-8',
            'UTF-16BE': 'utf-16-be',
            'UTF-16LE': 'utf-16-le',
            'UTF-16': 'utf-16',
            'US-ASCII': 'ascii',
            'ISO-8859-1': 'iso-8859-1',
        }
        return encoding_map.get(name, name.lower().replace('-', '_'))

    def r_char(self):
        """Read character as int code point for Tokenizer compatibility."""
        c = self.read_char()
        return c if c is not None else None

    def unread_char(self, c):
        if not hasattr(self, '_unread_char_stack'):
            self._unread_char_stack = []
        self._unread_char_stack.append(int(c))
        return self

    def peek_char(self):
        """Peek character without advancing, using this stream's charset."""
        if hasattr(self, '_unread_char_stack') and self._unread_char_stack:
            return self._unread_char_stack[-1]
        old_pos = self._buf._pos
        ch = self.read_char()
        self._buf._pos = old_pos
        return ch

    def read_chars(self, n):
        """Read exactly n characters using this stream's charset."""
        if n < 0:
            from .Err import ArgErr
            raise ArgErr.make(f"readChars n < 0: {n}")
        chars = []
        for _ in range(int(n)):
            ch = self.read_char()
            if ch is None:
                from .Err import IOErr
                raise IOErr.make("Unexpected end of stream")
            chars.append(chr(ch))
        return ''.join(chars)

    def read_line(self, max_chars=None):
        """Read line of text using this stream's charset."""
        if self._buf._pos >= self._buf._size:
            return None
        chars = []
        count = 0
        while self._buf._pos < self._buf._size:
            if max_chars is not None and count >= max_chars:
                break
            ch = self.read_char()
            if ch is None:
                break
            if ch == ord('\n'):
                break
            if ch == ord('\r'):
                next_ch = self.peek_char()
                if next_ch == ord('\n'):
                    self.read_char()
                break
            chars.append(chr(ch))
            count += 1
        if not chars and self._buf._pos >= self._buf._size:
            return None
        return ''.join(chars)

    def read_all_str(self, normalize=True):
        """Read all remaining as string using this stream's charset.

        Direct implementation that doesn't delegate to _buf.read_all_str(),
        because ConstBuf.read_all_str() throws ReadonlyErr.
        """
        self._buf._bytes.seek(self._buf._pos)
        data = self._buf._bytes.read(self._buf._size - self._buf._pos)
        self._buf._pos = self._buf._size
        charset_name = self._get_python_encoding()
        s = data.decode(charset_name)
        if normalize:
            s = s.replace('\r\n', '\n').replace('\r', '\n')
        return s

    def read_all_lines(self):
        return self._buf.read_all_lines()

    def each_line(self, f):
        self._buf.each_line(f)

    def pipe(self, out, n=None, close=True):
        """Pipe data from this InStream to an OutStream.

        Args:
            out: The OutStream to write to
            n: Number of bytes to pipe (None = all remaining)
            close: Whether to close this stream when done

        Returns:
            Number of bytes piped

        Raises:
            IOErr: If n is specified but not enough bytes available
        """
        from .Err import IOErr

        try:
            total = 0
            if n is None:
                # Pipe all remaining
                while True:
                    b = self._buf.read()
                    if b is None:
                        break
                    out.write(b)
                    total += 1
            else:
                # Pipe exactly n bytes - throw IOErr if not enough
                for _ in range(int(n)):
                    b = self._buf.read()
                    if b is None:
                        raise IOErr.make("Unexpected end of stream")
                    out.write(b)
                    total += 1
            return total
        finally:
            if close:
                self.close()

    def read_str_token(self, max_chars=None, func=None):
        """Read string token until whitespace or func returns true.

        Args:
            max_chars: Maximum characters to read (None = unlimited)
            func: Optional function that takes a char code and returns true to terminate

        Returns:
            The string token, or None at end of stream

        Note: Uses byte-level read/unread on THIS stream (BufInStream),
        not the underlying Buf, so that subsequent read() calls see the pushed-back byte.
        """
        from .Int import Int

        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        # Read first byte using THIS stream's read()
        c = self.read()
        if c is None:
            return None

        chars = []
        while True:
            # Check termination condition
            if func is None:
                terminate = Int.is_space(c)
            else:
                terminate = func.call(c)

            if terminate:
                # Push back byte using THIS stream's unread() so subsequent read() sees it
                self.unread(c)
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self.read()
            if c is None:
                break

        return ''.join(chars)

    def read_null_terminated_str(self, max_chars=None):
        """Read string until null byte or max chars.

        Args:
            max_chars: Maximum characters to read (None = unlimited)

        Returns:
            The string, or None at end of stream
        """
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        # Read first char
        c = self._buf.read_char()
        if c is None:
            return None

        chars = []
        while True:
            if c == 0:  # null terminator
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self._buf.read_char()
            if c is None:
                break

        return ''.join(chars)

    def charset(self, val=None):
        """Get or set charset.

        BufInStream maintains its own charset for stream isolation.
        This allows wrapped streams to have different charsets from the underlying Buf.
        """
        if val is None:
            if self._charset is None:
                from .Charset import Charset
                self._charset = Charset.utf8()
            return self._charset
        self._charset = val
        return self

    def endian(self, val=None):
        """Get or set endian."""
        return self._buf.endian(val)

    def skip(self, n):
        """Skip n bytes in the stream.

        Args:
            n: Number of bytes to skip

        Returns:
            Number of bytes actually skipped
        """
        n = int(n)
        avail = self._buf.remaining()
        to_skip = min(n, avail)
        self._buf._pos += to_skip
        return to_skip

    def close(self):
        return True
