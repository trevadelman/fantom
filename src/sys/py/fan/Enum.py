#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Enum(Obj):
    """
    Base class for all Fantom enum types.
    """

    def __init__(self, ordinal=0, name=""):
        self._ordinal = ordinal
        self._name = name

    def ordinal(self):
        """Return ordinal value"""
        return self._ordinal

    def name(self):
        """Return enum name"""
        return self._name

    def to_str(self):
        """Return string representation (the name)"""
        return self._name

    def __str__(self):
        return self._name

    def equals(self, other):
        """Enums are singletons - use identity comparison"""
        return self is other

    def compare(self, other):
        """Compare by ordinal"""
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
        if not isinstance(other, Enum):
            return False
        return self._ordinal == other._ordinal

    def __hash__(self):
        return hash(self._ordinal)

    def is_immutable(self):
        """Enums are always immutable in Fantom"""
        return True

    def typeof(self):
        """Return the Fantom type for this enum"""
        from .Type import Type
        # Get the actual class type
        cls = self.__class__
        module = cls.__module__
        if module.startswith('fan.'):
            parts = module.split('.')
            if len(parts) >= 3:
                pod = parts[1]
                return Type.find(f"{pod}::{cls.__name__}")
        return Type.find(f"sys::{cls.__name__}")
