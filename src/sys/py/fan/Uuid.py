#
# Uuid - UUID for Fantom
#
import uuid as py_uuid
from fan.sys.Obj import Obj

class Uuid(Obj):
    """
    Uuid represents a 128-bit universally unique identifier.
    """

    def __init__(self, uuid_obj):
        self._uuid = uuid_obj

    @staticmethod
    def make():
        """Generate a new random UUID (version 4)"""
        return Uuid(py_uuid.uuid4())

    @staticmethod
    def make_str(s):
        """Create UUID from string"""
        return Uuid.from_str(s)

    @staticmethod
    def from_str(s, checked=True):
        """Parse UUID from string"""
        try:
            return Uuid(py_uuid.UUID(s))
        except ValueError as e:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid UUID: {s}")
            return None

    @staticmethod
    def make_bits(hi, lo):
        """Create UUID from high/low 64-bit values (signed 64-bit ints from Fantom)"""
        # Convert signed 64-bit to unsigned 64-bit
        if hi < 0:
            hi = hi & 0xFFFFFFFFFFFFFFFF
        if lo < 0:
            lo = lo & 0xFFFFFFFFFFFFFFFF
        # Combine hi and lo into 128-bit unsigned integer
        val = (hi << 64) | lo
        return Uuid(py_uuid.UUID(int=val))

    def bits_hi(self):
        """Get upper 64 bits as signed 64-bit int (Fantom convention)"""
        val = self._uuid.int >> 64
        # Convert to signed if high bit is set
        if val >= 0x8000000000000000:
            val -= 0x10000000000000000
        return val

    def bits_lo(self):
        """Get lower 64 bits as signed 64-bit int (Fantom convention)"""
        val = self._uuid.int & 0xFFFFFFFFFFFFFFFF
        # Convert to signed if high bit is set
        if val >= 0x8000000000000000:
            val -= 0x10000000000000000
        return val

    def to_str(self):
        """String representation"""
        return str(self._uuid)

    def equals(self, other):
        """Test equality"""
        if not isinstance(other, Uuid):
            return False
        return self._uuid == other._uuid

    def hash_(self):
        """Hash code"""
        return hash(self._uuid)

    def compare(self, other):
        """Compare to another UUID"""
        if not isinstance(other, Uuid):
            return 1
        if self._uuid < other._uuid:
            return -1
        if self._uuid > other._uuid:
            return 1
        return 0

    def __lt__(self, other):
        return self.compare(other) < 0

    def __le__(self, other):
        return self.compare(other) <= 0

    def __gt__(self, other):
        return self.compare(other) > 0

    def __ge__(self, other):
        return self.compare(other) >= 0

    def typeof(self):
        """Return the Fantom type of this object."""
        from fan.sys.Type import Type
        return Type.find("sys::Uuid")

    def literal_encode(self, encoder):
        """Encode for serialization.

        Simple types serialize as: Type("toStr")
        Example: sys::Uuid("550e8400-e29b-41d4-a716-446655440000")
        """
        encoder.w_type(self.typeof())
        encoder.w('(')
        encoder.w_str_literal(self.to_str(), '"')
        encoder.w(')')
