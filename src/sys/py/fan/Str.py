#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Str(Obj):
    """String type - uses static methods on native str"""

    @staticmethod
    def def_val():
        return ""

    @staticmethod
    def is_immutable(self):
        return True

    @staticmethod
    def to_immutable(self):
        """Strings are already immutable, return self"""
        return self

    @staticmethod
    def typeof(self):
        return "sys::Str"

    @staticmethod
    def hash(self):
        return hash(self)

    @staticmethod
    def hash_(self):
        return Str.hash(self)

    @staticmethod
    def equals(self, other):
        if other is None:
            return False
        return self == other

    # Size and access
    @staticmethod
    def size(self):
        if self is None:
            from .Err import NullErr
            raise NullErr.make("Str.size")
        return len(self)

    @staticmethod
    def is_empty(self):
        return len(self) == 0

    @staticmethod
    def get(self, index):
        return ord(self[index])

    @staticmethod
    def get_safe(self, index, default=0):
        if index < 0 or index >= len(self):
            return default
        return ord(self[index])

    @staticmethod
    def get_range(self, r):
        """Get substring from range"""
        from .Err import IndexErr
        n = len(self)

        # Use Range's index resolution methods which handle negative indices
        # and throw IndexErr for out of bounds
        s = r.start_(n)
        e = r.end_(n)

        # Check for inverted range (e+1 < s means empty/invalid)
        if e + 1 < s:
            raise IndexErr(str(r))

        return self[s:e+1]

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

    @staticmethod
    def compare_ignore_case(self, that):
        return Str.compare(self.lower(), that.lower())

    # Concatenation
    @staticmethod
    def plus(self, obj):
        from .ObjUtil import ObjUtil
        if obj is None:
            return self + "null"
        return self + ObjUtil.to_str(obj)

    # Transformations
    @staticmethod
    def upper(self):
        """Convert to uppercase - return same object if no change needed (ASCII only)"""
        # Check if already all uppercase
        for ch in self:
            c = ord(ch)
            if 97 <= c <= 122:  # lowercase a-z
                # Needs change - use Fantom's ASCII-only conversion
                upper = ""
                for c2 in self:
                    code = ord(c2)
                    if 97 <= code <= 122:
                        upper += chr(code & ~0x20)
                    else:
                        upper += c2
                return upper
        return self  # Return same object - no change needed

    @staticmethod
    def lower(self):
        """Convert to lowercase - return same object if no change needed (ASCII only)"""
        # Check if already all lowercase
        for ch in self:
            c = ord(ch)
            if 65 <= c <= 90:  # uppercase A-Z
                # Needs change - use Fantom's ASCII-only conversion
                lower = ""
                for c2 in self:
                    code = ord(c2)
                    if 65 <= code <= 90:
                        lower += chr(code | 0x20)
                    else:
                        lower += c2
                return lower
        return self  # Return same object - no change needed

    @staticmethod
    def capitalize(self):
        """Capitalize first char - return same object if no change needed"""
        if len(self) == 0:
            return self
        ch = ord(self[0])
        if 97 <= ch <= 122:  # lowercase a-z - needs change
            return chr(ch & ~0x20) + self[1:]
        return self  # Return same object - already capitalized or not ASCII letter

    @staticmethod
    def decapitalize(self):
        """Decapitalize first char - return same object if no change needed"""
        if len(self) == 0:
            return self
        ch = ord(self[0])
        if 65 <= ch <= 90:  # uppercase A-Z - needs change
            return chr(ch | 0x20) + self[1:]
        return self  # Return same object - already decapitalized or not ASCII letter

    @staticmethod
    def trim(self):
        """Trim chars <= 0x20 (space) from both ends - return same object if no change"""
        n = len(self)
        if n == 0:
            return self
        start = 0
        end = n
        while start < end and ord(self[start]) <= 0x20:
            start += 1
        while end > start and ord(self[end - 1]) <= 0x20:
            end -= 1
        # Return same object if nothing was trimmed
        if start == 0 and end == n:
            return self
        return self[start:end]

    @staticmethod
    def trim_start(self):
        """Trim chars <= 0x20 (space) from start - return same object if no change"""
        n = len(self)
        if n == 0:
            return self
        start = 0
        while start < n and ord(self[start]) <= 0x20:
            start += 1
        # Return same object if nothing was trimmed
        if start == 0:
            return self
        return self[start:]

    @staticmethod
    def trim_end(self):
        """Trim chars <= 0x20 (space) from end - return same object if no change"""
        n = len(self)
        if n == 0:
            return self
        end = n
        while end > 0 and ord(self[end - 1]) <= 0x20:
            end -= 1
        # Return same object if nothing was trimmed
        if end == n:
            return self
        return self[:end]

    @staticmethod
    def trim_to_null(self):
        """Trim and return null if empty"""
        result = Str.trim(self)
        return None if len(result) == 0 else result

    @staticmethod
    def reverse(self):
        """Reverse string - return same object if length <= 1"""
        # Single char or empty strings are their own reverse
        if len(self) <= 1:
            return self
        return self[::-1]

    @staticmethod
    def replace(self, old, new):
        """Replace all occurrences of old with new"""
        # In Fantom, replacing empty string is a no-op
        if len(old) == 0:
            return self
        return self.replace(old, new)

    # Search
    @staticmethod
    def contains(self, s):
        return s in self

    @staticmethod
    def contains_char(self, ch):
        """Check if string contains the character (given as codepoint)"""
        return chr(ch) in self

    @staticmethod
    def starts_with(self, s):
        return self.startswith(s)

    @staticmethod
    def ends_with(self, s):
        return self.endswith(s)

    @staticmethod
    def index(self, s, off=0):
        try:
            return self.index(s, off)
        except ValueError:
            return None

    @staticmethod
    def indexr(self, s, off=None):
        """Find last index of s, searching backwards from off (default end)"""
        try:
            n = len(self)
            if off is None:
                return self.rindex(s)
            # Convert negative offset to positive
            if off < 0:
                off = n + off
            # Clamp to valid range
            if off < 0:
                off = 0
            if off >= n:
                off = n - 1
            # Find last occurrence where match STARTS at or before off
            # We need to include matches that start at 'off' but extend beyond
            # So search in self[0:off+len(s)] (clamped to string length)
            end = min(off + len(s), n)
            idx = self.rfind(s, 0, end)
            # Make sure the match starts at or before off
            while idx > off:
                # Match starts after off, search again
                end = idx + len(s) - 1
                idx = self.rfind(s, 0, end)
            return idx if idx >= 0 else None
        except ValueError:
            return None

    # Split/Join
    @staticmethod
    def split(self, sep=None, trimmed=True):
        """Split string on whitespace or separator (int for char code)"""
        from .List import List
        if sep is None:
            # Split on whitespace
            if len(self) == 0:
                return List.from_literal([""], "sys::Str")
            result = self.split()
            if trimmed:
                result = [s.strip() for s in result if s.strip()]
            if len(result) == 0:
                return List.from_literal([""], "sys::Str")  # All whitespace returns empty string
            return List.from_literal(result, "sys::Str")
        else:
            # Convert int separator to char
            if isinstance(sep, int):
                sep = chr(sep)
            # Handle empty string case
            if len(self) == 0:
                return List.from_literal([""], "sys::Str")
            result = self.split(sep)
            if trimmed:
                # Trim each part but keep empty strings
                result = [s.strip() for s in result]
            return List.from_literal(result, "sys::Str")

    @staticmethod
    def split_lines(self):
        """Split string into lines - preserves empty strings unlike Python's splitlines.
        Returns a Fantom List, not a Python list.
        """
        from .List import List
        if len(self) == 0:
            return List.from_literal([""], "sys::Str")
        result = self.splitlines(keepends=False)
        # Append empty string if original ended with newline
        if self.endswith('\n') or self.endswith('\r'):
            result.append("")
        return List.from_literal(result if result else [""], "sys::Str")

    # Padding
    @staticmethod
    def padl(self, width, ch=32):
        return self.rjust(width, chr(ch))

    @staticmethod
    def padr(self, width, ch=32):
        return self.ljust(width, chr(ch))

    # Conversion
    @staticmethod
    def to_str(self):
        return self

    @staticmethod
    def to_uri(s):
        """Convert string to Uri"""
        from .Uri import Uri
        return Uri.from_str(s)

    @staticmethod
    def to_regex(self):
        """Convert string to Regex pattern"""
        from .Regex import Regex
        return Regex.from_str(self)

    @staticmethod
    def to_code(self, quote='"', escapeUnicode=False):
        """Convert to Fantom string literal code.

        Uses Fantom escape syntax:
        - \\n, \\r, \\t, \\f for control chars
        - \\\\, \\$, \\", \\', \\` for special chars
        - \\u{hex} for other control chars and non-ASCII when escapeUnicode=true
        """
        # Handle quote as int (char code)
        if isinstance(quote, int):
            quote = chr(quote)
        result = []
        for ch in self:
            c = ord(ch)
            if ch == '\\':
                result.append('\\\\')
            elif ch == '$':
                result.append('\\$')
            elif quote is not None and ch == quote:
                result.append('\\' + quote)
            elif ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            elif ch == '\f':
                result.append('\\f')
            elif c < 0x20:
                # Control characters use \u{hex} format
                result.append(f'\\u{{{c:x}}}')
            elif escapeUnicode and c > 0x7f:
                # Non-ASCII characters when escapeUnicode=true
                result.append(f'\\u{{{c:x}}}')
            else:
                result.append(ch)
        # If no quote specified, return raw escaped content
        if quote is None:
            return ''.join(result)
        return quote + ''.join(result) + quote

    @staticmethod
    def to_bool(self, checked=True):
        lower = self.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
        if not checked:
            return None
        from .Err import ParseErr
        raise ParseErr.make_str("Bool", self)

    @staticmethod
    def to_int(self, radix=10, checked=True):
        try:
            return int(self, radix)
        except ValueError:
            if not checked:
                return None
            from .Err import ParseErr
            raise ParseErr.make_str("Int", self)

    @staticmethod
    def to_float(self, checked=True):
        try:
            return float(self)
        except ValueError:
            if not checked:
                return None
            from .Err import ParseErr
            raise ParseErr.make_str("Float", self)

    # Parsing (static)
    @staticmethod
    def from_str(s, checked=True):
        return s

    # Characters
    @staticmethod
    def chars(self):
        from .List import List as FanList
        return FanList.from_literal([ord(c) for c in self], "sys::Int")

    @staticmethod
    def _get_param_count(f):
        """Get number of required parameters for a function"""
        # Check if f is a Func instance - use its params() method
        from .Func import Func
        if isinstance(f, Func):
            return len(f.params())

        import inspect
        try:
            sig = inspect.signature(f)
            return len([p for p in sig.parameters.values()
                       if p.default is inspect.Parameter.empty])
        except:
            return 1

    @staticmethod
    def each(self, f):
        """Iterate over each char (as Int codepoint), optionally with index"""
        param_count = Str._get_param_count(f)
        if param_count >= 2:
            for i, ch in enumerate(self):
                f(ord(ch), i)
        else:
            for ch in self:
                f(ord(ch))

    @staticmethod
    def each_while(self, f):
        """Iterate until f returns non-null"""
        param_count = Str._get_param_count(f)
        if param_count >= 2:
            for i, ch in enumerate(self):
                result = f(ord(ch), i)
                if result is not None:
                    return result
        else:
            for ch in self:
                result = f(ord(ch))
                if result is not None:
                    return result
        return None

    # Cache for spaces strings (like Fantom does)
    _spaces_cache = {}

    @staticmethod
    def spaces(n):
        """Return string of n space characters - cached for small values"""
        if n < 20:
            # Use cache for small values for identity equality
            if n not in Str._spaces_cache:
                Str._spaces_cache[n] = " " * n
            return Str._spaces_cache[n]
        return " " * n

    # String tests
    @staticmethod
    def is_space(self):
        """Return true if all chars are whitespace (or empty)"""
        for ch in self:
            if ord(ch) > 0x20:
                return False
        return True

    @staticmethod
    def is_alpha(self):
        """Return true if all chars are ASCII alpha (or empty)"""
        for ch in self:
            c = ord(ch)
            if not ((65 <= c <= 90) or (97 <= c <= 122)):
                return False
        return True

    @staticmethod
    def is_alpha_num(self):
        """Return true if all chars are ASCII alphanumeric (or empty)"""
        for ch in self:
            c = ord(ch)
            if not ((48 <= c <= 57) or (65 <= c <= 90) or (97 <= c <= 122)):
                return False
        return True

    @staticmethod
    def is_upper(self):
        """Return true if all chars are ASCII uppercase letters (or empty)"""
        for ch in self:
            c = ord(ch)
            # Must be uppercase ASCII letter A-Z
            if not (65 <= c <= 90):
                return False
        return True

    @staticmethod
    def is_lower(self):
        """Return true if all chars are ASCII lowercase letters (or empty)"""
        for ch in self:
            c = ord(ch)
            # Must be lowercase ASCII letter a-z
            if not (97 <= c <= 122):
                return False
        return True

    @staticmethod
    def is_ascii(self):
        """Return true if all chars are ASCII (0-127)"""
        for ch in self:
            if ord(ch) > 127:
                return False
        return True

    # Equality with case options
    @staticmethod
    def equals_ignore_case(self, that):
        """Case-insensitive equality"""
        if that is None:
            return False
        return self.lower() == that.lower()

    # Additional index methods
    @staticmethod
    def index_ignore_case(self, s, off=0):
        """Case-insensitive index search"""
        try:
            return self.lower().index(s.lower(), off)
        except ValueError:
            return None

    @staticmethod
    def indexr_ignore_case(self, s, off=None):
        """Case-insensitive reverse index search"""
        try:
            lower_self = self.lower()
            lower_s = s.lower()
            n = len(lower_self)
            if off is None:
                return lower_self.rindex(lower_s)
            # Convert negative offset to positive
            if off < 0:
                off = n + off
            # Clamp to valid range
            if off < 0:
                off = 0
            if off >= n:
                off = n - 1
            # Find last occurrence where match STARTS at or before off
            end = min(off + len(lower_s), n)
            idx = lower_self.rfind(lower_s, 0, end)
            # Make sure the match starts at or before off
            while idx > off:
                end = idx + len(lower_s) - 1
                idx = lower_self.rfind(lower_s, 0, end)
            return idx if idx >= 0 else None
        except ValueError:
            return None

    # Justify methods (aliases for pad)
    @staticmethod
    def justl(self, width):
        """Left justify (pad right)"""
        return self.ljust(width)

    @staticmethod
    def justr(self, width):
        """Right justify (pad left)"""
        return self.rjust(width)

    # Reverse iteration
    @staticmethod
    def eachr(self, f):
        """Iterate over each char in reverse (as Int codepoint), optionally with index"""
        param_count = Str._get_param_count(f)
        if param_count >= 2:
            for i in range(len(self) - 1, -1, -1):
                f(ord(self[i]), i)
        else:
            for ch in reversed(self):
                f(ord(ch))

    # Newline counting
    @staticmethod
    def num_newlines(self):
        """Count number of newline chars (\n or \r)"""
        count = 0
        i = 0
        while i < len(self):
            ch = self[i]
            if ch == '\n':
                count += 1
            elif ch == '\r':
                count += 1
                # Don't double-count \r\n
                if i + 1 < len(self) and self[i + 1] == '\n':
                    i += 1
            i += 1
        return count

    # InStream from string
    @staticmethod
    def in_(self):
        """Get an InStream to read from this string"""
        from .InStream import StrInStream
        return StrInStream(self)

    # Predicate methods
    @staticmethod
    def all_(self, f):
        """Return true if f returns true for all chars"""
        param_count = Str._get_param_count(f)
        if param_count >= 2:
            for i, ch in enumerate(self):
                if not f(ord(ch), i):
                    return False
        else:
            for ch in self:
                if not f(ord(ch)):
                    return False
        return True

    @staticmethod
    def any_(self, f):
        """Return true if f returns true for any char"""
        param_count = Str._get_param_count(f)
        if param_count >= 2:
            for i, ch in enumerate(self):
                if f(ord(ch), i):
                    return True
        else:
            for ch in self:
                if f(ord(ch)):
                    return True
        return False

    @staticmethod
    def from_chars(chars):
        """Create string from list of char codepoints"""
        return ''.join(chr(c) for c in chars)

    @staticmethod
    def intern(self):
        """Return interned (canonical) version of this string"""
        import sys
        return sys.intern(self)

    @staticmethod
    def to_locale(self):
        """Return locale string representation (same as toStr for strings)"""
        return self

    @staticmethod
    def locale_upper(self):
        """Convert to uppercase using current locale"""
        return self.upper()

    @staticmethod
    def locale_lower(self):
        """Convert to lowercase using current locale"""
        return self.lower()

    @staticmethod
    def locale_compare(self, that):
        """Compare strings using locale rules"""
        return Str.compare(self, that)

    @staticmethod
    def locale_capitalize(self):
        """Capitalize using current locale"""
        return self.capitalize()

    @staticmethod
    def locale_decapitalize(self):
        """Decapitalize using current locale"""
        if len(self) == 0:
            return self
        return self[0].lower() + self[1:]

    @staticmethod
    def each_line(self, f):
        """Iterate over each line"""
        lines = Str.split_lines(self)
        for line in lines:
            f(line)

    @staticmethod
    def to_decimal(self, checked=True):
        """Convert to Decimal"""
        from decimal import Decimal as PyDecimal, InvalidOperation
        try:
            return float(PyDecimal(self))
        except (InvalidOperation, ValueError):
            if not checked:
                return None
            from .Err import ParseErr
            raise ParseErr.make_str("Decimal", self)

    @staticmethod
    def to_display_name(self):
        """Convert camelCase to display name with spaces.

        XMLCode -> XML Code
        fooBar -> Foo Bar
        FooBar -> Foo Bar
        2days -> 2 Days
        5foo -> 5 Foo
        f_b -> F B
        foo_bar -> Foo Bar
        """
        if len(self) == 0:
            return self
        n = len(self)
        result = []
        capitalize_next = False

        for i, ch in enumerate(self):
            c = ord(ch)
            curr_is_upper = 65 <= c <= 90
            curr_is_lower = 97 <= c <= 122
            curr_is_digit = 48 <= c <= 57
            curr_is_underscore = ch == '_'

            # Skip underscores - replace with space and capitalize next
            if curr_is_underscore:
                result.append(' ')
                capitalize_next = True
                continue

            if i > 0:
                # Get actual previous char (before underscore handling)
                prev_idx = i - 1
                while prev_idx >= 0 and self[prev_idx] == '_':
                    prev_idx -= 1
                if prev_idx >= 0:
                    prev = ord(self[prev_idx])
                    prev_is_upper = 65 <= prev <= 90
                    prev_is_lower = 97 <= prev <= 122
                    prev_is_digit = 48 <= prev <= 57
                else:
                    prev_is_upper = prev_is_lower = prev_is_digit = False

                # Look ahead for lowercase (skip underscores)
                next_is_lower = False
                next_idx = i + 1
                while next_idx < n and self[next_idx] == '_':
                    next_idx += 1
                if next_idx < n:
                    next_c = ord(self[next_idx])
                    next_is_lower = 97 <= next_c <= 122

                # Insert space before uppercase if:
                # 1. Previous is lowercase, OR
                # 2. Previous is uppercase AND next is lowercase (end of acronym)
                if curr_is_upper and not capitalize_next:
                    if not prev_is_upper:
                        result.append(' ')
                    elif next_is_lower:
                        # End of acronym like "XMLCode" - space before 'C'
                        result.append(' ')
                # Insert space before digit sequence (after non-digit)
                elif curr_is_digit and not prev_is_digit and not capitalize_next:
                    result.append(' ')
                # Insert space before letter after digit, and capitalize
                elif curr_is_lower and prev_is_digit and not capitalize_next:
                    result.append(' ')
                    # Capitalize this letter
                    ch = chr(c & ~0x20)

            # Handle capitalize_next from underscore
            if capitalize_next and curr_is_lower:
                ch = chr(c & ~0x20)
                capitalize_next = False
            elif capitalize_next:
                capitalize_next = False

            result.append(ch)

        # Capitalize first letter
        s = ''.join(result)
        if len(s) > 0 and ord(s[0]) >= 97 and ord(s[0]) <= 122:
            s = chr(ord(s[0]) & ~0x20) + s[1:]
        return s

    @staticmethod
    def from_display_name(self):
        """Convert display name with spaces to camelCase.

        "Foo Bar" -> "fooBar"
        "IO File" -> "IOFile"
        "file XML" -> "fileXML"
        """
        if len(self) == 0:
            return self

        # Split on spaces
        words = self.split(' ')
        result = []

        for i, word in enumerate(words):
            if not word:
                continue
            if i == 0:
                # First word - lowercase first char only if it's uppercase
                # But keep rest of case (e.g., "IO" stays "IO", "Foo" -> "foo")
                c = ord(word[0])
                if 65 <= c <= 90:  # uppercase
                    # Check if whole word is uppercase (acronym)
                    is_acronym = all(65 <= ord(ch) <= 90 or not (97 <= ord(ch) <= 122) for ch in word)
                    if is_acronym and len(word) > 1:
                        # Preserve acronym case
                        result.append(word)
                    else:
                        # Lowercase first char
                        result.append(chr(c | 0x20) + word[1:])
                else:
                    result.append(word)
            else:
                # Subsequent words - just append as-is (capitalize first if lowercase)
                c = ord(word[0])
                if 97 <= c <= 122:  # lowercase
                    result.append(chr(c & ~0x20) + word[1:])
                else:
                    result.append(word)

        return ''.join(result)

    @staticmethod
    def to_xml(self):
        """Escape string for XML - return same object if no escaping needed.

        Rules:
        - & -> &amp;
        - < -> &lt;
        - > -> &gt; only at start of string or after ]
        - " -> &quot;
        - ' -> &#39;
        """
        n = len(self)
        # First pass: check if any escaping is needed
        needs_escape = False
        for i, ch in enumerate(self):
            if ch in ('&', '<', '"', "'"):
                needs_escape = True
                break
            elif ch == '>':
                # > needs escaping at start or after ]
                if i == 0 or self[i-1] == ']':
                    needs_escape = True
                    break
        # Return same object if no escaping needed
        if not needs_escape:
            return self
        # Build escaped string
        result = []
        for i, ch in enumerate(self):
            if ch == '&':
                result.append('&amp;')
            elif ch == '<':
                result.append('&lt;')
            elif ch == '>':
                # > needs escaping at start or after ]
                if i == 0 or self[i-1] == ']':
                    result.append('&gt;')
                else:
                    result.append('>')
            elif ch == '"':
                result.append('&quot;')
            elif ch == "'":
                result.append('&#39;')
            else:
                result.append(ch)
        return ''.join(result)

    @staticmethod
    def to_buf(self, charset=None):
        """Convert to Buf using given charset"""
        # For now, use UTF-8 encoding
        from .Buf import Buf
        encoding = "utf-8" if charset is None else str(charset)
        return Buf(self.encode(encoding))

    @staticmethod
    def mult(self, times):
        """Repeat string n times"""
        return self * times
