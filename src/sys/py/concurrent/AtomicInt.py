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

    def _getVal(self):
        """Get the value atomically (callable version)."""
        with self._lock:
            return self.__val

    def getAndSet(self, val):
        """Atomically set to the given value and return the old value."""
        with self._lock:
            old = self.__val
            self.__val = val
            return old

    def compareAndSet(self, expect, update):
        """Atomically set to update if current value equals expect."""
        with self._lock:
            if self.__val == expect:
                self.__val = update
                return True
            return False

    def getAndIncrement(self):
        """Atomically increment and return the old value."""
        with self._lock:
            old = self.__val
            self.__val += 1
            return old

    def getAndDecrement(self):
        """Atomically decrement and return the old value."""
        with self._lock:
            old = self.__val
            self.__val -= 1
            return old

    def getAndAdd(self, delta):
        """Atomically add delta and return the old value."""
        with self._lock:
            old = self.__val
            self.__val += delta
            return old

    def incrementAndGet(self):
        """Atomically increment and return the new value."""
        with self._lock:
            self.__val += 1
            return self.__val

    def decrementAndGet(self):
        """Atomically decrement and return the new value."""
        with self._lock:
            self.__val -= 1
            return self.__val

    def addAndGet(self, delta):
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

    def toStr(self):
        return Int.toStr(self._getVal())

    def __str__(self):
        return self.toStr()


# Type metadata registration for reflection
from fan.sys.Type import Type
from fan.sys.Param import Param

_t = Type.find('concurrent::AtomicInt')
_t.tf_({'sys::Js': {}})
_t.af_('val', 1, 'sys::Int', {})
_t.am_('make', 257, 'sys::Void', [Param('val', Type.find('sys::Int'), True)], {})
_t.am_('getAndSet', 1, 'sys::Int', [Param('val', Type.find('sys::Int'), False)], {})
_t.am_('compareAndSet', 1, 'sys::Bool', [Param('expect', Type.find('sys::Int'), False), Param('update', Type.find('sys::Int'), False)], {})
_t.am_('getAndIncrement', 1, 'sys::Int', [], {})
_t.am_('getAndDecrement', 1, 'sys::Int', [], {})
_t.am_('getAndAdd', 1, 'sys::Int', [Param('delta', Type.find('sys::Int'), False)], {})
_t.am_('incrementAndGet', 1, 'sys::Int', [], {})
_t.am_('decrementAndGet', 1, 'sys::Int', [], {})
_t.am_('addAndGet', 1, 'sys::Int', [Param('delta', Type.find('sys::Int'), False)], {})
_t.am_('increment', 1, 'sys::Void', [], {})
_t.am_('decrement', 1, 'sys::Void', [], {})
_t.am_('add', 1, 'sys::Void', [Param('delta', Type.find('sys::Int'), False)], {})
_t.am_('toStr', 4609, 'sys::Str', [], {})
