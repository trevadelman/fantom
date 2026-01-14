#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#
# Native Locale implementation for Python runtime
#

import re
import threading
from fan.sys.Obj import Obj


class Locale(Obj):
    """
    Locale models a cultural language and region/country.
    Format: "lang" or "lang-COUNTRY" where lang is lowercase 2 letters and COUNTRY is uppercase 2 letters.
    """

    # Thread-local storage for current locale - each thread gets its own
    _thread_local = threading.local()
    _cache = {}  # Cache for parsed locales (shared, but locales are immutable)
    _en = None   # Cached English locale

    def __init__(self, str_val, lang, country):
        """Initialize Locale with string, language and country.

        Args:
            str_val: Full locale string (e.g., "en-US", "de")
            lang: Language code (e.g., "en", "de")
            country: Country code or None (e.g., "US", None)
        """
        self._str = str_val
        self._lang = lang
        self._country = country

        # Pre-computed Uri objects for props lookup
        from .Uri import Uri
        self.__strProps = Uri.from_str(f"locale/{str_val}.props")
        self.__langProps = Uri.from_str(f"locale/{lang}.props")

        # Cached lookups (populated on first use)
        self._monthsByName = None
        self._numSymbols = None

    @staticmethod
    def from_str(s, checked=True):
        """Parse a Locale from string like 'en' or 'en-US'.

        Format: "xx" or "xx-XX" where:
        - Language is exactly 2 lowercase letters
        - Country is exactly 2 uppercase letters
        """
        if s in Locale._cache:
            return Locale._cache[s]

        try:
            if not s or not s.strip():
                raise ValueError("Empty locale")

            s = s.strip()

            # Validate format
            if '-' in s:
                # Format: lang-COUNTRY
                parts = s.split('-', 1)
                lang = parts[0]
                country = parts[1]

                # Validate language: exactly 2 lowercase letters
                if not re.match(r'^[a-z]{2}$', lang):
                    raise ValueError(f"Invalid language code: {lang}")

                # Validate country: exactly 2 uppercase letters
                if not re.match(r'^[A-Z]{2}$', country):
                    raise ValueError(f"Invalid country code: {country}")
            else:
                # Format: lang only
                # Must be exactly 2 lowercase letters
                if not re.match(r'^[a-z]{2}$', s):
                    raise ValueError(f"Invalid language code: {s}")

            # Create locale with parsed components
            if '-' in s:
                locale = Locale(s, lang, country)
            else:
                locale = Locale(s, s, None)
            Locale._cache[s] = locale
            return locale

        except Exception as e:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid locale: {s}")
            return None

    def __month_by_name(self, name):
        """Get Month by localized name (abbr or full).

        Matches JS implementation - builds cache on first use.
        """
        if self._monthsByName is None:
            from .Month import Month
            from .Str import Str
            name_map = {}
            vals = Month.vals()
            # Handle both hand-written and generated Month classes
            size = vals.size() if callable(getattr(vals, 'size', None)) else len(vals)
            for i in range(size):
                m = vals.get(i) if hasattr(vals, 'get') else vals[i]
                name_map[Str.lower(m._Month__abbr(self))] = m
                name_map[Str.lower(m._Month__full(self))] = m
            self._monthsByName = name_map
        return self._monthsByName.get(name)

    def __num_symbols(self):
        """Get number formatting symbols for this locale.

        Returns dict with decimal, grouping, etc.
        """
        if self._numSymbols is None:
            from .Pod import Pod
            from .Env import Env
            pod = Pod.find("sys")
            env = Env.cur()
            self._numSymbols = {
                'decimal': env.locale(pod, "numDecimal", ".", self),
                'grouping': env.locale(pod, "numGrouping", ",", self),
                'minus': env.locale(pod, "numMinus", "-", self),
                'percent': env.locale(pod, "numPercent", "%", self),
                'posInf': env.locale(pod, "numPosInf", "+Inf", self),
                'negInf': env.locale(pod, "numNegInf", "-Inf", self),
                'nan': env.locale(pod, "numNaN", "NaN", self),
            }
        return self._numSymbols

    @staticmethod
    def en():
        """Get English locale singleton"""
        if Locale._en is None:
            Locale._en = Locale.from_str("en")
        return Locale._en

    @staticmethod
    def cur():
        """Get current locale for this thread"""
        if not hasattr(Locale._thread_local, 'current') or Locale._thread_local.current is None:
            Locale._thread_local.current = Locale.from_str("en-US")
        return Locale._thread_local.current

    @staticmethod
    def set_cur(locale):
        """Set current locale for this thread"""
        if locale is None:
            from fan.sys.Err import NullErr
            raise NullErr("Locale cannot be null")
        Locale._thread_local.current = locale

    def lang(self):
        """Get language code (lowercase 2 letters)"""
        return self._lang

    def country(self):
        """Get country code (uppercase 2 letters) or null"""
        return self._country

    def use(self, func):
        """Execute function with this locale as current, restoring afterwards.

        The function receives the locale as its argument (|This| closure).
        If the function throws, the original locale is still restored.
        Returns the function's result.
        """
        old = Locale.cur()  # Get current for this thread
        Locale.set_cur(self)
        try:
            # Fantom's use expects |This| closure, so pass self as argument
            result = func(self)
            return result
        finally:
            Locale.set_cur(old)

    def to_str(self):
        """String representation"""
        return self._str

    def __str__(self):
        return self._str

    def equals(self, other):
        """Test equality"""
        if not isinstance(other, Locale):
            return False
        return self._str == other._str

    def hash_(self):
        """Hash code - uses string's hash"""
        return hash(self._str)

    @property
    def hash(self):
        """Hash property for Fantom compatibility - delegates to string hash"""
        return self._str.__hash__()

    def __hash__(self):
        """Python hash"""
        return hash(self._str)

    def __eq__(self, other):
        """Python equality"""
        if not isinstance(other, Locale):
            return False
        return self._str == other._str

    def typeof(self):
        """Return the Fantom type of this object."""
        from fan.sys.Type import Type
        return Type.find("sys::Locale")

    def literal_encode(self, encoder):
        """Encode for serialization.

        Simple types serialize as: Type("toStr")
        Example: sys::Locale("en-US")
        """
        encoder.w_type(self.typeof())
        encoder.w('(')
        encoder.w_str_literal(self.to_str(), '"')
        encoder.w(')')
