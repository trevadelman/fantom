#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#


from .Obj import Obj


class Unsafe(Obj):
    """Wrapper for reassignable local variables captured by closures.

    Python closures capture variables by value, so reassignments after
    closure creation aren't visible to the closure. This wrapper solves
    that by providing mutable reference semantics.

    Also used to wrap mutable objects for immutable contexts.

    Usage:
        strs = Unsafe(initial_value)   # or make(initial_value)
        strs._val = new_value          # Reassign
        use_value(strs.val())          # Access current value
    """

    def __init__(self, val=None):
        self._val = val

    @staticmethod
    def make(val=None):
        """Factory method for creating Unsafe wrapper (called by transpiled code)."""
        return Unsafe(val)

    def val(self):
        """Get current value"""
        return self._val

    def is_immutable(self):
        """Unsafe wrapper is always immutable"""
        return True

    def to_str(self):
        return f"Unsafe({self._val})"


def make(initial_value=None):
    """Create an Unsafe wrapper for a reassignable variable.

    This is a convenience function that creates an Unsafe wrapper.
    """
    return Unsafe(initial_value)
