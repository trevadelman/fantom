#
# web::Cookie - Python native implementation
#
# HTTP cookie representation.
#

from fan.sys.Obj import Obj


class Cookie(Obj):
    """HTTP Cookie representation.

    This is a Python-native implementation for handling HTTP cookies.
    Used by WebClient to manage request/response cookies.
    """

    @staticmethod
    def make(name, val):
        """Create a new Cookie with name and value."""
        c = Cookie()
        c._name = name
        c._val = val
        return c

    @staticmethod
    def from_str(s, checked=True):
        """Parse a cookie from a Set-Cookie header value.

        Args:
            s: Set-Cookie header value string
            checked: If true, throw on parse error; if false, return None

        Returns:
            Cookie or None
        """
        try:
            c = Cookie()

            # Parse name=value; attr1; attr2=val2; ...
            parts = s.split(';')
            if not parts:
                if checked:
                    raise ValueError(f"Invalid cookie: {s}")
                return None

            # First part is name=value
            name_val = parts[0].strip()
            eq_idx = name_val.find('=')
            if eq_idx < 0:
                if checked:
                    raise ValueError(f"Invalid cookie - no '=': {s}")
                return None

            c._name = name_val[:eq_idx].strip()
            c._val = name_val[eq_idx + 1:].strip()

            # Parse attributes
            for part in parts[1:]:
                part = part.strip()
                if not part:
                    continue

                eq_idx = part.find('=')
                if eq_idx < 0:
                    attr_name = part.lower()
                    attr_val = None
                else:
                    attr_name = part[:eq_idx].strip().lower()
                    attr_val = part[eq_idx + 1:].strip()

                if attr_name == 'domain':
                    c._domain = attr_val
                elif attr_name == 'path':
                    c._path = attr_val
                elif attr_name == 'expires':
                    c._expires = attr_val  # Keep as string for now
                elif attr_name == 'max-age':
                    c._max_age = int(attr_val) if attr_val else None
                elif attr_name == 'secure':
                    c._secure = True
                elif attr_name == 'httponly':
                    c._http_only = True
                elif attr_name == 'samesite':
                    c._same_site = attr_val

            return c

        except Exception as e:
            if checked:
                raise
            return None

    def __init__(self):
        super().__init__()
        self._name = None
        self._val = None
        self._domain = None
        self._path = None
        self._expires = None
        self._max_age = None
        self._secure = False
        self._http_only = False
        self._same_site = None

    def name(self):
        """Get the cookie name."""
        return self._name

    def val(self):
        """Get the cookie value."""
        return self._val

    def domain(self):
        """Get the domain attribute."""
        return self._domain

    def path(self):
        """Get the path attribute."""
        return self._path

    def secure(self):
        """Check if cookie has Secure attribute."""
        return self._secure

    def http_only(self):
        """Check if cookie has HttpOnly attribute."""
        return self._http_only

    def to_name_val_str(self):
        """Return the cookie as 'name=value' string for Cookie header."""
        return f"{self._name}={self._val}"

    def to_str(self):
        """Full string representation including attributes."""
        parts = [f"{self._name}={self._val}"]
        if self._domain:
            parts.append(f"Domain={self._domain}")
        if self._path:
            parts.append(f"Path={self._path}")
        if self._expires:
            parts.append(f"Expires={self._expires}")
        if self._max_age is not None:
            parts.append(f"Max-Age={self._max_age}")
        if self._secure:
            parts.append("Secure")
        if self._http_only:
            parts.append("HttpOnly")
        if self._same_site:
            parts.append(f"SameSite={self._same_site}")
        return "; ".join(parts)

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return f"Cookie({self._name}={self._val})"

    def is_empty(self):
        """Check if cookies list is empty (for compatibility)."""
        return False  # Single cookie is never empty

    # Static method for empty list (used by Fantom code)
    @staticmethod
    def empty_list():
        """Return an empty cookie list."""
        from fan.sys.List import List
        return List.from_literal([], 'web::Cookie')
