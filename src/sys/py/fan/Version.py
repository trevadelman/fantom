#
# Version - Version number for Fantom
#
from fan.sys.Obj import Obj

class Version(Obj):
    """
    Version represents a version number like 1.2.3.
    """

    _cache = {}

    def __init__(self, segments):
        self._segments = list(segments)

    @staticmethod
    def fromStr(s, checked=True):
        """Parse a Version from string like '1.2.3'"""
        if s in Version._cache:
            return Version._cache[s]

        try:
            segments = [int(p) for p in s.split(".")]
            v = Version(segments)
            Version._cache[s] = v
            return v
        except Exception as e:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid version: {s}")
            return None

    @staticmethod
    def make(segments):
        """Create from list of Int segments"""
        return Version(list(segments))

    @staticmethod
    def defVal():
        """Default version 0"""
        return Version([0])

    def segments(self):
        """Get version segments as read-only list"""
        from fan.sys.List import List
        result = List.fromList(self._segments)
        return result.toImmutable()  # Return immutable list

    def major(self):
        """Get major version number"""
        return self._segments[0] if len(self._segments) > 0 else 0

    def minor(self):
        """Get minor version number or null"""
        return self._segments[1] if len(self._segments) > 1 else None

    def build(self):
        """Get build number or null"""
        return self._segments[2] if len(self._segments) > 2 else None

    def patch(self):
        """Get patch number or null"""
        return self._segments[3] if len(self._segments) > 3 else None

    def toStr(self):
        """String representation"""
        return ".".join(str(s) for s in self._segments)

    def equals(self, other):
        """Test equality"""
        if not isinstance(other, Version):
            return False
        return self._segments == other._segments

    def hash_(self):
        """Hash code - matches Fantom's algorithm"""
        # Fantom's hash: combine segment hashes
        h = 0
        for seg in self._segments:
            h = (h * 31) ^ seg
        # Ensure fits in signed 32-bit range like Java/Fantom
        return h & 0x7FFFFFFF

    def compare(self, other):
        """Compare to another version"""
        if not isinstance(other, Version):
            return 1
        for i in range(max(len(self._segments), len(other._segments))):
            a = self._segments[i] if i < len(self._segments) else 0
            b = other._segments[i] if i < len(other._segments) else 0
            if a < b:
                return -1
            if a > b:
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
