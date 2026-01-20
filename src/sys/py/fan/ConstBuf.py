#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Buf import Buf


class ConstBuf(Buf):
    """Immutable buffer.

    ConstBuf is an immutable buffer that wraps byte data.
    All modification operations raise ReadonlyErr.
    """

    def __init__(self, data=None, capacity=1024):
        super().__init__(data, capacity)
        self._immutable = True

    def typeof(self):
        from .Type import Type
        return Type.find("sys::ConstBuf")

    def is_immutable(self):
        return True

    def to_immutable(self):
        """Already immutable, return self."""
        return self

    def in_(self):
        """Get InStream for reading.

        For ConstBuf, always read from position 0 since immutable buffers
        should be readable multiple times. Each InStream starts fresh.
        """
        # Reset pos to 0 before creating InStream so reads start at beginning
        self._pos = 0
        from .Buf import BufInStream
        return BufInStream(self)

    # Override all modification methods to throw ReadonlyErr
    def _readonly_err(self):
        from .Err import ReadonlyErr
        raise ReadonlyErr.make("ConstBuf is immutable")

    def set_(self, pos, b):
        self._readonly_err()

    def __setitem__(self, pos, b):
        self._readonly_err()

    def clear(self):
        self._readonly_err()

    def fill(self, b, times):
        self._readonly_err()

    def write(self, b):
        self._readonly_err()

    def write_buf(self, other, n=None):
        self._readonly_err()

    def write_i2(self, x):
        self._readonly_err()

    def write_i4(self, x):
        self._readonly_err()

    def write_i8(self, x):
        self._readonly_err()

    def write_f4(self, x):
        self._readonly_err()

    def write_f8(self, x):
        self._readonly_err()

    def write_bool(self, x):
        self._readonly_err()

    def write_decimal(self, x):
        self._readonly_err()

    def write_utf(self, s):
        self._readonly_err()

    def write_char(self, c):
        self._readonly_err()

    def write_chars(self, s, off=0, length=None):
        self._readonly_err()

    def print_(self, obj):
        self._readonly_err()

    def print_line(self, obj=None):
        self._readonly_err()

    def unread(self, b):
        self._readonly_err()

    def unread_char(self, c):
        self._readonly_err()

    def flip(self):
        self._readonly_err()

    def seek(self, pos):
        """Seek is only allowed to position 0 for ConstBuf."""
        pos = int(pos)
        if pos == 0:
            self._pos = 0
            return self
        self._readonly_err()

    def each_line(self, f):
        self._readonly_err()

    def read_all_lines(self):
        self._readonly_err()

    def read_all_str(self, normalize=True):
        self._readonly_err()

    def read_line(self, max_chars=None):
        self._readonly_err()

    def read(self):
        self._readonly_err()

    def read_char(self):
        self._readonly_err()

    def read_buf(self, other, n):
        self._readonly_err()

    def read_all_buf(self):
        self._readonly_err()

    def peek(self):
        self._readonly_err()

    def peek_char(self):
        self._readonly_err()

    def read_bool(self):
        self._readonly_err()

    def read_buf_fully(self, buf, n):
        self._readonly_err()

    def read_chars(self, n):
        self._readonly_err()

    def read_decimal(self):
        self._readonly_err()

    def read_f4(self):
        self._readonly_err()

    def read_f8(self):
        self._readonly_err()

    def read_obj(self, options=None):
        self._readonly_err()

    def read_props(self):
        self._readonly_err()

    def read_s1(self):
        self._readonly_err()

    def read_s2(self):
        self._readonly_err()

    def read_s4(self):
        self._readonly_err()

    def read_s8(self):
        self._readonly_err()

    def read_str_token(self, max_chars=None, func=None):
        self._readonly_err()

    def read_u1(self):
        self._readonly_err()

    def read_u2(self):
        self._readonly_err()

    def read_u4(self):
        self._readonly_err()

    def read_utf(self):
        self._readonly_err()

    def sync(self):
        self._readonly_err()

    def write_obj(self, obj, options=None):
        self._readonly_err()

    def write_props(self, props):
        self._readonly_err()

    def write_xml(self, s, mask=0):
        self._readonly_err()

    def out(self):
        """Return OutStream that throws on any write operation."""
        self._readonly_err()

    def size(self, val=None):
        if val is not None:
            self._readonly_err()
        return self._size

    def capacity(self, val=None):
        """Capacity is not supported for ConstBuf - always throws ReadonlyErr."""
        self._readonly_err()

    def charset(self, val=None):
        """For ConstBuf, charset cannot be changed.

        Getting always returns UTF-8 per Fantom immutable Buf semantics.
        """
        if val is not None:
            self._readonly_err()
        from .Charset import Charset
        return Charset.utf8()

    def endian(self, val=None):
        """For ConstBuf, endian cannot be changed.

        Getting always returns big-endian per Fantom immutable Buf semantics.
        """
        if val is not None:
            self._readonly_err()
        from .Endian import Endian
        return Endian.big()

    def remaining(self):
        """For ConstBuf, remaining always returns full size.

        Immutable buffers can be read multiple times, so remaining
        is based on the full content, not the current position.
        """
        return self._size

    def pos(self, val=None):
        """For ConstBuf, pos always appears as 0 for external read operations.

        The internal _pos may change during reading, but externally
        ConstBuf always presents as if at position 0 since it can be
        read multiple times from the beginning.
        """
        if val is not None:
            # Setting pos on immutable buf is allowed (for seek operations)
            self._pos = int(val)
            return self
        # Always report pos as 0 for external callers
        return 0
