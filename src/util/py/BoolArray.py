#
# util::BoolArray - Native Python implementation
# Hand-written runtime for Python transpilation
#
# Uses bit-packed int array for efficient storage (like Java implementation).
# Each int stores 32 boolean values.
#

from fan.sys.Obj import Obj
from fan.sys.Type import Type


class BoolArray(Obj):
    """
    Optimized fixed size array of booleans using bit-packed storage.
    The array values default to false.
    """

    def __init__(self, size):
        super().__init__()
        self._size = int(size)
        # Each int stores 32 bits, so we need (size >> 5) + 1 ints
        num_words = (self._size >> 5) + 1
        self._words = [0] * num_words

    @staticmethod
    def make(size):
        """Create a boolean array of given size."""
        return BoolArray(size)

    def size(self):
        """Get number of booleans in the array."""
        return self._size

    def get(self, index):
        """Get the boolean at the given index."""
        i = int(index)
        word_index = i >> 5  # i / 32
        bit_mask = 1 << (i & 0x1F)  # i % 32
        return (self._words[word_index] & bit_mask) != 0

    def __getitem__(self, index):
        """Support [] operator for getting."""
        return self.get(index)

    def set(self, index, val):
        """Set the boolean at the given index."""
        i = int(index)
        word_index = i >> 5  # i / 32
        bit_mask = 1 << (i & 0x1F)  # i % 32
        if val:
            self._words[word_index] |= bit_mask
        else:
            self._words[word_index] &= ~bit_mask

    def __setitem__(self, index, val):
        """Support [] operator for setting."""
        self.set(index, val)

    def get_and_set(self, index, val):
        """
        Get the current boolean value at index, then set it to val.
        Returns the previous value.
        """
        i = int(index)
        word_index = i >> 5
        bit_mask = 1 << (i & 0x1F)
        prev = (self._words[word_index] & bit_mask) != 0
        if val:
            self._words[word_index] |= bit_mask
        else:
            self._words[word_index] &= ~bit_mask
        return prev

    def fill(self, val, r=None):
        """
        Fill this array with the given boolean value.
        """
        if r is None and not val:
            return self.clear()

        size = self._size

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
            self.set(i, val)

        return self

    def clear(self):
        """Clear all booleans to false."""
        for i in range(len(self._words)):
            self._words[i] = 0
        return self

    def each_true(self, func):
        """
        Iterate over all indices where the value is true.
        Calls func(index) for each true value.
        """
        for word_index in range(len(self._words)):
            if self._words[word_index] == 0:
                continue
            for bit_pos in range(32):
                index = (word_index << 5) + bit_pos
                if index >= self._size:
                    break
                if self.get(index):
                    func.call(index)

    def copy_from(self, that):
        """
        Copy the booleans from 'that' array into this array.
        """
        # Copy words directly for efficiency
        for i in range(len(that._words)):
            if i < len(self._words):
                self._words[i] = that._words[i]
        return self

    def typeof(self):
        return Type.find("util::BoolArray")
