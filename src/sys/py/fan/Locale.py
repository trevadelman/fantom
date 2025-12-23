#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
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

    def __init__(self, str_val):
        self._str = str_val
        self._lang = None
        self._country = None
        self._parse()

    def _parse(self):
        """Parse locale string into lang and country components"""
        s = self._str
        if '-' in s:
            parts = s.split('-', 1)
            self._lang = parts[0]
            self._country = parts[1]
        else:
            self._lang = s
            self._country = None

    @staticmethod
    def fromStr(s, checked=True):
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

            locale = Locale(s)
            Locale._cache[s] = locale
            return locale

        except Exception as e:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid locale: {s}")
            return None

    @staticmethod
    def en():
        """Get English locale singleton"""
        if Locale._en is None:
            Locale._en = Locale.fromStr("en")
        return Locale._en

    @staticmethod
    def cur():
        """Get current locale for this thread"""
        if not hasattr(Locale._thread_local, 'current') or Locale._thread_local.current is None:
            Locale._thread_local.current = Locale.fromStr("en-US")
        return Locale._thread_local.current

    @staticmethod
    def setCur(locale):
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
        Locale.setCur(self)
        try:
            # Fantom's use expects |This| closure, so pass self as argument
            result = func(self)
            return result
        finally:
            Locale.setCur(old)

    def toStr(self):
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
