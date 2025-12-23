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
        self._flags = flags
        self._compiled = re.compile(pattern, flags)

    @staticmethod
    def fromStr(pattern, checked=True):
        """Parse a Regex from string pattern"""
        try:
            return Regex(pattern)
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
        """Quote special regex characters in string"""
        return re.escape(s)

    @staticmethod
    def defVal():
        """Default value is empty pattern"""
        return Regex("")

    def toStr(self):
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
        """Split string using this pattern as delimiter"""
        from fan.sys.List import List
        if limit == 0:
            return List.fromList(self._compiled.split(s))
        else:
            return List.fromList(self._compiled.split(s, limit - 1))

    def equals(self, other):
        """Test equality"""
        if not isinstance(other, Regex):
            return False
        return self._pattern == other._pattern and self._flags == other._flags

    def hash_(self):
        """Hash code"""
        return hash(self._pattern)


class RegexMatcher(Obj):
    """
    RegexMatcher is used to iterate through matches in a string.
    """

    def __init__(self, compiled, s):
        self._compiled = compiled
        self._s = s
        self._match = None
        self._pos = 0
        self._matches_iter = None

    def matches(self):
        """Return true if entire input matches the pattern"""
        self._match = self._compiled.fullmatch(self._s)
        return self._match is not None

    def find(self):
        """Find next match in input"""
        self._match = self._compiled.search(self._s, self._pos)
        if self._match:
            self._pos = self._match.end()
            return True
        return False

    def replaceFirst(self, replacement):
        """Replace first occurrence"""
        return self._compiled.sub(replacement, self._s, count=1)

    def replaceAll(self, replacement):
        """Replace all occurrences"""
        return self._compiled.sub(replacement, self._s)

    def group(self, group=None):
        """Get matched group (0 = whole match, 1+ = capturing groups)"""
        if self._match is None:
            return None
        if group is None:
            return self._match.group(0)
        return self._match.group(group)

    def groupCount(self):
        """Get number of capturing groups"""
        if self._match is None:
            return 0
        return len(self._match.groups())

    def start(self, group=0):
        """Get start index of match"""
        if self._match is None:
            return -1
        return self._match.start(group)

    def end(self, group=0):
        """Get end index of match"""
        if self._match is None:
            return -1
        return self._match.end(group)

    def toStr(self):
        """String representation"""
        return f"RegexMatcher({self._compiled.pattern})"
