#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Int(Obj):
    """Integer type - uses static methods on native int"""

    @staticmethod
    def defVal():
        return 0

    @staticmethod
    def isImmutable(self):
        return True

    @staticmethod
    def typeof(self):
        return "sys::Int"

    @staticmethod
    def hash(self):
        return self

    @staticmethod
    def hash_(self):
        """Alias for hash - transpiler may generate hash_"""
        return Int.hash(self)

    @staticmethod
    def equals(self, other):
        """Equality comparison"""
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
        return self // b

    @staticmethod
    def mod(self, b):
        return self % b

    @staticmethod
    def negate(self):
        return -self

    # Bitwise operations
    @staticmethod
    def and_(self, b):
        return self & b

    @staticmethod
    def or_(self, b):
        return self | b

    @staticmethod
    def xor(self, b):
        return self ^ b

    @staticmethod
    def not_(self):
        return ~self

    @staticmethod
    def shiftl(self, b):
        return self << b

    @staticmethod
    def shiftr(self, b):
        """Logical right shift (fills with zeros)"""
        # For negative numbers, treat as unsigned 64-bit then shift
        if self < 0:
            # Convert to unsigned 64-bit representation
            unsigned = self & 0xFFFFFFFFFFFFFFFF
            return unsigned >> b
        return self >> b

    @staticmethod
    def shifta(self, b):
        """Arithmetic right shift (fills with sign bit)"""
        # Python's >> is arithmetic for signed integers
        # But Python integers are arbitrary precision, so we need to preserve 64-bit semantics
        # For positive numbers, same as logical shift
        if self >= 0:
            return self >> b
        # For negative numbers, arithmetic shift preserves sign
        # We need to work in 64-bit signed space
        # Convert to signed 64-bit, shift, keep signed
        return self >> b  # Python's >> already does arithmetic shift for negative numbers

    # Comparison
    @staticmethod
    def compare(self, that):
        if that is None:
            return 1
        if self < that:
            return -1
        if self > that:
            return 1
        return 0

    # Conversions
    @staticmethod
    def toStr(self):
        if self is None:
            return None
        return str(self)

    @staticmethod
    def toCode(self, base=10):
        if base == 16:
            return "0x" + hex(self)[2:]
        return str(self)

    @staticmethod
    def toHex(self, width=None):
        if self < 0:
            # Handle negative numbers as unsigned 64-bit
            val = self & 0xFFFFFFFFFFFFFFFF
        else:
            val = self
        h = format(val, 'x')
        if width is not None:
            h = h.zfill(width)
        return h

    @staticmethod
    def toRadix(self, radix, width=None):
        if radix == 16:
            s = Int.toHex(self)
        elif radix == 2:
            s = bin(self)[2:]
        elif radix == 8:
            s = oct(self)[2:]
        else:
            s = str(self)
        if width is not None:
            s = s.zfill(width)
        return s

    @staticmethod
    def toChar(self):
        return chr(self)

    @staticmethod
    def toFloat(self):
        return float(self)

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

    # Ranges
    @staticmethod
    def times(self, f):
        """Iterate f(i) from 0 to self-1
        If closure accepts arg, pass i. If not, call without args.
        """
        # Check if f is a Func instance - use its params() method
        from .Func import Func
        if isinstance(f, Func):
            accepts_arg = len(f.params()) > 0
        else:
            import inspect
            try:
                # Check how many positional parameters the function accepts
                sig = inspect.signature(f)
                # Count positional params (exclude keyword-only params with defaults like _self=self)
                pos_params = [p for p in sig.parameters.values()
                              if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                           inspect.Parameter.POSITIONAL_OR_KEYWORD)
                              and p.default is inspect.Parameter.empty]
                accepts_arg = len(pos_params) > 0
            except (ValueError, TypeError):
                accepts_arg = True  # Default to passing arg

        for i in range(self):
            if accepts_arg:
                f(i)
            else:
                f()

    # Parsing
    @staticmethod
    def fromStr(s, radix=10, checked=True):
        try:
            val = int(s, radix)
            # Convert to signed 64-bit if high bit is set
            if val >= 0x8000000000000000:
                val -= 0x10000000000000000
            return val
        except ValueError:
            if not checked:
                return None
            from .Err import ParseErr
            raise ParseErr.makeStr("Int", s)

    @staticmethod
    def clamp(self, min_val, max_val):
        if self < min_val:
            return min_val
        if self > max_val:
            return max_val
        return self

    @staticmethod
    def isEven(self):
        return self % 2 == 0

    @staticmethod
    def isOdd(self):
        return self % 2 != 0

    # Character tests (for Unicode codepoints)
    # Fantom uses ASCII-only definitions for these methods
    @staticmethod
    def isSpace(ch):
        # ASCII whitespace: space, tab, newline, carriage return, etc.
        return ch == 32 or ch == 9 or ch == 10 or ch == 13 or ch == 12

    @staticmethod
    def isAlpha(ch):
        # ASCII letters only: A-Z (65-90), a-z (97-122)
        return (65 <= ch <= 90) or (97 <= ch <= 122)

    @staticmethod
    def isAlphaNum(ch):
        # ASCII alphanumeric: 0-9, A-Z, a-z
        return (48 <= ch <= 57) or (65 <= ch <= 90) or (97 <= ch <= 122)

    @staticmethod
    def isDigit(ch, radix=10):
        """Check if ch is a digit in the given radix"""
        if 48 <= ch <= 57:  # '0'-'9'
            digit_val = ch - 48
        elif 65 <= ch <= 90:  # 'A'-'Z'
            digit_val = ch - 65 + 10
        elif 97 <= ch <= 122:  # 'a'-'z'
            digit_val = ch - 97 + 10
        else:
            return False
        return digit_val < radix

    @staticmethod
    def isUpper(ch):
        # ASCII uppercase only: A-Z (65-90)
        return 65 <= ch <= 90

    @staticmethod
    def isLower(ch):
        # ASCII lowercase only: a-z (97-122)
        return 97 <= ch <= 122

    @staticmethod
    def upper(ch):
        # Only convert ASCII lowercase to uppercase
        if 97 <= ch <= 122:  # a-z
            return ch - 32
        return ch

    @staticmethod
    def lower(ch):
        # Only convert ASCII uppercase to lowercase
        if 65 <= ch <= 90:  # A-Z
            return ch + 32
        return ch

    @staticmethod
    def equalsIgnoreCase(a, b):
        return chr(a).lower() == chr(b).lower()

    @staticmethod
    def localeIsLower(ch, locale=None):
        """Check if character is lowercase per locale.
        Uses Python's Unicode-aware islower() which handles locale-specific cases.
        """
        return chr(ch).islower()

    @staticmethod
    def localeIsUpper(ch, locale=None):
        """Check if character is uppercase per locale.
        Uses Python's Unicode-aware isupper() which handles locale-specific cases.
        """
        return chr(ch).isupper()

    @staticmethod
    def localeUpper(ch, locale=None):
        """Convert character to uppercase per locale.
        Uses Python's Unicode-aware upper() which handles locale-specific cases.
        """
        return ord(chr(ch).upper())

    @staticmethod
    def localeLower(ch, locale=None):
        """Convert character to lowercase per locale.
        Uses Python's Unicode-aware lower() which handles locale-specific cases.
        """
        return ord(chr(ch).lower())

    @staticmethod
    def toDigit(i, radix=10):
        """Convert int 0-35 to digit char ('0'-'9', 'a'-'z')"""
        if i < 0 or i >= radix:
            return None
        if i < 10:
            return 48 + i  # '0' + i
        return 97 + (i - 10)  # 'a' + (i - 10)

    @staticmethod
    def fromDigit(ch, radix=10):
        """Convert digit char to int value, or None if invalid"""
        if 48 <= ch <= 57:  # '0'-'9'
            val = ch - 48
        elif 65 <= ch <= 90:  # 'A'-'Z'
            val = ch - 65 + 10
        elif 97 <= ch <= 122:  # 'a'-'z'
            val = ch - 97 + 10
        else:
            return None
        if val >= radix:
            return None
        return val

    # Duration conversion (nanoseconds)
    @staticmethod
    def toDuration(self):
        from .Duration import Duration
        return Duration.make(self)

    # Random
    @staticmethod
    def random(r=None):
        import random
        if r is None:
            return random.randint(Int.minVal(), Int.maxVal())
        # r should be a Range object
        from .Range import Range as RangeClass
        start = r._start if hasattr(r, '_start') else 0
        end = r._end if hasattr(r, '_end') else 100
        exclusive = r._exclusive if hasattr(r, '_exclusive') else False
        if exclusive:
            # Exclusive range: [start, end)
            return random.randint(start, end - 1)
        else:
            # Inclusive range: [start, end]
            return random.randint(start, end)

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

    # Unit constants for byte formatting
    _KB = 1024
    _MB = 1024 * 1024
    _GB = 1024 * 1024 * 1024

    @staticmethod
    def toLocale(self, pattern=None, locale=None):
        """Format int according to locale pattern"""
        # Get locale-specific thousands separator
        thousands_sep, decimal_sep = Int._getLocaleSeparators(locale)

        # Special case: "B" pattern formats as bytes with KB/MB/GB suffix
        if pattern == "B":
            return Int._toLocaleBytes(self, locale)

        if pattern is None:
            # Default: add thousands separators (3-digit groups)
            return Int._formatWithGrouping(self, 3, thousands_sep)

        # Handle patterns like "#,###" or "#,####" or "0000"
        # Check for suffix patterns (alpha characters at end)
        suffix = ""
        if pattern and pattern[-1].isalpha():
            suffix = pattern[-1]
            pattern = pattern[:-1]
            if not pattern:
                return str(self) + suffix

        # Parse grouping from pattern like "#,###" -> group size 3
        if ',' in pattern:
            parts = pattern.split(',')
            # Group size is the length of the last segment
            group_size = len(parts[-1])
            return Int._formatWithGrouping(self, group_size, thousands_sep) + suffix

        # Fixed width with leading zeros (pattern like "000")
        if pattern.startswith('0'):
            width = len(pattern)
            s = str(abs(self)).zfill(width)
            return ('-' + s) if self < 0 else s

        # Pattern "#" - no grouping
        if pattern == '#':
            return str(self) + suffix

        return str(self) + suffix

    @staticmethod
    def _formatWithGrouping(val, group_size, sep):
        """Format integer with specified group size and separator"""
        neg = val < 0
        s = str(abs(val))

        # Apply grouping from right to left
        result = []
        for i, char in enumerate(reversed(s)):
            if i > 0 and i % group_size == 0:
                result.append(sep)
            result.append(char)

        formatted = ''.join(reversed(result))
        return ('-' + formatted) if neg else formatted

    @staticmethod
    def _toLocaleBytes(b, locale=None):
        """Format bytes with KB/MB/GB suffix based on magnitude.

        Following the same algorithm as the JavaScript runtime:
        - < 1KB: show as bytes (e.g., "123B")
        - < 10KB: show with one decimal (e.g., "1.2KB")
        - < 1MB: show as rounded KB (e.g., "98KB")
        - < 10MB: show with one decimal MB
        - < 1GB: show as rounded MB
        - < 10GB: show with one decimal GB
        - >= 10GB: show as rounded GB
        """
        from .Float import Float

        KB = Int._KB
        MB = Int._MB
        GB = Int._GB

        if b < KB:
            return str(b) + "B"
        if b < 10 * KB:
            return Float.toLocale(b / KB, "#.#", locale) + "KB"
        if b < MB:
            return str(round(b / KB)) + "KB"
        if b < 10 * MB:
            return Float.toLocale(b / MB, "#.#", locale) + "MB"
        if b < GB:
            return str(round(b / MB)) + "MB"
        if b < 10 * GB:
            return Float.toLocale(b / GB, "#.#", locale) + "GB"
        return str(round(b / GB)) + "GB"

    @staticmethod
    def trap(self, name, args=None):
        """Dynamic method invocation"""
        if args is None:
            args = []
        # Map method names to static methods
        method_map = {
            'and': Int.and_,
            'or': Int.or_,
            'xor': Int.xor,
            'not': Int.not_,
            'plus': Int.plus,
            'minus': Int.minus,
            'mult': Int.mult,
            'div': Int.div,
            'mod': Int.mod,
            'shiftl': Int.shiftl,
            'shiftr': Int.shiftr,
            'shifta': Int.shifta,
            'abs': Int.abs,
            'min': Int.min,
            'max': Int.max,
            'pow': Int.pow,
            'toStr': Int.toStr,
            'toHex': Int.toHex,
            'toChar': Int.toChar,
            'toFloat': Int.toFloat,
        }
        method = method_map.get(name)
        if method:
            return method(self, *args)
        raise AttributeError(f"Int.{name}")

    # Constants
    @staticmethod
    def maxVal():
        return 9223372036854775807  # 2^63 - 1

    @staticmethod
    def minVal():
        return -9223372036854775808  # -2^63

    @staticmethod
    def toDateTime(ticks, tz=None):
        """Convert ticks to DateTime"""
        from .DateTime import DateTime
        return DateTime.makeTicks(ticks, tz)
