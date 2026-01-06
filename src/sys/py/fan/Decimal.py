#
# Decimal - Decimal number for Fantom
#
from decimal import Decimal as PyDecimal, ROUND_HALF_UP, ROUND_FLOOR, ROUND_CEILING
from fan.sys.Obj import Obj

class Decimal(Obj):
    """
    Decimal represents an immutable arbitrary-precision decimal number.
    """

    # Default value cache
    _defVal = None

    def __init__(self, val):
        if isinstance(val, PyDecimal):
            self._val = val
        else:
            self._val = PyDecimal(str(val))

    @staticmethod
    def fromStr(s, checked=True):
        """Parse a Decimal from string"""
        try:
            return Decimal(PyDecimal(s))
        except Exception as e:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid decimal: {s}")
            return None

    @staticmethod
    def make(val):
        """Create Decimal from numeric value"""
        return Decimal(val)

    @staticmethod
    def defVal():
        """Default value (0)"""
        if Decimal._defVal is None:
            Decimal._defVal = Decimal(PyDecimal("0"))
        return Decimal._defVal

    def negate(self):
        """Return negated value"""
        return Decimal(-self._val)

    def increment(self):
        """Return this + 1"""
        return Decimal(self._val + 1)

    def decrement(self):
        """Return this - 1"""
        return Decimal(self._val - 1)

    def plus(self, other):
        """Add two decimals"""
        if isinstance(other, Decimal):
            return Decimal(self._val + other._val)
        return Decimal(self._val + PyDecimal(str(other)))

    def minus(self, other):
        """Subtract two decimals"""
        if isinstance(other, Decimal):
            return Decimal(self._val - other._val)
        return Decimal(self._val - PyDecimal(str(other)))

    def mult(self, other):
        """Multiply two decimals"""
        if isinstance(other, Decimal):
            return Decimal(self._val * other._val)
        return Decimal(self._val * PyDecimal(str(other)))

    def div(self, other):
        """Divide two decimals"""
        if isinstance(other, Decimal):
            return Decimal(self._val / other._val)
        return Decimal(self._val / PyDecimal(str(other)))

    def mod(self, other):
        """Modulo"""
        if isinstance(other, Decimal):
            return Decimal(self._val % other._val)
        return Decimal(self._val % PyDecimal(str(other)))

    def abs(self):
        """Absolute value"""
        return Decimal(abs(self._val))

    def min(self, other):
        """Return minimum"""
        if isinstance(other, Decimal):
            return Decimal(min(self._val, other._val))
        return Decimal(min(self._val, PyDecimal(str(other))))

    def max(self, other):
        """Return maximum"""
        if isinstance(other, Decimal):
            return Decimal(max(self._val, other._val))
        return Decimal(max(self._val, PyDecimal(str(other))))

    def floor(self):
        """Round toward negative infinity"""
        return Decimal(self._val.to_integral_value(rounding=ROUND_FLOOR))

    def ceil(self):
        """Round toward positive infinity"""
        return Decimal(self._val.to_integral_value(rounding=ROUND_CEILING))

    def round(self):
        """Round to nearest integer"""
        return Decimal(self._val.to_integral_value(rounding=ROUND_HALF_UP))

    def toInt(self):
        """Convert to Int"""
        return int(self._val)

    def toFloat(self):
        """Convert to Float"""
        return float(self._val)

    def toStr(self):
        """String representation"""
        return str(self._val)

    def toCode(self):
        """Code representation"""
        return str(self._val) + "d"

    def toLocale(self, pattern=None):
        """Format with locale"""
        # Simple implementation - format with commas
        s = str(self._val)
        if "." in s:
            whole, frac = s.split(".")
        else:
            whole, frac = s, ""

        # Add thousands separators
        if whole.startswith("-"):
            sign = "-"
            whole = whole[1:]
        else:
            sign = ""

        result = ""
        for i, c in enumerate(reversed(whole)):
            if i > 0 and i % 3 == 0:
                result = "," + result
            result = c + result

        if frac:
            return sign + result + "." + frac
        return sign + result

    def equals(self, other):
        """Test equality"""
        if isinstance(other, Decimal):
            return self._val == other._val
        if isinstance(other, (int, float)):
            return self._val == PyDecimal(str(other))
        return False

    def hash_(self):
        """Hash code"""
        return hash(self._val)

    def compare(self, other):
        """Compare to another decimal"""
        if isinstance(other, Decimal):
            other_val = other._val
        else:
            other_val = PyDecimal(str(other))

        if self._val < other_val:
            return -1
        if self._val > other_val:
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

    def __float__(self):
        return float(self._val)

    def __int__(self):
        return int(self._val)

    def literalEncode(self, out):
        """Encode for serialization.

        Decimal literals are written with 'd' suffix: 123.456d
        """
        out.w(str(self._val))
        out.w("d")

    @staticmethod
    def encode(self, out):
        """Static method to encode decimal for serialization.

        Args:
            self: The Decimal value to encode
            out: ObjEncoder to write to

        Decimals are written with a 'd' suffix.
        """
        if isinstance(self, Decimal):
            out.w(str(self._val))
        else:
            out.w(str(self))
        out.w("d")
