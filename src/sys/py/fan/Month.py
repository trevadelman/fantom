#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#
# Native Month implementation for Python runtime
# Matches JavaScript Month.js pattern
#

from .Enum import Enum


class Month(Enum):
    """Month enum with locale support.

    Provides localized month names using Env.locale() lookup,
    matching the JavaScript implementation pattern.
    """

    _vals = None
    _initialized = False

    def __init__(self, ordinal, name, quarter):
        """Initialize Month with ordinal, name, and quarter."""
        super().__init__()
        self._ordinal = ordinal
        self._name = name
        self._quarter = quarter
        self._locale_abbr_key = f"{name}Abbr"
        self._locale_full_key = f"{name}Full"

    @staticmethod
    def vals():
        """Get list of all Month values."""
        if Month._vals is None:
            Month._initialize()
        return Month._vals

    @staticmethod
    def _initialize():
        """Initialize month values (called once)."""
        if Month._initialized:
            return
        Month._initialized = True
        from .List import List
        Month._vals = List.from_literal([
            Month._make_month(0, "jan", 1),
            Month._make_month(1, "feb", 1),
            Month._make_month(2, "mar", 1),
            Month._make_month(3, "apr", 2),
            Month._make_month(4, "may", 2),
            Month._make_month(5, "jun", 2),
            Month._make_month(6, "jul", 3),
            Month._make_month(7, "aug", 3),
            Month._make_month(8, "sep", 3),
            Month._make_month(9, "oct", 4),
            Month._make_month(10, "nov", 4),
            Month._make_month(11, "dec", 4)
        ], "sys::Month").to_immutable()

    @staticmethod
    def _make_month(ordinal, name, quarter):
        """Create a Month instance."""
        m = object.__new__(Month)
        m._ordinal = ordinal
        m._name = name
        m._quarter = quarter
        m._locale_abbr_key = f"{name}Abbr"
        m._locale_full_key = f"{name}Full"
        return m

    @staticmethod
    def _get(ordinal):
        """Get Month by ordinal (0-11). Used internally by DateTime."""
        return Month.vals().get(ordinal)

    # Static accessors for each month
    @staticmethod
    def jan(): return Month.vals().get(0)
    @staticmethod
    def feb(): return Month.vals().get(1)
    @staticmethod
    def mar(): return Month.vals().get(2)
    @staticmethod
    def apr(): return Month.vals().get(3)
    @staticmethod
    def may(): return Month.vals().get(4)
    @staticmethod
    def jun(): return Month.vals().get(5)
    @staticmethod
    def jul(): return Month.vals().get(6)
    @staticmethod
    def aug(): return Month.vals().get(7)
    @staticmethod
    def sep(): return Month.vals().get(8)
    @staticmethod
    def oct_(): return Month.vals().get(9)  # Python reserved word
    @staticmethod
    def nov(): return Month.vals().get(10)
    @staticmethod
    def dec(): return Month.vals().get(11)

    @staticmethod
    def from_str(name, checked=True):
        """Parse month from string."""
        from .Err import ParseErr
        for v in Month.vals():
            if v._name == name:
                return v
        if checked:
            raise ParseErr.make(f"Unknown Month: {name}")
        return None

    def ordinal(self):
        """Get ordinal 0-11."""
        return self._ordinal

    def name(self):
        """Get name (jan, feb, etc.)."""
        return self._name

    def to_str(self):
        """Get string representation."""
        return self._name

    def __str__(self):
        return self._name

    def equals(self, other):
        """Check equality."""
        return self is other

    def compare(self, other):
        """Compare to another month."""
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
        if not isinstance(other, Month):
            return False
        return self._ordinal == other._ordinal

    def __hash__(self):
        return hash(self._ordinal)

    def increment(self):
        """Get next month (wraps from Dec to Jan)."""
        return Month.vals().get((self._ordinal + 1) % 12)

    def decrement(self):
        """Get previous month (wraps from Jan to Dec)."""
        return Month.vals().get(11 if self._ordinal == 0 else self._ordinal - 1)

    def __add__(self, val):
        """Month + Int -> Month (with wrapping)."""
        return Month.vals().get((self._ordinal + val) % 12)

    def __sub__(self, val):
        """Month - Int -> Month (with wrapping)."""
        return Month.vals().get((self._ordinal - val) % 12)

    def num_days(self, year):
        """Get number of days in this month for the given year."""
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if self._ordinal == 1:  # February
            # Leap year check
            if (year & 3) == 0 and (year % 100 != 0 or year % 400 == 0):
                return 29
        return days_in_month[self._ordinal]

    def to_locale(self, pattern=None, locale=None):
        """Format month using pattern.

        Pattern:
          M    -> 1-12
          MM   -> 01-12
          MMM  -> Jan-Dec (abbreviated)
          MMMM -> January-December (full)
        """
        from .Locale import Locale
        from .Err import ArgErr

        if locale is None:
            locale = Locale.cur()

        # Default pattern - just abbreviated name
        if pattern is None:
            return self.__abbr(locale)

        # Check if pattern is all 'M' characters
        if pattern and all(c == 'M' for c in pattern):
            length = len(pattern)
            if length == 1:
                return str(self._ordinal + 1)
            elif length == 2:
                return f"0{self._ordinal + 1}" if self._ordinal < 9 else str(self._ordinal + 1)
            elif length == 3:
                return self.__abbr(locale)
            elif length == 4:
                return self.__full(locale)

        raise ArgErr.make(f"Invalid pattern: {pattern}")

    def locale_abbr(self):
        """Get localized abbreviated name using current locale."""
        from .Locale import Locale
        return self.__abbr(Locale.cur())

    def __abbr(self, locale):
        """Get localized abbreviated name for given locale."""
        from .Pod import Pod
        from .Env import Env
        pod = Pod.find("sys")
        return Env.cur().locale(pod, self._locale_abbr_key, self._name, locale)

    def locale_full(self):
        """Get localized full name using current locale."""
        from .Locale import Locale
        return self.__full(Locale.cur())

    def __full(self, locale):
        """Get localized full name for given locale."""
        from .Pod import Pod
        from .Env import Env
        pod = Pod.find("sys")
        return Env.cur().locale(pod, self._locale_full_key, self._name, locale)
