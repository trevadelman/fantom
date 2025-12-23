#
# util::SeededRandom - Native Python implementation
# Hand-written runtime for Python transpilation
#

import random as py_random
from fan.sys.Obj import Obj
from fan.sys.Type import Type


class SeededRandom(Obj):
    """
    Random number generator that uses a seed for reproducible sequences.
    """

    def __init__(self, seed):
        super().__init__()
        self._seed = int(seed)
        self._rand = py_random.Random(self._seed)

    @staticmethod
    def make(seed):
        """Create a seeded random generator."""
        return SeededRandom(seed)

    def seed(self, val=None):
        """Get or set the seed."""
        if val is None:
            return self._seed
        else:
            self._seed = int(val)
            self._rand = py_random.Random(self._seed)

    def init(self):
        """Initialize the random generator (called after construction)."""
        # Already initialized in __init__
        pass

    def next(self, r=None):
        """
        Return the next random integer.
        If range is provided, return value within that range.
        """
        # Get a random 64-bit value
        val = self._rand.getrandbits(64)
        # Convert to signed
        if val >= (1 << 63):
            val = val - (1 << 64)

        if r is None:
            return val

        # Apply range
        if val < 0:
            val = -val

        start = r._start
        end = r._end

        # Handle inclusive/exclusive
        if r._exclusive:
            end_val = end
        else:
            end_val = end + 1

        if end_val <= start:
            from fan.sys.Err import ArgErr
            raise ArgErr.make(f"Range end < start: {r}")

        return start + (val % (end_val - start))

    def nextBool(self):
        """Return the next random boolean."""
        return self._rand.random() < 0.5

    def nextFloat(self):
        """Return the next random float between 0.0 and 1.0."""
        return self._rand.random()

    def nextBuf(self, size):
        """Return a buffer filled with random bytes."""
        from fan.sys.Buf import Buf
        size = int(size)
        data = bytes(self._rand.getrandbits(8) for _ in range(size))
        buf = Buf.make(size)
        for b in data:
            buf.write(b)
        buf.flip()
        return buf

    def typeof(self):
        return Type.find("util::SeededRandom")
