#
# concurrent::AtomicBool
# Hand-written runtime implementation for atomic boolean operations
#

import threading
from fan.sys.Obj import Obj
from fan.sys import Bool


class AtomicBool(Obj):
    """AtomicBool provides atomic operations on a boolean value."""

    def __init__(self, val=False):
        super().__init__()
        self._lock = threading.Lock()
        self.__val = val if val is not None else False

    @staticmethod
    def make(val=False):
        return AtomicBool(val if val is not None else False)

    def val(self, new_val=None):
        """Fantom-style getter/setter: obj.val() to get, obj.val(x) to set."""
        if new_val is None:
            with self._lock:
                return self.__val
        else:
            with self._lock:
                self.__val = new_val

    def _get_val(self):
        """Get the value atomically (callable version)."""
        with self._lock:
            return self.__val

    def get_and_set(self, val):
        """Atomically set to the given value and return the old value."""
        with self._lock:
            old = self.__val
            self.__val = val
            return old

    def compare_and_set(self, expect, update):
        """Atomically set to update if current value equals expect."""
        with self._lock:
            if self.__val == expect:
                self.__val = update
                return True
            return False

    def to_str(self):
        return Bool.to_str(self._get_val())

    def __str__(self):
        return self.to_str()


# Type metadata registration for reflection
from fan.sys.Type import Type
from fan.sys.Param import Param

_t = Type.find('concurrent::AtomicBool')
_t.tf_({'sys::Js': {}})
_t.af_('val', 1, 'sys::Bool', {})
_t.am_('make', 257, 'sys::Void', [Param('val', Type.find('sys::Bool'), True)], {})
_t.am_('get_and_set', 1, 'sys::Bool', [Param('val', Type.find('sys::Bool'), False)], {})
_t.am_('compare_and_set', 1, 'sys::Bool', [Param('expect', Type.find('sys::Bool'), False), Param('update', Type.find('sys::Bool'), False)], {})
_t.am_('to_str', 4609, 'sys::Str', [], {})
