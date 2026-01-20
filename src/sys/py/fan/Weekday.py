#
# Weekday - Day of week enum for Fantom
#
from fan.sys.Enum import Enum

class Weekday(Enum):
    """
    Weekday represents a day of the week (enum).
    """

    _vals = None
    _byName = None
    _localeValsCache = {}  # Cache per locale start day

    def __init__(self, ordinal, name):
        super().__init__(ordinal, name)

    @staticmethod
    def sun():
        return Weekday.vals().get(0)

    @staticmethod
    def mon():
        return Weekday.vals().get(1)

    @staticmethod
    def tue():
        return Weekday.vals().get(2)

    @staticmethod
    def wed():
        return Weekday.vals().get(3)

    @staticmethod
    def thu():
        return Weekday.vals().get(4)

    @staticmethod
    def fri():
        return Weekday.vals().get(5)

    @staticmethod
    def sat():
        return Weekday.vals().get(6)

    @staticmethod
    def _make_enum(ordinal, name):
        inst = object.__new__(Weekday)
        inst._ordinal = ordinal
        inst._name = name
        return inst

    @staticmethod
    def vals():
        """Get all weekday values"""
        from fan.sys.List import List
        if Weekday._vals is None:
            Weekday._vals = List.to_immutable(List.from_list([
                Weekday._make_enum(0, "sun"),
                Weekday._make_enum(1, "mon"),
                Weekday._make_enum(2, "tue"),
                Weekday._make_enum(3, "wed"),
                Weekday._make_enum(4, "thu"),
                Weekday._make_enum(5, "fri"),
                Weekday._make_enum(6, "sat")
            ]))
        return Weekday._vals

    @staticmethod
    def _get(ordinal):
        """Get weekday by ordinal"""
        return Weekday.vals().get(ordinal)

    @staticmethod
    def locale_start_of_week():
        """Get locale-specific start of week (Sunday in US, Monday in Europe)"""
        from .Locale import Locale
        cur = Locale.cur()
        # US and Canada use Sunday as start of week
        # Most other locales use Monday
        lang = cur.lang()
        country = cur.country()
        # US (en-US) and Canada (en-CA) start on Sunday
        if country in ['US', 'CA']:
            return Weekday.sun()
        # Default for most locales is Monday (ISO 8601 standard)
        return Weekday.mon()

    @staticmethod
    def locale_vals():
        """Get weekdays in locale-specific order starting from localeStartOfWeek"""
        from fan.sys.List import List
        start = Weekday.locale_start_of_week().ordinal()
        # Cache per start day for identity (verifySame requirement)
        if start not in Weekday._localeValsCache:
            result = []
            for i in range(7):
                result.append(Weekday.vals().get((start + i) % 7))
            Weekday._localeValsCache[start] = List.to_immutable(List.from_list(result))
        return Weekday._localeValsCache[start]

    @staticmethod
    def from_str(s, checked=True):
        """Parse Weekday from string"""
        if Weekday._byName is None:
            Weekday._byName = {
                "sun": 0, "sunday": 0,
                "mon": 1, "monday": 1,
                "tue": 2, "tuesday": 2,
                "wed": 3, "wednesday": 3,
                "thu": 4, "thursday": 4,
                "fri": 5, "friday": 5,
                "sat": 6, "saturday": 6,
            }
        s_lower = s.lower()
        if s_lower in Weekday._byName:
            return Weekday.vals().get(Weekday._byName[s_lower])
        if checked:
            from fan.sys.Err import ParseErr
            raise ParseErr.make(f"Unknown weekday: {s}")
        return None

    def name(self):
        """Get weekday name"""
        return self._name

    def ordinal(self):
        """Get ordinal (0=Sunday, 6=Saturday in Fantom)"""
        return self._ordinal

    def increment(self, days=1):
        """Return weekday + days"""
        new_ord = (self._ordinal + days) % 7
        return Weekday.vals().get(new_ord)

    def decrement(self, days=1):
        """Return weekday - days"""
        new_ord = (self._ordinal - days) % 7
        return Weekday.vals().get(new_ord)

    def locale_abbr(self):
        """Abbreviated locale name"""
        return self._name[:3].title()

    def locale_full(self):
        """Full locale name"""
        names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        return names[self._ordinal]

    def to_locale(self, pattern=None, locale=None):
        """Format weekday for locale.

        Matches JS: pattern must be all 'W' chars, length 3 or 4.
        - null -> abbreviated
        - WWW -> abbreviated
        - WWWW -> full
        - anything else -> ArgErr
        """
        from .Locale import Locale
        if locale is None:
            locale = Locale.cur()
        if pattern is None:
            return self.__abbr(locale)
        # Pattern must be all 'W' characters with length 3 or 4
        if pattern and all(c == 'W' for c in pattern):
            if len(pattern) == 3:
                return self.__abbr(locale)
            elif len(pattern) == 4:
                return self.__full(locale)
        from fan.sys.Err import ArgErr
        raise ArgErr.make(f"Invalid pattern: {pattern}")

    def __abbr(self, locale):
        """Get locale-aware abbreviated name"""
        abbr_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        return abbr_names[self._ordinal]

    def __full(self, locale):
        """Get locale-aware full name"""
        full_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        return full_names[self._ordinal]

    def to_str(self):
        return self._name

    def __str__(self):
        return self._name

    def equals(self, other):
        if not isinstance(other, Weekday):
            return False
        return self._ordinal == other._ordinal

    def compare(self, other):
        return self._ordinal - other._ordinal

    def __lt__(self, other):
        return self._ordinal < other._ordinal

    def __le__(self, other):
        return self._ordinal <= other._ordinal

    def __gt__(self, other):
        return self._ordinal > other._ordinal

    def __ge__(self, other):
        return self._ordinal >= other._ordinal

    def __eq__(self, other):
        if not isinstance(other, Weekday):
            return False
        return self._ordinal == other._ordinal

    def __hash__(self):
        return hash(self._ordinal)

    def hash_(self):
        return self._ordinal

    def is_immutable(self):
        """Enums are always immutable in Fantom"""
        return True

    def __add__(self, val):
        """Weekday + Int -> Weekday"""
        return self.increment(val)

    def __sub__(self, val):
        """Weekday - Int -> Weekday"""
        return self.decrement(val)
