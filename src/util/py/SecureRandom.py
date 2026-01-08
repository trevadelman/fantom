#
# util::SecureRandom - Native Python implementation
# Hand-written runtime for Python transpilation
#

import secrets
import os
from fan.sys.Obj import Obj
from fan.sys.Type import Type


class SecureRandom(Obj):
    """
    Cryptographically secure random number generator.
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def make():
        """Create a secure random generator."""
        return SecureRandom()

    def init(self):
        """Initialize the random generator."""
        pass

    def next(self, r=None):
        """
        Return the next random integer.
        If range is provided, return value within that range.
        """
        # Get a random 64-bit value
        val = secrets.randbits(64)
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

    def next_bool(self):
        """Return the next random boolean."""
        return secrets.randbits(1) == 1

    def next_float(self):
        """Return the next random float between 0.0 and 1.0."""
        # Generate 53 bits of randomness for a float in [0, 1)
        return secrets.randbits(53) / (1 << 53)

    def next_buf(self, size):
        """Return a buffer filled with random bytes."""
        from fan.sys.Buf import Buf
        size = int(size)
        data = os.urandom(size)
        buf = Buf.make(size)
        for b in data:
            buf.write(b)
        buf.flip()
        return buf

    def typeof(self):
        return Type.find("util::SecureRandom")
