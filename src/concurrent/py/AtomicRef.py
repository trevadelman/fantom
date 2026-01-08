#
# concurrent::AtomicRef
# Hand-written runtime implementation for atomic reference operations
#

import threading
from fan.sys.Obj import Obj
from fan.sys.ObjUtil import ObjUtil


class AtomicRef(Obj):
    """AtomicRef provides atomic operations on an object reference.

    Values must be immutable. Attempting to store a mutable object
    will throw NotImmutableErr.
    """

    # Sentinel to distinguish getter call from setter call with null value
    _UNSET = object()

    def __init__(self, val=None):
        super().__init__()
        self._lock = threading.Lock()
        # Check immutability if val provided
        if val is not None:
            self._check_immutable(val)
        self.__val = val

    @staticmethod
    def make(val=None):
        return AtomicRef(val)

    def _check_immutable(self, val):
        """Check if value is immutable, throw NotImmutableErr if not.

        This matches the JavaScript ES6 implementation which enforces
        immutability on all AtomicRef values.
        """
        if val is not None and not ObjUtil.is_immutable(val):
            from fan.sys.Err import NotImmutableErr
            raise NotImmutableErr.make("AtomicRef value is not immutable")

    def val(self, new_val=_UNSET):
        """Fantom-style getter/setter: obj.val() to get, obj.val(x) to set.

        Uses sentinel _UNSET to distinguish getter call from setter with null.
        """
        if new_val is AtomicRef._UNSET:
            # Getter
            with self._lock:
                return self.__val
        else:
            # Setter (new_val can be None)
            self._check_immutable(new_val)
            with self._lock:
                self.__val = new_val

    def _get_val(self):
        """Get the value atomically (callable version)."""
        with self._lock:
            return self.__val

    def get_and_set(self, val):
        """Atomically set to the given value and return the old value."""
        self._check_immutable(val)
        with self._lock:
            old = self.__val
            self.__val = val
            return old

    def compare_and_set(self, expect, update):
        """Atomically set to update if current value equals expect."""
        self._check_immutable(update)
        with self._lock:
            # Use identity comparison for objects
            if self.__val is expect or self.__val == expect:
                self.__val = update
                return True
            return False

    def to_str(self):
        val = self._get_val()
        if val is None:
            return "null"
        return ObjUtil.to_str(val)

    def __str__(self):
        return self.to_str()


# Type metadata registration for reflection
from fan.sys.Type import Type
from fan.sys.Param import Param

_t = Type.find('concurrent::AtomicRef')
_t.tf_({'sys::Js': {}})
_t.af_('val', 1, 'sys::Obj?', {})
_t.am_('make', 257, 'sys::Void', [Param('val', Type.find('sys::Obj?'), True)], {})
_t.am_('get_and_set', 1, 'sys::Obj?', [Param('val', Type.find('sys::Obj?'), False)], {})
_t.am_('compare_and_set', 1, 'sys::Bool', [Param('expect', Type.find('sys::Obj?'), False), Param('update', Type.find('sys::Obj?'), False)], {})
_t.am_('to_str', 4609, 'sys::Str', [], {})
