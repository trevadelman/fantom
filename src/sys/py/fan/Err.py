#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Err(Exception, Obj):
    """Base error class"""

    def __init__(self, msg=None, cause=None):
        Exception.__init__(self, msg)
        Obj.__init__(self)
        self._msg = msg
        self._cause = cause

    @classmethod
    def make(cls, msg=None, cause=None):
        """Factory method - creates instance of the calling class"""
        return cls(msg, cause)

    def msg(self):
        # Fantom returns empty string when no message provided, not null
        return self._msg if self._msg is not None else ""

    def cause(self):
        return self._cause

    def to_str(self):
        # Use Fantom qname format
        qname = self.typeof().qname()
        if self._msg:
            return f"{qname}: {self._msg}"
        return qname

    def trace(self, out=None, options=None):
        """Print stack trace to output stream (default: Env.cur.out)"""
        from .ObjUtil import ObjUtil
        trace_str = self.trace_to_str()
        if out is None:
            ObjUtil.echo(trace_str)
        else:
            # out is an OutStream - use writeChars or print
            if hasattr(out, 'print_line'):
                out.print_line(trace_str)
            elif hasattr(out, 'write_chars'):
                out.write_chars(trace_str + "\n")
            elif hasattr(out, 'print'):
                out.print(trace_str + "\n")
            else:
                out.write(trace_str.encode('utf-8') + b'\n')
        return self

    def trace_to_str(self):
        """Return stack trace as string"""
        import traceback
        import sys

        # Build trace string
        s = self.to_str()

        # Add Python stack trace
        tb = getattr(self, '__traceback__', None)
        if tb:
            lines = traceback.format_tb(tb)
            s += "\n" + "".join(lines)

        # Add cause if present
        if self._cause:
            if hasattr(self._cause, 'trace_to_str'):
                s += "\n  Caused by: " + self._cause.trace_to_str()
            else:
                s += f"\n  Caused by: {self._cause}"

        return s

    def is_immutable(self):
        """Err objects are always immutable"""
        return True

    def to_immutable(self):
        """Err objects are already immutable, return self"""
        return self

    def compare(self, that):
        """Compare by message for consistent ordering"""
        if that is None:
            return 1
        return -1 if self._msg < that._msg else (1 if self._msg > that._msg else 0)

    def __str__(self):
        return self.to_str()


class ParseErr(Err):
    """Parse error"""

    @staticmethod
    def make_str(type_name, s):
        return ParseErr(f"Invalid {type_name}: '{s}'")


class NullErr(Err):
    """Null error - thrown when null is accessed"""
    pass


class CastErr(Err):
    """Cast error - thrown when type cast fails"""
    pass


class ArgErr(Err):
    """Argument error"""
    pass


class IndexErr(Err):
    """Index out of bounds error"""
    pass


class UnsupportedErr(Err):
    """Unsupported operation error"""
    pass


class UnknownTypeErr(Err):
    """Unknown type error"""
    pass


class UnknownPodErr(Err):
    """Unknown pod error"""
    pass


class UnknownSlotErr(Err):
    """Unknown slot error - thrown when slot lookup fails"""
    pass


class UnknownFacetErr(Err):
    """Unknown facet error - thrown when facet lookup fails"""
    pass


class UnresolvedErr(Err):
    """Unresolved error - thrown when resource cannot be found"""
    pass


class UnknownServiceErr(Err):
    """Unknown service error - thrown when service lookup fails"""
    pass


class ReadonlyErr(Err):
    """Modification of read-only data error"""
    pass


class IOErr(Err):
    """I/O error"""

    @staticmethod
    def make(msg=None, cause=None):
        return IOErr(msg, cause)

    def is_immutable(self):
        return True


class NotImmutableErr(Err):
    """Not immutable error"""

    @staticmethod
    def make(msg=None, cause=None):
        return NotImmutableErr(msg, cause)


class CancelledErr(Err):
    """Cancelled operation error"""
    pass


class ConstErr(Err):
    """Const field modification error"""
    pass


class InterruptedErr(Err):
    """Thread interrupted error"""
    pass


class NameErr(Err):
    """Invalid name error"""
    pass


class TimeoutErr(Err):
    """Timeout error"""
    pass


class QueueOverflowErr(Err):
    """Queue overflow error - thrown when actor queue is full"""
    pass


class NotCompleteErr(Err):
    """Not complete error - thrown when Future is still pending"""
    pass


class TestErr(Err):
    """Test error - thrown in test assertions"""
    pass


class ReturnErr(Err):
    """Return error - used for control flow in Axon"""

    def __init__(self, msg=None, cause=None, val=None):
        super().__init__(msg, cause)
        self._val = val

    @staticmethod
    def make_val(val):
        err = ReturnErr(None, None, val)
        return err

    def val(self):
        return self._val


class NotFilterErr(Err):
    """Not filter error - thrown when filter parse fails"""
    pass


class UnknownNameErr(Err):
    """Unknown name error"""
    pass


class UnknownKeyErr(Err):
    """Unknown key error (key not found in map/dict)"""
    pass
