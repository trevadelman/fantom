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
    def fromHex(s):
        """Create Buf from hex string."""
        # Filter non-hex chars
        hex_chars = ''.join(c for c in str(s) if c in '0123456789abcdefABCDEF')
        if len(hex_chars) % 2 != 0:
            from .Err import IOErr
            raise IOErr.make("Invalid hex str")
        data = bytes.fromhex(hex_chars)
        return Buf(data)

    @staticmethod
    def fromBase64(s):
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
    def fromBytes(data):
        """Create Buf from bytes."""
        return Buf(data)

    #################################################################
    # Identity
    #################################################################

    def typeof(self):
        from .Type import Type
        return Type.find("sys::Buf")

    def toStr(self):
        return f"Buf(pos={self._pos} size={self._size})"

    def __str__(self):
        return self.toStr()

    def equals(self, other):
        return self is other

    def bytesEqual(self, other):
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

    def isEmpty(self):
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
                return Int.maxVal()
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
        """Seek to position. Negative seeks from end."""
        pos = int(pos)
        if pos < 0:
            pos = self._size + pos
        if pos < 0 or pos > self._size:
            from .Err import IndexErr
            raise IndexErr.make(str(pos))
        self._pos = pos
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

    def getRange(self, r):
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

    def toImmutable(self):
        """Return an immutable copy of this Buf."""
        # In Python, we just return a copy with immutable flag
        data = self._get_data()
        buf = Buf(data)
        buf._immutable = True
        return buf

    def isImmutable(self):
        """Return true if this Buf is immutable."""
        return getattr(self, '_immutable', False)

    #################################################################
    # Modification
    #################################################################

    def set(self, pos, b):
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
        self.set(pos, b)

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

    def writeBuf(self, other, n=None):
        """Write from another Buf."""
        if n is None:
            n = other.remaining()
        n = int(n)
        other._bytes.seek(other._pos)
        data = other._bytes.read(n)
        other._pos += len(data)
        self._bytes.seek(self._pos)
        self._bytes.write(data)
        self._pos += len(data)
        if self._pos > self._size:
            self._size = self._pos
        return self

    def writeI2(self, x):
        """Write 16-bit int (handles full unsigned range)."""
        x = int(x) & 0xFFFF  # Mask to 16-bit
        if self._is_big_endian():
            self.write((x >> 8) & 0xFF)
            self.write(x & 0xFF)
        else:
            self.write(x & 0xFF)
            self.write((x >> 8) & 0xFF)
        return self

    def writeI4(self, x):
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

    def writeI8(self, x):
        """Write 64-bit signed int."""
        fmt = '>q' if self._is_big_endian() else '<q'
        self._write_struct(fmt, int(x))
        return self

    def writeF4(self, x):
        """Write 32-bit float."""
        fmt = '>f' if self._is_big_endian() else '<f'
        self._write_struct(fmt, float(x))
        return self

    def writeF8(self, x):
        """Write 64-bit float."""
        fmt = '>d' if self._is_big_endian() else '<d'
        self._write_struct(fmt, float(x))
        return self

    def writeBool(self, x):
        """Write boolean as byte."""
        return self.write(1 if x else 0)

    def writeDecimal(self, x):
        """Write decimal as string (Fantom serialization)."""
        s = str(float(x))
        return self.writeUtf(s)

    def writeUtf(self, s):
        """Write modified UTF-8 string."""
        data = str(s).encode('utf-8')
        self.writeI2(len(data))
        self._bytes.seek(self._pos)
        self._bytes.write(data)
        self._pos += len(data)
        if self._pos > self._size:
            self._size = self._pos
        return self

    def writeChar(self, c):
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

    def writeChars(self, s, off=0, length=None):
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
        s = "null" if obj is None else ObjUtil.toStr(obj)
        return self.writeChars(s)

    # Alias for transpiled code
    print = print_

    def printLine(self, obj=None):
        """Print with newline."""
        if obj is not None:
            self.print_(obj)
        return self.writeChar(ord('\n'))

    def writeXml(self, s, mask=0):
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
                self._writeXmlEsc(code)
            # Newlines
            elif ch == '\n' or ch == '\r':
                if not escNewlines:
                    self.writeChar(code)
                else:
                    self._writeXmlEsc(code)
            # XML special chars
            elif ch == '<':
                self.writeChars("&lt;")
            elif ch == '>':
                if i > 0 and s[i-1] != ']':
                    self.writeChar(code)
                else:
                    self.writeChars("&gt;")
            elif ch == '&':
                self.writeChars("&amp;")
            elif ch == '"':
                if not escQuotes:
                    self.writeChar(code)
                else:
                    self.writeChars("&quot;")
            elif ch == "'":
                if not escQuotes:
                    self.writeChar(code)
                else:
                    self.writeChars("&#39;")
            # Unicode chars > 0xf7
            elif code > 0xf7 and escUnicode:
                self._writeXmlEsc(code)
            # Normal chars
            else:
                self.writeChar(code)

        return self

    def _writeXmlEsc(self, ch):
        """Write XML numeric character escape."""
        hex_chars = "0123456789abcdef"
        self.writeChars("&#x")
        if ch > 0xff:
            self.writeChar(ord(hex_chars[(ch >> 12) & 0xf]))
            self.writeChar(ord(hex_chars[(ch >> 8) & 0xf]))
        self.writeChar(ord(hex_chars[(ch >> 4) & 0xf]))
        self.writeChar(ord(hex_chars[ch & 0xf]))
        self.writeChars(";")

    #################################################################
    # InStream Operations (read)
    #################################################################

    def in_(self):
        """Get InStream for reading."""
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

    def readBuf(self, other, n):
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

    def readAllBuf(self):
        """Read remaining as new Buf."""
        self._bytes.seek(self._pos)
        data = self._bytes.read(self._size - self._pos)
        self._pos = self._size
        return Buf(data)

    def readBufFully(self, buf, n):
        """Read exactly n bytes into buf, then flip buf for reading."""
        n = int(n)
        if buf is None:
            buf = Buf.make(n)
        result = self.readBuf(buf, n)
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

    def readU1(self):
        """Read unsigned 8-bit."""
        b = self.read()
        if b is None:
            from .Err import IOErr
            raise IOErr.make("Unexpected end of stream")
        return b

    def readS1(self):
        """Read signed 8-bit."""
        b = self.readU1()
        return b if b < 128 else b - 256

    def readU2(self):
        """Read unsigned 16-bit."""
        fmt = '>H' if self._is_big_endian() else '<H'
        return self._read_struct(fmt)

    def readS2(self):
        """Read signed 16-bit."""
        fmt = '>h' if self._is_big_endian() else '<h'
        return self._read_struct(fmt)

    def readU4(self):
        """Read unsigned 32-bit."""
        fmt = '>I' if self._is_big_endian() else '<I'
        return self._read_struct(fmt)

    def readS4(self):
        """Read signed 32-bit."""
        fmt = '>i' if self._is_big_endian() else '<i'
        return self._read_struct(fmt)

    def readS8(self):
        """Read signed 64-bit."""
        fmt = '>q' if self._is_big_endian() else '<q'
        return self._read_struct(fmt)

    def readF4(self):
        """Read 32-bit float."""
        fmt = '>f' if self._is_big_endian() else '<f'
        return self._read_struct(fmt)

    def readF8(self):
        """Read 64-bit float."""
        fmt = '>d' if self._is_big_endian() else '<d'
        return self._read_struct(fmt)

    def readBool(self):
        """Read boolean."""
        return self.readU1() != 0

    def readUtf(self):
        """Read modified UTF-8 string."""
        length = self.readU2()
        self._bytes.seek(self._pos)
        data = self._bytes.read(length)
        self._pos += len(data)
        return data.decode('utf-8')

    def readChar(self):
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

    def unreadChar(self, c):
        """Push character to be read next (stack behavior)."""
        self._unread_char_stack.append(int(c))
        return self

    def peekChar(self):
        """Peek character without advancing."""
        # Check unread char stack first
        if self._unread_char_stack:
            return self._unread_char_stack[-1]  # peek top of stack without pop
        old_pos = self._pos
        ch = self.readChar()
        self._pos = old_pos
        return ch

    def readChars(self, n):
        """Read n characters."""
        if n < 0:
            from .Err import ArgErr
            raise ArgErr.make(f"readChars n < 0: {n}")
        chars = []
        for _ in range(int(n)):
            ch = self.readChar()
            if ch is None:
                break
            chars.append(chr(ch))
        return ''.join(chars)

    def readLine(self, max_chars=None):
        """Read line of text."""
        if self._pos >= self._size:
            return None
        chars = []
        count = 0
        while self._pos < self._size:
            if max_chars is not None and count >= max_chars:
                break
            ch = self.readChar()
            if ch is None:
                break
            if ch == ord('\n'):
                break
            if ch == ord('\r'):
                # Check for \r\n
                next_ch = self.peekChar()
                if next_ch == ord('\n'):
                    self.readChar()
                break
            chars.append(chr(ch))
            count += 1
        if not chars and self._pos >= self._size:
            return None
        return ''.join(chars)

    def readAllStr(self, normalize=True):
        """Read all remaining as string."""
        self._bytes.seek(self._pos)
        data = self._bytes.read(self._size - self._pos)
        self._pos = self._size
        charset_name = self._get_python_encoding()
        s = data.decode(charset_name)
        if normalize:
            s = s.replace('\r\n', '\n').replace('\r', '\n')
        return s

    def readAllLines(self):
        """Read all lines."""
        from .List import List
        lines = []
        while True:
            line = self.readLine()
            if line is None:
                break
            lines.append(line)
        return List.fromLiteral(lines, "sys::Str")

    def eachLine(self, f):
        """Iterate each line."""
        while True:
            line = self.readLine()
            if line is None:
                break
            f.call(line)

    #################################################################
    # Conversion
    #################################################################

    def toHex(self):
        """Convert to hex string."""
        return self._get_data().hex()

    def toBase64(self):
        """Convert to base64 string."""
        return base64.b64encode(self._get_data()).decode('ascii')

    def toBase64Uri(self):
        """Convert to URL-safe base64."""
        return base64.urlsafe_b64encode(self._get_data()).decode('ascii').rstrip('=')

    def toFile(self, uri):
        """Write buffer contents to a file.

        Args:
            uri: The Uri or string path to write to

        Returns:
            The File that was written
        """
        from .File import File
        from .Uri import Uri

        if isinstance(uri, str):
            uri = Uri.fromStr(uri)
        f = File(uri)
        f._path.parent.mkdir(parents=True, exist_ok=True)
        f._path.write_bytes(self._get_data())
        return f

    def toDigest(self, algorithm):
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

    def crc(self, algorithm):
        """Compute CRC checksum."""
        import zlib
        if algorithm == "CRC-32":
            return zlib.crc32(self._get_data()) & 0xFFFFFFFF
        if algorithm == "CRC-32-Adler":
            return zlib.adler32(self._get_data()) & 0xFFFFFFFF
        from .Err import ArgErr
        raise ArgErr.make(f"Unknown CRC algorithm: {algorithm}")

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


class BufOutStream:
    """OutStream wrapper for Buf."""

    def __init__(self, buf):
        self._buf = buf
        self._bitsBuf = 0  # Lower 8 bits = buffered byte, bits 8-15 = buffer size

    def write(self, b):
        self._buf.write(b)
        return self

    def writeBuf(self, other, n=None):
        self._buf.writeBuf(other, n)
        return self

    def writeI2(self, x):
        self._buf.writeI2(x)
        return self

    def writeI4(self, x):
        self._buf.writeI4(x)
        return self

    def writeI8(self, x):
        self._buf.writeI8(x)
        return self

    def writeF4(self, x):
        self._buf.writeF4(x)
        return self

    def writeF8(self, x):
        self._buf.writeF8(x)
        return self

    def writeBool(self, x):
        self._buf.writeBool(x)
        return self

    def writeDecimal(self, x):
        self._buf.writeDecimal(x)
        return self

    def writeUtf(self, s):
        self._buf.writeUtf(s)
        return self

    def writeChar(self, c):
        self._buf.writeChar(c)
        return self

    def writeChars(self, s, off=0, length=None):
        self._buf.writeChars(s, off, length)
        return self

    def print_(self, obj):
        self._buf.print_(obj)
        return self

    print = print_

    def printLine(self, obj=None):
        self._buf.printLine(obj)
        return self

    def writeBits(self, val, num):
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

    def numPendingBits(self):
        """Return number of bits buffered but not yet written."""
        return (self._bitsBuf >> 8) & 0xff

    def _flushBits(self):
        """Flush any pending bits to stream (pads with zeros)."""
        if self._bitsBuf != 0:
            self._buf.write(self._bitsBuf & 0xff)
            self._bitsBuf = 0

    def flush(self):
        self._flushBits()
        return self

    def writeXml(self, s, mask=0):
        """Write XML-escaped string."""
        self._buf.writeXml(s, mask)
        return self

    def writeProps(self, props):
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
                escaped_key = self._escapePropsKey(str(key))
                # Escape value
                escaped_val = self._escapePropsVal(str(val))
                # Write line
                self._buf.writeChars(f"{escaped_key}={escaped_val}\n")
        finally:
            self._buf.charset(origCharset)

        return self

    def _escapePropsKey(self, s):
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

    def _escapePropsVal(self, s):
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


class BufInStream:
    """InStream wrapper for Buf."""

    def __init__(self, buf):
        self._buf = buf
        self._bitsBuf = 0  # Lower 8 bits = buffered byte, bits 8-15 = buffer size

    def avail(self):
        return self._buf.remaining()

    def read(self):
        return self._buf.read()

    def readBuf(self, other, n):
        return self._buf.readBuf(other, n)

    def unread(self, n):
        self._buf.unread(n)
        return self

    def readAllBuf(self):
        return self._buf.readAllBuf()

    def readBufFully(self, buf, n):
        return self._buf.readBufFully(buf, n)

    def peek(self):
        return self._buf.peek()

    def readU1(self):
        return self._buf.readU1()

    def readS1(self):
        return self._buf.readS1()

    def readU2(self):
        return self._buf.readU2()

    def readS2(self):
        return self._buf.readS2()

    def readU4(self):
        return self._buf.readU4()

    def readS4(self):
        return self._buf.readS4()

    def readS8(self):
        return self._buf.readS8()

    def readF4(self):
        return self._buf.readF4()

    def readF8(self):
        return self._buf.readF8()

    def readBool(self):
        return self._buf.readBool()

    def readUtf(self):
        return self._buf.readUtf()

    def readDecimal(self):
        """Read decimal serialized as UTF string."""
        s = self._buf.readUtf()
        from .Decimal import Decimal
        return Decimal.fromStr(s, True)

    def readBits(self, num):
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

    def numPendingBits(self):
        """Return number of bits buffered but not yet read."""
        return (self._bitsBuf >> 8) & 0xff

    def readProps(self):
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
            content = self.readAllStr(normalize=False)

            # Use StrInStream's full props parser
            return StrInStream(content).readProps()
        finally:
            self._buf.charset(origCharset)

    def readChar(self):
        return self._buf.readChar()

    def unreadChar(self, c):
        self._buf.unreadChar(c)
        return self

    def peekChar(self):
        return self._buf.peekChar()

    def readChars(self, n):
        return self._buf.readChars(n)

    def readLine(self, max_chars=None):
        return self._buf.readLine(max_chars)

    def readAllStr(self, normalize=True):
        return self._buf.readAllStr(normalize)

    def readAllLines(self):
        return self._buf.readAllLines()

    def eachLine(self, f):
        self._buf.eachLine(f)

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

    def readStrToken(self, max_chars=None, func=None):
        """Read string token until whitespace or func returns true.

        Args:
            max_chars: Maximum characters to read (None = unlimited)
            func: Optional function that takes a char code and returns true to terminate

        Returns:
            The string token, or None at end of stream
        """
        from .Int import Int

        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""

        # Read first char
        c = self._buf.readChar()
        if c is None:
            return None

        chars = []
        while True:
            # Check termination condition
            if func is None:
                terminate = Int.isSpace(c)
            else:
                terminate = func.call(c)

            if terminate:
                self._buf.unreadChar(c)
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self._buf.readChar()
            if c is None:
                break

        return ''.join(chars)

    def readNullTerminatedStr(self, max_chars=None):
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
        c = self._buf.readChar()
        if c is None:
            return None

        chars = []
        while True:
            if c == 0:  # null terminator
                break

            chars.append(chr(c))
            if len(chars) >= max_len:
                break

            c = self._buf.readChar()
            if c is None:
                break

        return ''.join(chars)

    def charset(self, val=None):
        """Get or set charset (delegates to underlying buf)."""
        return self._buf.charset(val)

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
