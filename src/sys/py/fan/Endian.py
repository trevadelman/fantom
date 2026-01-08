#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Endian(Obj):
    """Endian represents byte order (big or little endian)."""

    _big = None
    _little = None

    def __init__(self, name):
        self._name = name

    @staticmethod
    def big():
        """Big endian byte order."""
        if Endian._big is None:
            Endian._big = Endian("big")
        return Endian._big

    @staticmethod
    def little():
        """Little endian byte order."""
        if Endian._little is None:
            Endian._little = Endian("little")
        return Endian._little

    @staticmethod
    def from_str(s, checked=True):
        """Get Endian from string."""
        s = str(s).lower()
        if s == "big":
            return Endian.big()
        if s == "little":
            return Endian.little()
        if checked:
            from .Err import ParseErr
            raise ParseErr.make(f"Invalid Endian: {s}")
        return None

    @staticmethod
    def vals():
        """Return list of all Endian values."""
        from .List import List
        return List.from_literal([Endian.big(), Endian.little()], "sys::Endian")

    @property
    def name(self):
        return self._name

    def to_str(self):
        return self._name

    def __str__(self):
        return self._name

    def typeof(self):
        from .Type import Type
        return Type.find("sys::Endian")

    def equals(self, other):
        if not isinstance(other, Endian):
            return False
        return self._name == other._name

    def hash_(self):
        return hash(self._name)
