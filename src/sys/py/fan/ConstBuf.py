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

    def size(self, val=None):
        if val is not None:
            self._readonly_err()
        return self._size

    def capacity(self, val=None):
        if val is not None:
            self._readonly_err()
        return self._capacity
