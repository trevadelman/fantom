#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Num import Num
from .Type import _camel_to_snake


class Int(Num):
    """Integer type - uses static methods on native int"""

    @staticmethod
    def def_val():
        return 0

    @staticmethod
    def is_immutable(self):
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
    def to_str(self):
        if self is None:
            return None
        return str(self)

    @staticmethod
    def to_code(self, base=10):
        if base == 10:
            return str(self)
        if base == 16:
            return "0x" + hex(self)[2:]
        from .Err import ArgErr
        raise ArgErr(f"Invalid base {base}")

    @staticmethod
    def to_hex(self, width=None):
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
    def to_radix(self, radix, width=None):
        if radix == 16:
            s = Int.to_hex(self)
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
    def to_char(self):
        # Valid Unicode range: 0 to 0x10FFFF (1,114,111)
        if self < 0 or self > 0x10FFFF:
            from .Err import Err
            raise Err(f"Invalid unicode char: {self}")
        return chr(self)

    @staticmethod
    def to_float(self):
        return float(self)

    # Math operations
    @staticmethod
    def abs_(self):
        return abs(self)

    @staticmethod
    def min_(self, that):
        return min(self, that)

    @staticmethod
    def max_(self, that):
        return max(self, that)

    @staticmethod
    def pow_(self, exp):
        if exp < 0:
            from .Err import ArgErr
            raise ArgErr("pow < 0")
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
    def from_str(s, radix=10, checked=True):
        try:
            # For non-decimal radixes, negative numbers are not supported
            if radix != 10 and s.startswith('-'):
                raise ValueError(f"Negative not allowed for radix {radix}")
            val = int(s, radix)
            # Convert to signed 64-bit if high bit is set
            if val >= 0x8000000000000000:
                val -= 0x10000000000000000
            return val
        except ValueError:
            if not checked:
                return None
            from .Err import ParseErr
            raise ParseErr.make_str("Int", s)

    @staticmethod
    def clamp(self, min_val, max_val):
        if self < min_val:
            return min_val
        if self > max_val:
            return max_val
        return self

    @staticmethod
    def is_even(self):
        return self % 2 == 0

    @staticmethod
    def is_odd(self):
        return self % 2 != 0

    # Character tests (for Unicode codepoints)
    # Fantom uses ASCII-only definitions for these methods
    @staticmethod
    def is_space(ch):
        # ASCII whitespace: space, tab, newline, carriage return, etc.
        return ch == 32 or ch == 9 or ch == 10 or ch == 13 or ch == 12

    @staticmethod
    def is_alpha(ch):
        # ASCII letters only: A-Z (65-90), a-z (97-122)
        return (65 <= ch <= 90) or (97 <= ch <= 122)

    @staticmethod
    def is_alpha_num(ch):
        # ASCII alphanumeric: 0-9, A-Z, a-z
        return (48 <= ch <= 57) or (65 <= ch <= 90) or (97 <= ch <= 122)

    @staticmethod
    def is_digit(ch, radix=10):
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
    def is_upper(ch):
        # ASCII uppercase only: A-Z (65-90)
        return 65 <= ch <= 90

    @staticmethod
    def is_lower(ch):
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
    def equals_ignore_case(a, b):
        return chr(a).lower() == chr(b).lower()

    @staticmethod
    def locale_is_lower(ch, locale=None):
        """Check if character is lowercase per locale.
        Uses Python's Unicode-aware islower() which handles locale-specific cases.
        """
        return chr(ch).islower()

    @staticmethod
    def locale_is_upper(ch, locale=None):
        """Check if character is uppercase per locale.
        Uses Python's Unicode-aware isupper() which handles locale-specific cases.
        """
        return chr(ch).isupper()

    @staticmethod
    def locale_upper(ch, locale=None):
        """Convert character to uppercase per locale.
        Uses Python's Unicode-aware upper() which handles locale-specific cases.
        """
        return ord(chr(ch).upper())

    @staticmethod
    def locale_lower(ch, locale=None):
        """Convert character to lowercase per locale.
        Uses Python's Unicode-aware lower() which handles locale-specific cases.
        """
        return ord(chr(ch).lower())

    @staticmethod
    def to_digit(i, radix=10):
        """Convert int 0-35 to digit char ('0'-'9', 'a'-'z')"""
        if i < 0 or i >= radix:
            return None
        if i < 10:
            return 48 + i  # '0' + i
        return 97 + (i - 10)  # 'a' + (i - 10)

    @staticmethod
    def from_digit(ch, radix=10):
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
    def to_duration(self):
        from .Duration import Duration
        return Duration.make(self)

    # Random
    @staticmethod
    def random(r=None):
        import random
        if r is None:
            return random.randint(Int.min_val(), Int.max_val())
        # r should be a Range object
        start = r._start if hasattr(r, '_start') else 0
        end = r._end if hasattr(r, '_end') else 100
        exclusive = r._exclusive if hasattr(r, '_exclusive') else False
        if exclusive:
            # Exclusive range: [start, end)
            if end <= start:
                from .Err import ArgErr
                raise ArgErr(f"Range end < start: {r}")
            return random.randint(start, end - 1)
        else:
            # Inclusive range: [start, end]
            if end < start:
                from .Err import ArgErr
                raise ArgErr(f"Range end < start: {r}")
            return random.randint(start, end)

    @staticmethod
    def _get_locale_separators(locale=None):
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
    def to_locale(self, pattern=None, locale=None):
        """Format int according to locale pattern"""
        # Get locale-specific thousands separator
        thousands_sep, decimal_sep = Int._get_locale_separators(locale)

        # Special case: "B" pattern formats as bytes with KB/MB/GB suffix
        if pattern == "B":
            return Int._to_locale_bytes(self, locale)

        if pattern is None:
            # Default: add thousands separators (3-digit groups)
            return Int._format_with_grouping(self, 3, thousands_sep)

        # Handle patterns like "#,###" or "#,####" or "0000"
        # Check for suffix patterns (alpha characters at end)
        suffix = ""
        if pattern and pattern[-1].isalpha():
            suffix = pattern[-1]
            pattern = pattern[:-1]
            if not pattern:
                return str(self) + suffix

        # Handle decimal patterns like "#,###.0" or "0.00"
        # For integers, we format the integer part then append the decimal portion
        decimal_format = ""
        if '.' in pattern:
            int_pattern, dec_pattern = pattern.split('.', 1)
            # Build decimal format based on pattern
            # '0' = required digit, '#' = optional digit
            # For integers, required decimal places are all zeros
            decimal_format = decimal_sep + ('0' * len(dec_pattern.replace('#', '')))
            # If pattern has only '#' after decimal, no decimals for integer
            if not decimal_format or decimal_format == decimal_sep:
                decimal_format = ""
            pattern = int_pattern

        # Parse grouping from pattern like "#,###" -> group size 3
        if ',' in pattern:
            parts = pattern.split(',')
            # Group size is the length of the last segment
            group_size = len(parts[-1])
            return Int._format_with_grouping(self, group_size, thousands_sep) + decimal_format + suffix

        # Fixed width with leading zeros (pattern like "000")
        if pattern.startswith('0'):
            width = len(pattern)
            s = str(abs(self)).zfill(width)
            result = ('-' + s) if self < 0 else s
            return result + decimal_format + suffix

        # Pattern "#" - no grouping
        if pattern == '#':
            return str(self) + decimal_format + suffix

        return str(self) + decimal_format + suffix

    @staticmethod
    def _format_with_grouping(val, group_size, sep):
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
    def _to_locale_bytes(b, locale=None):
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
            return Float.to_locale(b / KB, "#.#", locale) + "KB"
        if b < MB:
            return str(round(b / KB)) + "KB"
        if b < 10 * MB:
            return Float.to_locale(b / MB, "#.#", locale) + "MB"
        if b < GB:
            return str(round(b / MB)) + "MB"
        if b < 10 * GB:
            return Float.to_locale(b / GB, "#.#", locale) + "GB"
        return str(round(b / GB)) + "GB"

    @staticmethod
    def trap(self, name, args=None):
        """Dynamic method invocation with automatic name conversion.

        Supports both Fantom names (camelCase) and Python names (snake_case).
        Uses dynamic getattr() lookup instead of hardcoded map.
        """
        if args is None:
            args = []

        # First try exact match
        method = getattr(Int, name, None)

        # Try camelCase -> snake_case conversion
        if method is None:
            snake_name = _camel_to_snake(name)
            method = getattr(Int, snake_name, None)

        # Try adding underscore for Python builtins (and -> and_, or -> or_)
        if method is None and not name.endswith('_'):
            method = getattr(Int, name + '_', None)

        if method is not None and callable(method):
            return method(self, *args)

        raise AttributeError(f"Int.{name}")

    # Constants
    @staticmethod
    def max_val():
        return 9223372036854775807  # 2^63 - 1

    @staticmethod
    def min_val():
        return -9223372036854775808  # -2^63

    @staticmethod
    def to_date_time(ticks, tz=None):
        """Convert ticks to DateTime"""
        from .DateTime import DateTime
        return DateTime.make_ticks(ticks, tz)
