#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class StrBuf(Obj):
    """StrBuf is a mutable sequence of characters for building strings."""

    def __init__(self, capacity=16):
        self._buf = []
        self._capacity = capacity

    @staticmethod
    def make(capacity=16):
        """Create StrBuf with initial capacity."""
        return StrBuf(int(capacity) if capacity else 16)

    #################################################################
    # Accessors
    #################################################################

    def is_empty(self):
        """Return true if size is zero."""
        return len(self._buf) == 0

    def size(self):
        """Return number of characters."""
        return len(self._buf)

    @property
    def capacity(self):
        """Return current capacity."""
        return max(self._capacity, len(self._buf))

    @capacity.setter
    def capacity(self, size):
        """Set capacity."""
        self._capacity = int(size)

    def set_capacity(self, size):
        """Ensure capacity for at least size characters."""
        self._capacity = int(size)
        return self

    def get(self, index):
        """Get character at index as Int codepoint. Supports negative indexing."""
        if index < 0:
            index = len(self._buf) + index
        if index < 0 or index >= len(self._buf):
            from .Err import IndexErr
            raise IndexErr.make(f"Index {index} out of bounds")
        return ord(self._buf[index])

    def __getitem__(self, index):
        """Support [] operator for getting characters."""
        if isinstance(index, slice):
            # Range access
            from .Range import Range
            if hasattr(index, '_start'):
                r = index
            else:
                # Convert Python slice to Range
                start = index.start or 0
                stop = index.stop or len(self._buf)
                return ''.join(self._buf[start:stop])
        return self.get(index)

    def get_range(self, r):
        """Get substring for range."""
        from .Err import IndexErr
        n = len(self._buf)

        # Use Range's index resolution methods which handle negative indices
        # and throw IndexErr for out of bounds
        s = r.start_(n)
        e = r.end_(n)

        # Check for inverted range (e+1 < s means empty/invalid)
        if e + 1 < s:
            raise IndexErr.make(str(r))

        return ''.join(self._buf[s:e+1])

    def set_(self, index, ch):
        """Set character at index. Supports negative indexing."""
        if index < 0:
            index = len(self._buf) + index
        if index < 0 or index >= len(self._buf):
            from .Err import IndexErr
            raise IndexErr.make(f"Index {index} out of bounds")
        self._buf[index] = chr(int(ch))
        return self

    def __setitem__(self, index, ch):
        """Support [] operator for setting characters."""
        self.set_(index, ch)

    #################################################################
    # Modification
    #################################################################

    def add(self, obj):
        """Append string representation of object."""
        from .ObjUtil import ObjUtil
        s = "null" if obj is None else ObjUtil.to_str(obj)
        self._buf.extend(list(s))
        return self

    def add_char(self, ch):
        """Append single character by codepoint."""
        self._buf.append(chr(int(ch)))
        return self

    def add_range(self, s, r):
        """Append substring of s defined by range."""
        n = len(s)
        start = r._start
        end = r._end
        exclusive = r._exclusive

        # Convert negative indices
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end

        # Apply exclusive adjustment
        if not exclusive:
            end = end + 1

        self._buf.extend(list(s[start:end]))
        return self

    def add_trim(self, x):
        """Add string with its leading and trailing whitespace trimmed."""
        from .ObjUtil import ObjUtil
        s = "null" if x is None else ObjUtil.to_str(x)
        self._buf.extend(list(s.strip()))
        return self

    def join(self, obj, sep=" "):
        """Append object with separator if not empty."""
        from .ObjUtil import ObjUtil
        s = "null" if obj is None else ObjUtil.to_str(obj)
        if len(self._buf) > 0:
            self._buf.extend(list(sep))
        self._buf.extend(list(s))
        return self

    def join_not_null(self, obj, sep=" "):
        """Append object with separator if object is not null and buffer not empty."""
        if obj is not None:
            self.join(obj, sep)
        return self

    def insert(self, index, obj):
        """Insert string representation at index."""
        from .ObjUtil import ObjUtil
        s = "null" if obj is None else ObjUtil.to_str(obj)
        index = int(index)
        if index < 0:
            index = len(self._buf) + index
        if index < 0 or index > len(self._buf):
            from .Err import IndexErr
            raise IndexErr.make(f"Index {index} out of bounds")
        for i, c in enumerate(s):
            self._buf.insert(index + i, c)
        return self

    def trim_end(self):
        """Remove any trailing whitespace in the buffer."""
        while self._buf and self._buf[-1] in ' \t\n\r\f\v':
            self._buf.pop()
        return self

    def remove(self, index):
        """Remove character at index."""
        index = int(index)
        if index < 0:
            index = len(self._buf) + index
        if index < 0 or index >= len(self._buf):
            from .Err import IndexErr
            raise IndexErr.make(f"Index {index} out of bounds")
        del self._buf[index]
        return self

    def remove_range(self, r):
        """Remove characters in range."""
        n = len(self._buf)
        start = r._start
        end = r._end
        exclusive = r._exclusive

        # Convert negative indices
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end

        # Apply exclusive adjustment
        if not exclusive:
            end = end + 1

        # Validate range
        if start < 0 or end > n or end < start:
            from .Err import IndexErr
            raise IndexErr.make(f"Range {r}")

        del self._buf[start:end]
        return self

    def replace_range(self, r, s):
        """Replace characters in range with string."""
        n = len(self._buf)
        start = r._start
        end = r._end
        exclusive = r._exclusive

        # Convert negative indices
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end

        # Apply exclusive adjustment
        if not exclusive:
            end = end + 1

        # Validate range
        if start < 0 or end > n or end < start:
            from .Err import IndexErr
            raise IndexErr.make(f"Range {r}")

        self._buf[start:end] = list(s)
        return self

    def reverse(self):
        """Reverse characters in place."""
        self._buf.reverse()
        return self

    def clear(self):
        """Clear all characters."""
        self._buf = []
        return self

    #################################################################
    # Conversion
    #################################################################

    def to_str(self):
        """Return current string value."""
        return ''.join(self._buf)

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return f"StrBuf({self.to_str()!r})"

    #################################################################
    # OutStream Integration
    #################################################################

    def out(self):
        """Return an OutStream that writes to this StrBuf."""
        return StrBufOutStream(self)

    #################################################################
    # Type
    #################################################################

    def typeof(self):
        from .Type import Type
        return Type.find("sys::StrBuf")


class StrBufOutStream:
    """OutStream implementation that writes to a StrBuf."""

    def __init__(self, buf):
        self._buf = buf
        self._charset_obj = None  # Lazy init

    def charset(self, val=None):
        """Get or set charset (always UTF-8 for StrBuf, set is ignored)."""
        if val is None:
            if self._charset_obj is None:
                from .Charset import Charset
                self._charset_obj = Charset.utf8()
            return self._charset_obj
        # Setting charset is ignored for StrBuf - it's always UTF-8
        return self

    def write_char(self, ch):
        """Write single character."""
        self._buf.add_char(ch)
        return self

    def write_chars(self, s, off=0, length=None):
        """Write string of characters."""
        if length is None:
            self._buf.add(s[off:])
        else:
            self._buf.add(s[off:off + length])
        return self

    def print_(self, obj):
        """Print object."""
        self._buf.add(obj)
        return self

    # Alias for transpiled code that uses 'print' directly
    print = print_

    def print_line(self, obj=""):
        """Print object with newline."""
        self._buf.add(obj).add_char(ord('\n'))
        return self

    def write_xml(self, s, flags=0):
        """Write string with XML escaping.

        Args:
            s: String to write
            flags: Bitmask of options:
                   - xmlEscNewlines = 0x01
                   - xmlEscQuotes = 0x02
                   - xmlEscUnicode = 0x04

        Note: Fantom only escapes < and & by default, not >
        """
        xml_esc_quotes = 0x02  # OutStream.xmlEscQuotes
        result = []
        for ch in str(s):
            if ch == '<':
                result.append('&lt;')
            elif ch == '&':
                result.append('&amp;')
            elif ch == '"' and (flags & xml_esc_quotes):
                result.append('&quot;')
            elif ch == "'" and (flags & xml_esc_quotes):
                result.append('&#39;')
            else:
                result.append(ch)
        self._buf.add(''.join(result))
        return self

    def write_props(self, props, close=True):
        """Write map as properties file format."""
        for key, val in props.items() if hasattr(props, 'items') else []:
            # Escape special characters in value
            escaped_val = val.replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n')
            self._buf.add(f"{key}={escaped_val}\n")
        if close:
            self.close()
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

    def flush(self):
        """Flush (no-op for StrBuf)."""
        return self

    def close(self):
        """Close (no-op for StrBuf)."""
        return True

    # Methods that are unsupported for character-based output
    def write(self, byte):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def write_buf(self, buf, n=None):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def write_i2(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def write_i4(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def write_i8(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def write_f4(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def write_f8(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def write_utf(self, s):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")
