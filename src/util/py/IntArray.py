#
# util::IntArray - Native Python implementation
# Hand-written runtime for Python transpilation
#

import array
import struct
from fan.sys.Obj import Obj
from fan.sys.Type import Type


class IntArray(Obj):
    """
    Optimized fixed size array of 1, 2, 4, or 8 byte unboxed integers.
    The array values default to zero.
    """

    # Type codes for different integer sizes
    # (type_code, signed, byte_size, min_val, max_val, mask)
    _TYPES = {
        'S1': ('b', True, 1, -128, 127, 0xFF),
        'U1': ('B', False, 1, 0, 255, 0xFF),
        'S2': ('h', True, 2, -32768, 32767, 0xFFFF),
        'U2': ('H', False, 2, 0, 65535, 0xFFFF),
        'S4': ('i', True, 4, -2147483648, 2147483647, 0xFFFFFFFF),
        'U4': ('I', False, 4, 0, 4294967295, 0xFFFFFFFF),
        'S8': ('q', True, 8, None, None, None),  # Full 64-bit
    }

    def __init__(self, size, type_key):
        super().__init__()
        type_info = self._TYPES[type_key]
        self._type_key = type_key
        self._type_code = type_info[0]
        self._signed = type_info[1]
        self._byte_size = type_info[2]
        self._min_val = type_info[3]
        self._max_val = type_info[4]
        self._mask = type_info[5]
        self._arr = array.array(self._type_code, [0] * int(size))

    @staticmethod
    def make():
        """Protected constructor - use makeS1, makeU1, etc."""
        raise NotImplementedError("Use makeS1, makeU1, makeS2, etc.")

    @staticmethod
    def make_s1(size):
        """Create a signed 8-bit, 1-byte integer array (-128 to 127)."""
        return IntArray(size, 'S1')

    @staticmethod
    def make_u1(size):
        """Create an unsigned 8-bit, 1-byte integer array (0 to 255)."""
        return IntArray(size, 'U1')

    @staticmethod
    def make_s2(size):
        """Create a signed 16-bit, 2-byte integer array (-32_768 to 32_767)."""
        return IntArray(size, 'S2')

    @staticmethod
    def make_u2(size):
        """Create an unsigned 16-bit, 2-byte integer array (0 to 65_535)."""
        return IntArray(size, 'U2')

    @staticmethod
    def make_s4(size):
        """Create a signed 32-bit, 4-byte integer array."""
        return IntArray(size, 'S4')

    @staticmethod
    def make_u4(size):
        """Create an unsigned 32-bit, 4-byte integer array (0 to 4_294_967_295)."""
        return IntArray(size, 'U4')

    @staticmethod
    def make_s8(size):
        """Create a signed 64-bit, 8-byte integer array."""
        return IntArray(size, 'S8')

    def size(self):
        """Get number of integers in the array."""
        return len(self._arr)

    def get(self, index):
        """Get the integer at the given index."""
        return self._arr[int(index)]

    def __getitem__(self, index):
        """Support [] operator for getting."""
        return self.get(index)

    def set(self, index, val):
        """Set the integer at the given index."""
        val = int(val)
        # For unsigned types, mask the value
        if not self._signed and self._mask is not None:
            val = val & self._mask
        # For signed types with overflow, also mask
        elif self._signed and self._mask is not None:
            val = val & self._mask
            # Convert to signed if needed
            if self._type_key == 'S1' and val > 127:
                val = val - 256
            elif self._type_key == 'S2' and val > 32767:
                val = val - 65536
            elif self._type_key == 'S4' and val > 2147483647:
                val = val - 4294967296
        self._arr[int(index)] = val

    def __setitem__(self, index, val):
        """Support [] operator for setting."""
        self.set(index, val)

    def copy_from(self, that, thatRange=None, thisOffset=0):
        """
        Copy the integers from 'that' array into this array and return this.
        """
        from fan.sys.Err import ArgErr

        # Check type compatibility
        if self._type_key != that._type_key:
            raise ArgErr.make(f"Mismatched arrays: {self._type_key} != {that._type_key}")

        if thisOffset is None:
            thisOffset = 0
        thisOffset = int(thisOffset)

        thatSize = that.size()

        if thatRange is None:
            start = 0
            end = thatSize
        else:
            start = thatRange._start
            end = thatRange._end

            # Handle negative indices
            if start < 0:
                start = thatSize + start
            if end < 0:
                end = thatSize + end

            # Handle exclusive range
            if not thatRange._exclusive:
                end = end + 1

        # Copy elements
        for i in range(start, end):
            self._arr[thisOffset + (i - start)] = that._arr[i]

        return self

    def fill(self, val, r=None):
        """
        Fill this array with the given integer value.
        """
        val = int(val)
        size = self.size()

        if r is None:
            start = 0
            end = size - 1
        else:
            start = r._start
            end = r._end

            # Handle negative indices
            if start < 0:
                start = size + start
            if end < 0:
                end = size + end

            # Handle exclusive range
            if r._exclusive:
                end = end - 1

        # For unsigned types, mask the value
        if not self._signed and self._mask is not None:
            val = val & self._mask

        for i in range(start, end + 1):
            self._arr[i] = val

        return self

    def sort(self, r=None):
        """
        Sort the integers in this array.
        """
        size = self.size()

        if r is None:
            # Sort entire array
            sorted_arr = sorted(self._arr)
            for i in range(size):
                self._arr[i] = sorted_arr[i]
        else:
            start = r._start
            end = r._end

            # Handle negative indices
            if start < 0:
                start = size + start
            if end < 0:
                end = size + end

            # Handle exclusive range
            if r._exclusive:
                end = end - 1

            # Sort the specified range
            slice_list = list(self._arr[start:end + 1])
            slice_list.sort()
            for i, val in enumerate(slice_list):
                self._arr[start + i] = val

        return self

    def typeof(self):
        return Type.find("util::IntArray")
