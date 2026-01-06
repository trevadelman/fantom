#
# Charset - Character encoding for Fantom
#
from fan.sys.Obj import Obj


class Charset(Obj):
    """
    Charset represents a character encoding/decoding scheme.
    """

    # Cache of charset instances
    _cache = {}
    _utf8 = None
    _utf16BE = None
    _utf16LE = None
    _iso8859_1 = None

    def __init__(self, name):
        """Create a Charset with the given name"""
        self._name = name

    @staticmethod
    def make():
        """Default constructor returns UTF-8"""
        return Charset.utf8()

    @staticmethod
    def defVal():
        """Default value is UTF-8"""
        return Charset.utf8()

    @staticmethod
    def fromStr(name, checked=True):
        """
        Get a Charset by name (Fantom API).
        Returns cached instances for known charsets.
        Throws ParseErr for unknown charsets when checked=True.
        Returns None for unknown charsets when checked=False.
        """
        if name is None:
            if checked:
                from fan.sys.ParseErr import ParseErr
                raise ParseErr.make("Unsupported charset 'null'")
            return None

        nname = name.upper()

        # Map of supported charsets
        try:
            if nname == "UTF-8":
                return Charset.utf8()
            elif nname == "UTF-16BE":
                return Charset.utf16BE()
            elif nname == "UTF-16LE":
                return Charset.utf16LE()
            elif nname == "ISO-8859-1":
                return Charset.iso8859_1()
            elif nname == "ISO-8859-2":
                return Charset._getOrCreate("ISO-8859-2")
            elif nname == "ISO-8859-5":
                return Charset._getOrCreate("ISO-8859-5")
            elif nname == "ISO-8859-8":
                return Charset._getOrCreate("ISO-8859-8")
            else:
                # Unknown charset
                raise ValueError(f"Unsupported charset: {nname}")
        except (ValueError, KeyError):
            if not checked:
                return None
            from fan.sys.ParseErr import ParseErr
            raise ParseErr.make(f"Unsupported charset '{nname}'")

    @staticmethod
    def _getOrCreate(name):
        """Get or create a cached Charset instance by normalized name."""
        if name in Charset._cache:
            return Charset._cache[name]
        cs = Charset(name)
        Charset._cache[name] = cs
        return cs

    @staticmethod
    def forName(name):
        """
        Get a Charset by name (legacy method, use fromStr for Fantom API).
        This method is more lenient - allows creating charsets for any name.
        """
        if name is None:
            return None
        name_lower = name.lower().replace('_', '-')

        # Normalize common names to canonical form
        name_map = {
            "utf-8": "UTF-8",
            "utf8": "UTF-8",
            "utf-16be": "UTF-16BE",
            "utf-16le": "UTF-16LE",
            "utf-16": "UTF-16",
            "us-ascii": "US-ASCII",
            "ascii": "US-ASCII",
            "iso-8859-1": "ISO-8859-1",
            "iso-8859-2": "ISO-8859-2",
            "iso-8859-5": "ISO-8859-5",
            "iso-8859-8": "ISO-8859-8",
            "latin1": "ISO-8859-1",
        }

        normalized = name_map.get(name_lower, name)
        return Charset._getOrCreate(normalized)

    @staticmethod
    def utf8():
        """Get UTF-8 charset (cached singleton)"""
        if Charset._utf8 is None:
            Charset._utf8 = Charset("UTF-8")
            Charset._cache["UTF-8"] = Charset._utf8
        return Charset._utf8

    @staticmethod
    def utf16BE():
        """Get UTF-16BE charset (cached singleton)"""
        if Charset._utf16BE is None:
            Charset._utf16BE = Charset("UTF-16BE")
            Charset._cache["UTF-16BE"] = Charset._utf16BE
        return Charset._utf16BE

    @staticmethod
    def utf16LE():
        """Get UTF-16LE charset (cached singleton)"""
        if Charset._utf16LE is None:
            Charset._utf16LE = Charset("UTF-16LE")
            Charset._cache["UTF-16LE"] = Charset._utf16LE
        return Charset._utf16LE

    @staticmethod
    def iso8859_1():
        """Get ISO-8859-1 charset (cached singleton)"""
        if Charset._iso8859_1 is None:
            Charset._iso8859_1 = Charset("ISO-8859-1")
            Charset._cache["ISO-8859-1"] = Charset._iso8859_1
        return Charset._iso8859_1

    def name(self):
        """Get the charset name"""
        return self._name

    def toStr(self):
        """String representation"""
        return self._name

    def __str__(self):
        return self.toStr()

    def equals(self, other):
        """Test equality"""
        if other is None:
            return False
        if not isinstance(other, Charset):
            return False
        return self._name == other._name

    def __eq__(self, other):
        return self.equals(other)

    def hash_(self):
        """Hash code"""
        return hash(self._name)

    def __hash__(self):
        return self.hash_()

    def typeof(self):
        """Return Type for Charset"""
        from fan.sys.Type import Type
        return Type.find("sys::Charset")

    def literalEncode(self, encoder):
        """Encode for serialization.

        Simple types serialize as: Type("toStr")
        Example: sys::Charset("UTF-8")
        """
        encoder.wType(self.typeof())
        encoder.w('(')
        encoder.wStrLiteral(self.toStr(), '"')
        encoder.w(')')
