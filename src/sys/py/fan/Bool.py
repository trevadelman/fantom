#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Bool(Obj):
    """Boolean type - uses static methods on native bool"""

    @staticmethod
    def def_val():
        return False

    @staticmethod
    def is_immutable(self):
        return True

    @staticmethod
    def typeof(self):
        return "sys::Bool"

    @staticmethod
    def hash(self):
        return 1231 if self else 1237

    @staticmethod
    def hash_(self):
        """Alias for hash - transpiler generates hash_"""
        return Bool.hash(self)

    @staticmethod
    def equals(self, other):
        """Equality comparison"""
        if other is None:
            return False
        return self == other

    @staticmethod
    def not_(self):
        return not self

    @staticmethod
    def and_(self, b):
        return self and b

    @staticmethod
    def or_(self, b):
        return self or b

    @staticmethod
    def xor(self, b):
        return self != b

    @staticmethod
    def compare(self, that):
        if that is None:
            return 1
        if self == that:
            return 0
        return 1 if self else -1

    @staticmethod
    def to_str(self):
        return "true" if self else "false"

    @staticmethod
    def to_code(self):
        return "true" if self else "false"

    @staticmethod
    def to_locale(self):
        # Simplified for bootstrap
        return "True" if self else "False"

    @staticmethod
    def from_str(s, checked=True):
        if s == "true":
            return True
        if s == "false":
            return False
        if not checked:
            return None
        from .Err import ParseErr
        raise ParseErr.make_str("Bool", s)
