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

    def isEmpty(self):
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

    def setCapacity(self, size):
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

    def getRange(self, r):
        """Get substring for range."""
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

        if end < start:
            from .Err import IndexErr
            raise IndexErr.make(f"Range {r}")

        return ''.join(self._buf[start:end])

    def set(self, index, ch):
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
        self.set(index, ch)

    #################################################################
    # Modification
    #################################################################

    def add(self, obj):
        """Append string representation of object."""
        from .ObjUtil import ObjUtil
        s = "null" if obj is None else ObjUtil.toStr(obj)
        self._buf.extend(list(s))
        return self

    def addChar(self, ch):
        """Append single character by codepoint."""
        self._buf.append(chr(int(ch)))
        return self

    def addRange(self, s, r):
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

    def join(self, obj, sep=" "):
        """Append object with separator if not empty."""
        from .ObjUtil import ObjUtil
        s = "null" if obj is None else ObjUtil.toStr(obj)
        if len(self._buf) > 0:
            self._buf.extend(list(sep))
        self._buf.extend(list(s))
        return self

    def joinNotNull(self, obj, sep=" "):
        """Append object with separator if object is not null and buffer not empty."""
        if obj is not None:
            self.join(obj, sep)
        return self

    def insert(self, index, obj):
        """Insert string representation at index."""
        from .ObjUtil import ObjUtil
        s = "null" if obj is None else ObjUtil.toStr(obj)
        index = int(index)
        if index < 0:
            index = len(self._buf) + index
        if index < 0 or index > len(self._buf):
            from .Err import IndexErr
            raise IndexErr.make(f"Index {index} out of bounds")
        for i, c in enumerate(s):
            self._buf.insert(index + i, c)
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

    def removeRange(self, r):
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

    def replaceRange(self, r, s):
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

    def toStr(self):
        """Return current string value."""
        return ''.join(self._buf)

    def __str__(self):
        return self.toStr()

    def __repr__(self):
        return f"StrBuf({self.toStr()!r})"

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
        self._charset = "UTF-8"

    @property
    def charset(self):
        """Return charset (always UTF-8 for StrBuf)."""
        class Charset:
            def __init__(self):
                self.name = "UTF-8"
        return Charset()

    def writeChar(self, ch):
        """Write single character."""
        self._buf.addChar(ch)
        return self

    def writeChars(self, s, off=0, length=None):
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

    def printLine(self, obj=""):
        """Print object with newline."""
        self._buf.add(obj).addChar(ord('\n'))
        return self

    def writeXml(self, s, flags=0):
        """Write string with XML escaping.

        Args:
            s: String to write
            flags: Bitmask of options (xmlEscQuotes=0x01 to escape quotes as entities)

        Note: Fantom only escapes < and & by default, not >
        """
        xml_esc_quotes = 1  # OutStream.xmlEscQuotes
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

    def writeProps(self, props):
        """Write map as properties file format."""
        for key, val in props.items() if hasattr(props, 'items') else []:
            # Escape special characters in value
            escaped_val = val.replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n')
            self._buf.add(f"{key}={escaped_val}\n")
        return self

    def writeObj(self, obj, options=None):
        """Write serialized object representation."""
        # Simplified implementation - just convert to string
        from .ObjUtil import ObjUtil
        self._buf.add(ObjUtil.toStr(obj))
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

    def writeBuf(self, buf, n=None):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def writeI2(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def writeI4(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def writeI8(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def writeF4(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def writeF8(self, n):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")

    def writeUtf(self, s):
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("Binary write not supported for StrBuf.out")
