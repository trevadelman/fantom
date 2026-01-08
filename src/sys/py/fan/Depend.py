#
# Depend - Dependency specification for Fantom
#
import re
from fan.sys.Obj import Obj

class Depend(Obj):
    """
    Depend represents a pod dependency with version constraints.

    Constraint types:
    - Simple: exact version match (e.g., "foo 1.2")
    - Plus: version or higher (e.g., "foo 1.2+")
    - Range: version range (e.g., "foo 1.2-3.4")

    Multiple constraints can be comma-separated: "foo 1, 3.0-4.0, 5.2+"
    """

    # Constraint type constants
    _SIMPLE = 0
    _PLUS = 1
    _RANGE = 2

    def __init__(self, name, constraints=None):
        self._name = name
        # Each constraint is (start_version, end_version, type)
        # type: _SIMPLE, _PLUS, or _RANGE
        self._constraints = constraints or []

    @staticmethod
    def from_str(s, checked=True):
        """Parse a Depend from string like 'foo 1.0-2.0'"""
        try:
            if not s or not s.strip():
                raise ValueError("Empty depend")

            # Normalize whitespace (tabs to spaces, collapse multiple spaces)
            s = re.sub(r'[\t ]+', ' ', s.strip())

            # Check for invalid characters (newlines, etc)
            if '\n' in s or '\r' in s:
                raise ValueError("Invalid characters in depend")

            # Must start with a letter (pod name)
            if not s[0].isalpha():
                raise ValueError("Depend must start with pod name")

            # Split on first space to get name and version spec
            parts = s.split(' ', 1)
            if len(parts) < 1:
                raise ValueError("Empty depend")

            name = parts[0]

            # Validate pod name - must be identifier
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
                raise ValueError(f"Invalid pod name: {name}")

            constraints = []

            if len(parts) > 1:
                version_spec = parts[1].strip()
                if not version_spec:
                    raise ValueError("Missing version")

                # Split on comma for multiple constraints
                for constraint_str in version_spec.split(','):
                    constraint_str = constraint_str.strip()
                    # Normalize spaces around dash
                    constraint_str = re.sub(r'\s*-\s*', '-', constraint_str)

                    if not constraint_str:
                        continue

                    from fan.sys.Version import Version

                    if constraint_str.endswith('+'):
                        # Plus constraint: version or higher
                        ver_str = constraint_str[:-1].strip()
                        Depend._validate_version_str(ver_str)
                        ver = Version.from_str(ver_str)
                        constraints.append((ver, None, Depend._PLUS))
                    elif '-' in constraint_str:
                        # Range constraint
                        parts = constraint_str.split('-', 1)
                        lo_str = parts[0].strip()
                        hi_str = parts[1].strip()
                        Depend._validate_version_str(lo_str)
                        Depend._validate_version_str(hi_str)
                        lo = Version.from_str(lo_str)
                        hi = Version.from_str(hi_str)
                        constraints.append((lo, hi, Depend._RANGE))
                    else:
                        # Simple constraint: exact version
                        Depend._validate_version_str(constraint_str)
                        ver = Version.from_str(constraint_str)
                        constraints.append((ver, None, Depend._SIMPLE))
            else:
                raise ValueError("Missing version")

            if not constraints:
                raise ValueError("Missing version constraints")

            return Depend(name, constraints)
        except Exception as e:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid depend: {s}")
            return None

    @staticmethod
    def _validate_version_str(s):
        """Validate version string format"""
        if not s:
            raise ValueError("Empty version")
        # Version segments must be digits separated by dots
        if not re.match(r'^\d+(\.\d+)*$', s):
            raise ValueError(f"Invalid version: {s}")

    def name(self):
        """Get pod name"""
        return self._name

    def size(self):
        """Get number of version constraints"""
        return len(self._constraints)

    def version(self, index=None):
        """Get version at index (or first constraint's start version if no index)"""
        if index is None:
            index = 0
        if index < 0 or index >= len(self._constraints):
            return None
        return self._constraints[index][0]

    def end_version(self, index=None):
        """Get end version at index (for range constraints), null for simple/plus"""
        if index is None:
            index = 0
        if index < 0 or index >= len(self._constraints):
            return None
        constraint = self._constraints[index]
        if constraint[2] == Depend._RANGE:
            return constraint[1]
        return None

    def is_simple(self, index=None):
        """Check if constraint at index is a simple exact version"""
        if index is None:
            index = 0
        if index < 0 or index >= len(self._constraints):
            return False
        return self._constraints[index][2] == Depend._SIMPLE

    def is_plus(self, index=None):
        """Check if constraint at index is a plus (or higher) constraint"""
        if index is None:
            index = 0
        if index < 0 or index >= len(self._constraints):
            return False
        return self._constraints[index][2] == Depend._PLUS

    def is_range(self, index=None):
        """Check if constraint at index is a range constraint"""
        if index is None:
            index = 0
        if index < 0 or index >= len(self._constraints):
            return False
        return self._constraints[index][2] == Depend._RANGE

    def match_(self, version):
        """Check if version matches this dependency.

        For each constraint type:
        - Simple: version must start with constraint version segments
        - Plus: version must be >= constraint version (missing segments = 0)
        - Range: version must satisfy start prefix AND be <= end
        """
        if not self._constraints:
            return True

        from fan.sys.Version import Version

        for start_ver, end_ver, ctype in self._constraints:
            if ctype == Depend._SIMPLE:
                # Simple: version segments must match constraint as prefix
                if Depend._version_matches_prefix(version, start_ver):
                    return True
            elif ctype == Depend._PLUS:
                # Plus: version >= start (missing segments treated as 0)
                if Depend._version_gte_plus(version, start_ver):
                    return True
            elif ctype == Depend._RANGE:
                # Range: version must satisfy start prefix AND be <= end
                if Depend._version_gte_range(version, start_ver) and Depend._version_lte(version, end_ver):
                    return True
        return False

    @staticmethod
    def _version_matches_prefix(version, prefix):
        """Check if version matches prefix segments"""
        v_segs = version.segments()
        p_segs = prefix.segments()

        if len(v_segs) < len(p_segs):
            return False

        for i in range(len(p_segs)):
            if v_segs[i] != p_segs[i]:
                return False
        return True

    @staticmethod
    def _version_gte_plus(version, other):
        """Check if version >= other for Plus constraints.

        Missing segments are treated as 0.
        E.g., version "3" satisfies "2.3+" because 3.0 >= 2.3
        """
        v_segs = version.segments()
        o_segs = other.segments()

        for i in range(max(len(v_segs), len(o_segs))):
            v = v_segs[i] if i < len(v_segs) else 0
            o = o_segs[i] if i < len(o_segs) else 0
            if v > o:
                return True
            if v < o:
                return False
        return True  # Equal

    @staticmethod
    def _version_gte_range(version, other):
        """Check if version >= other for Range constraint start.

        If version's available segments are clearly greater, it matches.
        If segments are equal up to version's length, then version must
        have at least as many segments as constraint.
        E.g., "2" matches "1.2" (2 > 1)
        E.g., "3" does NOT match "3.0" (3 == 3, but missing .0 segment)
        """
        v_segs = version.segments()
        o_segs = other.segments()

        # Compare segment by segment
        for i in range(min(len(v_segs), len(o_segs))):
            v = v_segs[i]
            o = o_segs[i]
            if v > o:
                return True  # Clearly greater
            if v < o:
                return False  # Clearly less

        # Segments are equal so far
        # If version has fewer segments than constraint, it's "less specific"
        # E.g., "3" < "3.0" in specificity terms
        if len(v_segs) < len(o_segs):
            return False

        return True  # Equal or version has more segments

    @staticmethod
    def _version_lte(version, other):
        """Check if version <= other (using prefix matching for ranges)"""
        v_segs = version.segments()
        o_segs = other.segments()

        # For range matching, we need prefix semantics
        # "1.2-3" means 1.2.x through 3.x.x
        for i in range(len(o_segs)):
            v = v_segs[i] if i < len(v_segs) else 0
            o = o_segs[i]
            if v < o:
                return True
            if v > o:
                return False
        return True  # Equal up to prefix length

    def to_str(self):
        """String representation"""
        if not self._constraints:
            return self._name

        parts = []
        for start_ver, end_ver, ctype in self._constraints:
            if ctype == Depend._PLUS:
                parts.append(f"{start_ver}+")
            elif ctype == Depend._RANGE:
                parts.append(f"{start_ver}-{end_ver}")
            else:  # SIMPLE
                parts.append(str(start_ver))

        return f"{self._name} {','.join(parts)}"

    def equals(self, other):
        """Test equality"""
        if not isinstance(other, Depend):
            return False
        return self.to_str() == other.to_str()

    def hash_(self):
        """Hash code"""
        return hash(self.to_str())

    @property
    def hash(self):
        """Hash property for Fantom compatibility"""
        return self.to_str().__hash__()

    def __hash__(self):
        """Python hash"""
        return hash(self.to_str())

    def typeof(self):
        """Return the Fantom type of this object."""
        from fan.sys.Type import Type
        return Type.find("sys::Depend")

    def literal_encode(self, encoder):
        """Encode for serialization.

        Simple types serialize as: Type("toStr")
        Example: sys::Depend("foo 1.2-3.4")
        """
        encoder.w_type(self.typeof())
        encoder.w('(')
        encoder.w_str_literal(self.to_str(), '"')
        encoder.w(')')
