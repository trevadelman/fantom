#
# util::FloatArray - Native Python implementation
# Hand-written runtime for Python transpilation
#

import array
import struct
from fan.sys.Obj import Obj
from fan.sys.Type import Type


class FloatArray(Obj):
    """
    Optimized fixed size array of 4 or 8 byte unboxed floats.
    The array values default to zero.
    """

    # Type codes for different float sizes
    # (type_code, byte_size)
    _TYPES = {
        'F4': ('f', 4),  # 32-bit float
        'F8': ('d', 8),  # 64-bit double
    }

    def __init__(self, size, type_key):
        super().__init__()
        type_info = self._TYPES[type_key]
        self._type_key = type_key
        self._type_code = type_info[0]
        self._byte_size = type_info[1]
        self._arr = array.array(self._type_code, [0.0] * int(size))

    @staticmethod
    def make():
        """Protected constructor - use makeF4 or makeF8."""
        raise NotImplementedError("Use makeF4 or makeF8")

    @staticmethod
    def makeF4(size):
        """Create a 32-bit, 4-byte float array."""
        return FloatArray(size, 'F4')

    @staticmethod
    def makeF8(size):
        """Create a 64-bit, 8-byte float array."""
        return FloatArray(size, 'F8')

    def size(self):
        """Get number of floats in the array."""
        return len(self._arr)

    def get(self, index):
        """Get the float at the given index."""
        return self._arr[int(index)]

    def __getitem__(self, index):
        """Support [] operator for getting."""
        return self.get(index)

    def set(self, index, val):
        """Set the float at the given index."""
        self._arr[int(index)] = float(val)

    def __setitem__(self, index, val):
        """Support [] operator for setting."""
        self.set(index, val)

    def copyFrom(self, that, thatRange=None, thisOffset=0):
        """
        Copy the floats from 'that' array into this array and return this.
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
        Fill this array with the given float value.
        """
        val = float(val)
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

        for i in range(start, end + 1):
            self._arr[i] = val

        return self

    def sort(self, r=None):
        """
        Sort the floats in this array.
        """
        import math
        size = self.size()

        # Custom sort key that handles NaN properly (NaN sorts to end like Java)
        def float_sort_key(x):
            if math.isnan(x):
                return (1, 0)  # NaN sorts after everything
            return (0, x)

        if r is None:
            # Sort entire array
            sorted_arr = sorted(self._arr, key=float_sort_key)
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
            slice_list.sort(key=float_sort_key)
            for i, val in enumerate(slice_list):
                self._arr[start + i] = val

        return self

    def typeof(self):
        return Type.find("util::FloatArray")
