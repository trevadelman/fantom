#
# Regex - Regular expression support for Fantom
#
import re
from fan.sys.Obj import Obj

class Regex(Obj):
    """
    Regex represents a compiled regular expression.
    """

    # Cache for compiled patterns
    _cache = {}

    def __init__(self, pattern, flags=0):
        self._pattern = pattern
        # Convert string flags to Python int flags
        if isinstance(flags, str):
            int_flags = 0
            if 'i' in flags:
                int_flags |= re.IGNORECASE
            if 'm' in flags:
                int_flags |= re.MULTILINE
            if 's' in flags:
                int_flags |= re.DOTALL
            if 'x' in flags:
                int_flags |= re.VERBOSE
            flags = int_flags
        self._flags = flags
        # Pre-process pattern for Java regex escapes not in Python
        processed = self._preprocess_pattern(pattern)
        self._compiled = re.compile(processed, flags)

    @staticmethod
    def _preprocess_pattern(pattern):
        """Convert Java regex escapes to Python equivalents.

        Java/Fantom regex has features Python doesn't support natively:
        - \\e (escape character)
        - \\p{...} and \\P{...} POSIX/Unicode property escapes
        - \\Q...\\E quotation
        - Possessive quantifiers (*+, ++, ?+, {n}+, etc.)
        """
        import re as py_re
        result = pattern

        # \e (escape char) -> \x1b
        result = result.replace('\\e', '\\x1b')

        # Handle \Q...\E quotation (quote everything inside literally)
        def replace_quotation(m):
            quoted = m.group(1)
            return py_re.escape(quoted)
        result = py_re.sub(r'\\Q(.*?)\\E', replace_quotation, result)

        # Handle \p{...} and \P{...} property escapes
        # We need to be careful about context - inside vs outside character classes
        result = Regex._convert_property_escapes(result)

        # Handle possessive quantifiers - convert to greedy (not exact but functional)
        # *+ -> *(?:) atomic group approximation - just use greedy for now
        # This is an approximation since Python doesn't have possessive quantifiers
        result = py_re.sub(r'\*\+', '*', result)
        result = py_re.sub(r'\+\+', '+', result)
        result = py_re.sub(r'\?\+', '?', result)
        result = py_re.sub(r'\{(\d+(?:,\d*)?)\}\+', r'{\1}', result)

        return result

    @staticmethod
    def _convert_property_escapes(pattern):
        """Convert \\p{...} and \\P{...} property escapes to Python equivalents."""
        import re as py_re

        # Property class mappings (positive \p{...})
        # These map Java/POSIX property names to Python character class equivalents
        property_map = {
            # POSIX classes
            'Lower': 'a-z',
            'Upper': 'A-Z',
            'ASCII': '\x00-\x7f',
            'Alpha': 'a-zA-Z',
            'Digit': '0-9',
            'Alnum': 'a-zA-Z0-9',
            'Punct': '!"#$%&\'()*+,\\-./:;<=>?@\\[\\]^_`{|}~',
            'Graph': 'a-zA-Z0-9!"#$%&\'()*+,\\-./:;<=>?@\\[\\]^_`{|}~',
            'Print': 'a-zA-Z0-9!"#$%&\'()*+,\\-./:;<=>?@\\[\\]^_`{|}~ ',
            'Blank': ' \t',
            'Cntrl': '\x00-\x1f\x7f',
            'XDigit': '0-9a-fA-F',
            'Space': ' \t\n\x0b\f\r',
            # Unicode categories
            'L': 'a-zA-Z',  # Letter (simplified)
            'Lu': 'A-Z',    # Uppercase letter
            'Ll': 'a-z',    # Lowercase letter
            'S': '',        # Symbol (simplified - empty for now)
            'Sc': '$\xa2\xa3\xa4\xa5',  # Currency symbol
            # Java character classes
            'javaLowerCase': 'a-z',
            'javaUpperCase': 'A-Z',
            'javaWhitespace': ' \t\n\x0b\f\r',
            'javaMirrored': '',  # Complex - return empty
        }

        # Negative property class mappings (for use outside character classes)
        # \P{ASCII} means NOT ASCII, so [^\x00-\x7f]
        neg_property_map = {
            'Lower': '^a-z',
            'Upper': '^A-Z',
            'ASCII': '^\\x00-\\x7f',
            'Alpha': '^a-zA-Z',
            'Digit': '^0-9',
            'Alnum': '^a-zA-Z0-9',
            'Punct': '^!"#$%&\'()*+,\\-./:;<=>?@\\[\\]^_`{|}~',
            'Graph': '^a-zA-Z0-9!"#$%&\'()*+,\\-./:;<=>?@\\[\\]^_`{|}~',
            'Print': '^a-zA-Z0-9!"#$%&\'()*+,\\-./:;<=>?@\\[\\]^_`{|}~ ',
            'Blank': '^ \t',
            'Cntrl': '^\x00-\x1f\x7f',
            'XDigit': '^0-9a-fA-F',
            'Space': '^ \t\n\x0b\f\r',
            'L': '^a-zA-Z',
            'Lu': '^A-Z',
            'Ll': '^a-z',
            'S': '',
            'Sc': '^$\xa2\xa3\xa4\xa5',
            'javaLowerCase': '^a-z',
            'javaUpperCase': '^A-Z',
            'javaWhitespace': '^ \t\n\x0b\f\r',
            'javaMirrored': '',
        }

        # For inside character class - \P{ASCII} becomes \x80-\uffff (non-ASCII range)
        neg_in_class_map = {
            'ASCII': '\x80-\uffff',
            'Lower': 'A-Z0-9_',  # Approximate - not lowercase
            'Upper': 'a-z0-9_',  # Approximate - not uppercase
            'Alpha': '0-9_',     # Approximate - not alpha
            'Digit': 'a-zA-Z_',  # Approximate - not digit
            'Alnum': '_',        # Approximate - not alnum
            'Space': 'a-zA-Z0-9',  # Approximate - not space
        }

        result = []
        i = 0
        n = len(pattern)
        in_char_class = False

        while i < n:
            # Track if we're inside a character class
            if pattern[i] == '[' and (i == 0 or pattern[i-1] != '\\'):
                in_char_class = True
                result.append(pattern[i])
                i += 1
                continue
            elif pattern[i] == ']' and (i == 0 or pattern[i-1] != '\\'):
                in_char_class = False
                result.append(pattern[i])
                i += 1
                continue

            # Check for \p{...} or \P{...}
            if i + 2 < n and pattern[i] == '\\' and pattern[i+1] in 'pP':
                is_negated = pattern[i+1] == 'P'

                # Find the property name
                if i + 2 < n and pattern[i+2] == '{':
                    # \p{PropertyName}
                    end = pattern.find('}', i+3)
                    if end != -1:
                        prop_name = pattern[i+3:end]

                        if in_char_class:
                            # Inside character class
                            if is_negated and prop_name in neg_in_class_map:
                                result.append(neg_in_class_map[prop_name])
                            elif not is_negated and prop_name in property_map:
                                result.append(property_map[prop_name])
                            else:
                                # Unknown property - try to preserve or use fallback
                                result.append('')
                        else:
                            # Outside character class - wrap in [...]
                            if is_negated and prop_name in neg_property_map:
                                result.append('[')
                                result.append(neg_property_map[prop_name])
                                result.append(']')
                            elif not is_negated and prop_name in property_map:
                                result.append('[')
                                result.append(property_map[prop_name])
                                result.append(']')
                            else:
                                # Unknown property
                                result.append('.')

                        i = end + 1
                        continue
                elif i + 2 < n:
                    # \pX - single character property (like \pL)
                    prop_name = pattern[i+2]
                    if in_char_class:
                        if is_negated and prop_name in neg_in_class_map:
                            result.append(neg_in_class_map[prop_name])
                        elif not is_negated and prop_name in property_map:
                            result.append(property_map[prop_name])
                        else:
                            result.append('')
                    else:
                        if is_negated and prop_name in neg_property_map:
                            result.append('[')
                            result.append(neg_property_map[prop_name])
                            result.append(']')
                        elif not is_negated and prop_name in property_map:
                            result.append('[')
                            result.append(property_map[prop_name])
                            result.append(']')
                        else:
                            result.append('.')
                    i += 3
                    continue

            result.append(pattern[i])
            i += 1

        return ''.join(result)

    @staticmethod
    def from_str(pattern, flags="", checked=True):
        """Parse a Regex from string pattern with optional flags"""
        try:
            return Regex(pattern, flags)
        except re.error as e:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid regex: {pattern}")
            return None

    @staticmethod
    def glob(pattern):
        """Create a Regex from a glob pattern"""
        # Convert glob to regex - no anchors since matches() uses fullmatch()
        regex = ""
        for c in pattern:
            if c == '*':
                regex += ".*"
            elif c == '?':
                regex += "."
            elif c in r'\[](){}+^$.|':
                regex += "\\" + c
            else:
                regex += c
        return Regex(regex)

    @staticmethod
    def quote(s):
        """Quote special regex characters in string and return as Regex"""
        return Regex(re.escape(s))

    @staticmethod
    def def_val():
        """Default value is empty pattern"""
        return Regex("")

    def to_str(self):
        """Return the pattern string"""
        return self._pattern

    def flags(self):
        """Return the flags string"""
        flags_str = ""
        if self._flags & re.IGNORECASE:
            flags_str += "i"
        if self._flags & re.MULTILINE:
            flags_str += "m"
        if self._flags & re.DOTALL:
            flags_str += "s"
        return flags_str

    def matches(self, s):
        """Return true if entire string matches pattern"""
        m = self._compiled.fullmatch(s)
        return m is not None

    def matcher(self, s):
        """Return a RegexMatcher to find matches in string"""
        return RegexMatcher(self._compiled, s)

    def split(self, s, limit=0):
        """Split string using this pattern as delimiter.

        Java/Fantom semantics:
        - limit > 0: pattern applied at most limit-1 times, array length <= limit
        - limit == 0: unlimited splits, trailing empty strings DISCARDED
        - limit < 0: unlimited splits, trailing empty strings KEPT
        """
        from fan.sys.List import List
        if limit == 1:
            # No splitting - return original string as single element
            return List.from_list([s])
        elif limit > 1:
            # Python maxsplit = limit - 1 (limit=2 means 1 split = 2 parts)
            parts = self._compiled.split(s, limit - 1)
        else:
            # limit <= 0: unlimited splits
            parts = self._compiled.split(s)

        # Only strip trailing empty strings when limit == 0
        if limit == 0:
            while parts and parts[-1] == '':
                parts.pop()
        return List.from_list(parts)

    def equals(self, other):
        """Test equality"""
        if not isinstance(other, Regex):
            return False
        return self._pattern == other._pattern and self._flags == other._flags

    def hash_(self):
        """Hash code"""
        return hash(self._pattern)

    def typeof(self):
        """Return the Fantom type of this object."""
        from fan.sys.Type import Type
        return Type.find("sys::Regex")

    def literal_encode(self, encoder):
        """Encode for serialization.

        Simple types serialize as: Type("toStr")
        Example: sys::Regex("foo")
        """
        encoder.w_type(self.typeof())
        encoder.w('(')
        encoder.w_str_literal(self.to_str(), '"')
        encoder.w(')')


class RegexMatcher(Obj):
    """
    RegexMatcher is used to iterate through matches in a string.
    """

    def __init__(self, compiled, s):
        self._compiled = compiled
        self._s = s
        self._match = None
        self._pos = 0
        self._was_match = None  # None = no match attempted, True/False = result

    def matches(self):
        """Return true if entire input matches the pattern"""
        self._match = self._compiled.fullmatch(self._s)
        self._was_match = self._match is not None
        return self._was_match

    def find(self):
        """Find next match in input"""
        self._match = self._compiled.search(self._s, self._pos)
        if self._match:
            self._pos = self._match.end()
            self._was_match = True
            return True
        self._was_match = False
        return False

    def replace_first(self, replacement):
        """Replace first occurrence"""
        return self._compiled.sub(replacement, self._s, count=1)

    def replace_all(self, replacement):
        """Replace all occurrences"""
        return self._compiled.sub(replacement, self._s)

    def group(self, group=None):
        """Get matched group (0 = whole match, 1+ = capturing groups)"""
        from fan.sys.Err import Err, IndexErr
        if not self._was_match:
            raise Err.make("No match found")
        gc = self.group_count()
        if group is None:
            return self._match.group(0)
        if group < 0 or group > gc:
            raise IndexErr.make(str(group))
        return self._match.group(group)

    def group_count(self):
        """Get number of capturing groups"""
        if not self._was_match:
            return 0
        return len(self._match.groups())

    def start(self, group=0):
        """Get start index of match"""
        from fan.sys.Err import Err, IndexErr
        if not self._was_match:
            raise Err.make("No match found")
        gc = self.group_count()
        if group < 0 or group > gc:
            raise IndexErr.make(str(group))
        return self._match.start(group)

    def end(self, group=0):
        """Get end index of match"""
        from fan.sys.Err import Err, IndexErr
        if not self._was_match:
            raise Err.make("No match found")
        gc = self.group_count()
        if group < 0 or group > gc:
            raise IndexErr.make(str(group))
        return self._match.end(group)

    def to_str(self):
        """String representation"""
        return f"RegexMatcher({self._compiled.pattern})"
