#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

import math
from .Obj import Obj


class Float(Obj):
    """Float type - uses static methods on native float"""

    @staticmethod
    def defVal():
        return 0.0

    @staticmethod
    def isImmutable(self):
        return True

    @staticmethod
    def typeof(self):
        return "sys::Float"

    @staticmethod
    def hash(self):
        return hash(self)

    @staticmethod
    def hash_(self):
        return Float.hash(self)

    @staticmethod
    def equals(self, other):
        if other is None:
            return False
        return self == other

    # Arithmetic operations
    @staticmethod
    def plus(self, b):
        return self + b

    @staticmethod
    def minus(self, b):
        return self - b

    @staticmethod
    def mult(self, b):
        return self * b

    @staticmethod
    def div(self, b):
        return self / b

    @staticmethod
    def mod(self, b):
        return self % b

    @staticmethod
    def negate(self):
        return -self

    # Comparison
    @staticmethod
    def compare(self, that):
        if that is None:
            return 1
        # NaN sorts before everything (Fantom semantics)
        if math.isnan(self):
            if math.isnan(that):
                return 0  # NaN == NaN for comparison
            return -1  # NaN < any number
        if math.isnan(that):
            return 1  # any number > NaN
        if self < that:
            return -1
        if self > that:
            return 1
        return 0

    # Conversions
    @staticmethod
    def toStr(self):
        if math.isnan(self):
            return "NaN"
        if math.isinf(self):
            return "INF" if self > 0 else "-INF"
        s = str(self)
        # Fantom style: always show decimal point
        if "." not in s and "e" not in s and "E" not in s:
            s += ".0"
        # Fantom uses uppercase E in scientific notation without + sign
        s = s.replace('e+', 'E').replace('e-', 'E-').replace('e', 'E')
        return s

    @staticmethod
    def toCode(self):
        import math
        if math.isnan(self):
            return "Float.nan"
        if math.isinf(self):
            return "Float.posInf" if self > 0 else "Float.negInf"
        return Float.toStr(self) + "f"

    @staticmethod
    def toInt(self):
        # Handle special values - Fantom returns maxVal/minVal for infinity
        if math.isnan(self):
            return 0
        if math.isinf(self):
            if self > 0:
                return 9223372036854775807  # Int.maxVal
            else:
                return -9223372036854775808  # Int.minVal
        return int(self)

    @staticmethod
    def toFloat(self):
        return float(self)

    @staticmethod
    def toDecimal(self):
        """Convert to Decimal - returns the float value as-is for now"""
        return self

    # Math operations
    @staticmethod
    def abs(self):
        return abs(self)

    @staticmethod
    def min(self, that):
        return min(self, that)

    @staticmethod
    def max(self, that):
        return max(self, that)

    @staticmethod
    def pow(self, exp):
        return self ** exp

    @staticmethod
    def floor(self):
        # Handle special values - infinity and NaN floor to themselves
        if math.isnan(self) or math.isinf(self):
            return self
        return math.floor(self)

    @staticmethod
    def ceil(self):
        # Handle special values - infinity and NaN ceil to themselves
        if math.isnan(self) or math.isinf(self):
            return self
        return math.ceil(self)

    @staticmethod
    def round(self):
        # Handle special values - infinity and NaN round to themselves
        if math.isnan(self) or math.isinf(self):
            return self
        return round(self)

    @staticmethod
    def sqrt(self):
        return math.sqrt(self)

    @staticmethod
    def exp(self):
        return math.exp(self)

    @staticmethod
    def log(self):
        return math.log(self)

    @staticmethod
    def log10(self):
        return math.log10(self)

    # Trig
    @staticmethod
    def sin(self):
        return math.sin(self)

    @staticmethod
    def cos(self):
        return math.cos(self)

    @staticmethod
    def tan(self):
        return math.tan(self)

    @staticmethod
    def asin(self):
        return math.asin(self)

    @staticmethod
    def acos(self):
        return math.acos(self)

    @staticmethod
    def atan(self):
        return math.atan(self)

    @staticmethod
    def atan2(y, x):
        return math.atan2(y, x)

    # Hyperbolic
    @staticmethod
    def sinh(self):
        return math.sinh(self)

    @staticmethod
    def cosh(self):
        return math.cosh(self)

    @staticmethod
    def tanh(self):
        return math.tanh(self)

    # Degree conversion
    @staticmethod
    def toDegrees(self):
        return math.degrees(self)

    @staticmethod
    def toRadians(self):
        return math.radians(self)

    # Checks
    @staticmethod
    def isNaN(self):
        return math.isnan(self)

    @staticmethod
    def isNegZero(self):
        return self == 0.0 and math.copysign(1, self) < 0

    @staticmethod
    def normNegZero(self):
        """Normalize negative zero to positive zero"""
        if Float.isNegZero(self):
            return 0.0
        return self

    @staticmethod
    def approx(self, that, tolerance=None):
        """Check if two floats are approximately equal"""
        # NaN is approximately equal to NaN
        if math.isnan(self) and math.isnan(that):
            return True
        if math.isnan(self) or math.isnan(that):
            return False
        # Infinity handling
        if math.isinf(self) or math.isinf(that):
            return self == that
        # Normal case - default tolerance is relative to magnitude
        if tolerance is None:
            # Use larger of the two magnitudes for relative comparison
            mag = max(abs(self), abs(that))
            if mag < 1e-10:
                tolerance = 1e-10  # Absolute tolerance for very small numbers
            else:
                tolerance = mag * 1e-6  # Relative tolerance
        return abs(self - that) <= tolerance

    @staticmethod
    def clamp(self, min_val, max_val):
        if self < min_val:
            return min_val
        if self > max_val:
            return max_val
        return self

    @staticmethod
    def bits(self):
        """Get IEEE 754 64-bit bits as Int"""
        import struct
        return struct.unpack('>q', struct.pack('>d', self))[0]

    @staticmethod
    def bits32(self):
        """Get IEEE 754 32-bit bits as unsigned Int"""
        import struct
        return struct.unpack('>I', struct.pack('>f', self))[0]

    @staticmethod
    def makeBits(bits):
        """Convert IEEE 754 64-bit bits to Float"""
        import struct
        return struct.unpack('>d', struct.pack('>q', bits))[0]

    # Alias for compatibility
    bitsToFloat = makeBits

    @staticmethod
    def makeBits32(bits):
        """Convert IEEE 754 32-bit bits to Float"""
        import struct
        # Use unsigned int format for 32-bit
        return struct.unpack('>f', struct.pack('>I', bits))[0]

    # Parsing
    @staticmethod
    def fromStr(s, checked=True):
        try:
            s = s.strip()
            if s == "NaN":
                return float("nan")
            if s == "INF":
                return float("inf")
            if s == "-INF":
                return float("-inf")
            return float(s)
        except ValueError:
            if not checked:
                return None
            from .Err import ParseErr
            raise ParseErr.makeStr("Float", s)

    # Constants
    @staticmethod
    def posInf():
        return float("inf")

    @staticmethod
    def negInf():
        return float("-inf")

    @staticmethod
    def nan():
        return float("nan")

    @staticmethod
    def e():
        return math.e

    @staticmethod
    def pi():
        return math.pi

    @staticmethod
    def random():
        """Return random float between 0.0 (inclusive) and 1.0 (exclusive)"""
        import random
        return random.random()

    @staticmethod
    def _getLocaleSeparators(locale=None):
        """Get thousands and decimal separators for the given locale.

        Returns (thousands_sep, decimal_sep) tuple.

        Fantom uses CLDR-based locale formatting:
        - French/European style: non-breaking space for thousands, comma for decimal
        - English style: comma for thousands, period for decimal
        """
        from .Locale import Locale

        if locale is None:
            locale = Locale.cur()

        # Get language code
        lang = locale.lang() if hasattr(locale, 'lang') else 'en'

        # English locales use comma/period
        if lang == 'en':
            return (',', '.')

        # Most European locales use non-breaking space/comma
        # This includes French (fr), German (de), Italian (it), Spanish (es), etc.
        # Non-breaking space is \u00a0
        return ('\u00a0', ',')

    @staticmethod
    def toLocale(self, pattern=None, locale=None):
        """Format float according to locale pattern"""
        if math.isnan(self):
            return "NaN"
        if math.isinf(self):
            return "INF" if self > 0 else "-INF"

        # Get locale-specific separators
        thousands_sep, decimal_sep = Float._getLocaleSeparators(locale)

        # Handle negative zero - treat as positive zero
        # math.copysign(1, -0.0) returns -1.0, so check both value and sign
        is_negative = self < 0.0
        self = abs(self)

        # Default - use magnitude-based pattern like JavaScript implementation
        if pattern is None:
            # Zero special case
            if self == 0.0:
                return "0" + decimal_sep + "0"
            # Large numbers (>= 100) - round to integer with Int.toLocale
            if self >= 100.0:
                from .Int import Int
                rounded = round(self)
                if is_negative:
                    rounded = -rounded
                return Int.toLocale(rounded, None, locale)
            # Determine default pattern based on magnitude
            pattern = Float._getDefaultLocalePattern(self)

        # Pattern parsing for "#", "#.###", "#,###.00", "#.00##", "00.0" etc.
        use_grouping = ',' in pattern

        # Parse integer part of pattern
        int_pattern = pattern.split('.')[0] if '.' in pattern else pattern
        int_pattern_clean = int_pattern.replace(',', '').replace('#', '')
        min_int_digits = int_pattern_clean.count('0')  # Required integer digits

        # Determine decimal places
        if '.' in pattern:
            decimal_part = pattern.split('.')[1].replace(',', '')
            max_decimals = len(decimal_part)
            # Count minimum decimals (0 characters = required)
            min_decimals = decimal_part.count('0')

            # Format with max decimals
            formatted = f"{abs(self):.{max_decimals}f}"

            # Strip trailing zeros, but keep minimum decimals
            if min_decimals < max_decimals:
                if '.' in formatted:
                    parts = formatted.split('.')
                    int_part = parts[0]
                    dec_part = parts[1]
                    # Strip trailing zeros from decimal part
                    while len(dec_part) > min_decimals and dec_part.endswith('0'):
                        dec_part = dec_part[:-1]
                    formatted = int_part + '.' + dec_part if dec_part else int_part
        else:
            # No decimal part - truncate to integer
            formatted = str(abs(int(self)))

        # Handle minimum integer digits (leading zeros)
        if min_int_digits > 0:
            if '.' in formatted:
                parts = formatted.split('.')
                int_part = parts[0]
                dec_part = parts[1]
                while len(int_part) < min_int_digits:
                    int_part = '0' + int_part
                formatted = int_part + '.' + dec_part
            else:
                while len(formatted) < min_int_digits:
                    formatted = '0' + formatted

        # Handle grouping with locale-specific separator
        if use_grouping:
            # Determine group size from pattern
            # For "#,###" = 3, "#,####" = 4, "#,##,##" = 2 (repeating)
            # Use the size of the last group in the pattern
            int_pattern_parts = int_pattern.split(',')
            if len(int_pattern_parts) > 1:
                group_size = len(int_pattern_parts[-1])  # Last group size
            else:
                group_size = 3  # Default

            if '.' in formatted:
                parts = formatted.split('.')
                int_part = parts[0]
                dec_part = parts[1]
                int_part = Float._formatIntWithGrouping(int(int_part) if int_part else 0, group_size, thousands_sep)
                formatted = int_part + decimal_sep + dec_part
            else:
                formatted = Float._formatIntWithGrouping(int(formatted) if formatted else 0, group_size, thousands_sep)
        else:
            # No grouping - just replace decimal separator
            formatted = formatted.replace('.', decimal_sep)

        # Add sign back if negative
        if is_negative:
            formatted = '-' + formatted

        # Handle leading "." for values < 1 (pattern like ".123" instead of "0.123")
        if '#.' in pattern and int_pattern == '#':
            if formatted.startswith('0' + decimal_sep):
                formatted = formatted[1:]  # Remove leading "0"
            elif formatted.startswith('-0' + decimal_sep):
                formatted = '-' + formatted[2:]  # Keep sign, remove "0"

        return formatted

    @staticmethod
    def _getDefaultLocalePattern(val):
        """Determine default locale pattern based on magnitude.

        Following the JavaScript implementation:
        - >= 10.0: "#0.0#"  (1-2 decimal places)
        - >= 1.0:  "#0.0##" (1-3 decimal places)
        - Fractions are based on leading zeros
        """
        abs_val = abs(val)
        fabs = math.floor(abs_val)

        if fabs >= 10.0:
            return "#0.0#"
        if fabs >= 1.0:
            return "#0.0##"

        # Format a fractional number (no integer part)
        frac = abs_val - fabs
        if frac < 0.00000001:
            return "0.0"
        if frac < 0.0000001:
            return "0.0000000##"
        if frac < 0.000001:
            return "0.000000##"
        if frac < 0.00001:
            return "0.00000##"
        if frac < 0.0001:
            return "0.0000##"
        if frac < 0.001:
            return "0.000##"
        return "0.0##"

    @staticmethod
    def _formatIntWithGrouping(val, group_size, sep):
        """Format integer part with specified group size and separator"""
        s = str(abs(int(val)))

        if len(s) <= group_size:
            return s

        # Apply grouping from right to left
        result = []
        for i, char in enumerate(reversed(s)):
            if i > 0 and i % group_size == 0:
                result.append(sep)
            result.append(char)

        return ''.join(reversed(result))

    @staticmethod
    def encode(self, out):
        """Encode float for serialization.

        Args:
            self: The float value to encode
            out: ObjEncoder to write to

        Special values (NaN, INF, -INF) are written as sys::Float("NaN") etc.
        Normal values are written with an 'f' suffix.
        """
        if math.isnan(self):
            out.w('sys::Float("NaN")')
        elif math.isinf(self):
            if self > 0:
                out.w('sys::Float("INF")')
            else:
                out.w('sys::Float("-INF")')
        else:
            s = str(self)
            # Ensure there's a decimal point
            if '.' not in s and 'e' not in s and 'E' not in s:
                s += '.0'
            out.w(s)
            out.w("f")
