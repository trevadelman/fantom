#
# concurrent::AtomicInt
# Hand-written runtime implementation for atomic integer operations
#

import threading
from fan.sys.Obj import Obj
from fan.sys.Int import Int


class AtomicInt(Obj):
    """AtomicInt provides atomic operations on an integer value."""

    def __init__(self, val=0):
        super().__init__()
        self._lock = threading.Lock()
        self.__val = val if val is not None else 0

    @staticmethod
    def make(val=0):
        return AtomicInt(val if val is not None else 0)

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

    def get_and_increment(self):
        """Atomically increment and return the old value."""
        with self._lock:
            old = self.__val
            self.__val += 1
            return old

    def get_and_decrement(self):
        """Atomically decrement and return the old value."""
        with self._lock:
            old = self.__val
            self.__val -= 1
            return old

    def get_and_add(self, delta):
        """Atomically add delta and return the old value."""
        with self._lock:
            old = self.__val
            self.__val += delta
            return old

    def increment_and_get(self):
        """Atomically increment and return the new value."""
        with self._lock:
            self.__val += 1
            return self.__val

    def decrement_and_get(self):
        """Atomically decrement and return the new value."""
        with self._lock:
            self.__val -= 1
            return self.__val

    def add_and_get(self, delta):
        """Atomically add delta and return the new value."""
        with self._lock:
            self.__val += delta
            return self.__val

    def increment(self):
        """Atomically increment (void return)."""
        with self._lock:
            self.__val += 1

    def decrement(self):
        """Atomically decrement (void return)."""
        with self._lock:
            self.__val -= 1

    def add(self, delta):
        """Atomically add delta (void return)."""
        with self._lock:
            self.__val += delta

    def to_str(self):
        return Int.to_str(self._get_val())

    def __str__(self):
        return self.to_str()


# Type metadata registration for reflection
from fan.sys.Type import Type
from fan.sys.Param import Param

_t = Type.find('concurrent::AtomicInt')
_t.tf_({'sys::Js': {}})
_t.af_('val', 1, 'sys::Int', {})
_t.am_('make', 257, 'sys::Void', [Param('val', Type.find('sys::Int'), True)], {})
_t.am_('get_and_set', 1, 'sys::Int', [Param('val', Type.find('sys::Int'), False)], {})
_t.am_('compare_and_set', 1, 'sys::Bool', [Param('expect', Type.find('sys::Int'), False), Param('update', Type.find('sys::Int'), False)], {})
_t.am_('get_and_increment', 1, 'sys::Int', [], {})
_t.am_('get_and_decrement', 1, 'sys::Int', [], {})
_t.am_('get_and_add', 1, 'sys::Int', [Param('delta', Type.find('sys::Int'), False)], {})
_t.am_('increment_and_get', 1, 'sys::Int', [], {})
_t.am_('decrement_and_get', 1, 'sys::Int', [], {})
_t.am_('add_and_get', 1, 'sys::Int', [Param('delta', Type.find('sys::Int'), False)], {})
_t.am_('increment', 1, 'sys::Void', [], {})
_t.am_('decrement', 1, 'sys::Void', [], {})
_t.am_('add', 1, 'sys::Void', [Param('delta', Type.find('sys::Int'), False)], {})
_t.am_('to_str', 4609, 'sys::Str', [], {})
