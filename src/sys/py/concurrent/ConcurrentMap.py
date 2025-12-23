#
# concurrent::ConcurrentMap
# Hand-written runtime implementation for thread-safe map
#

import threading
from fan.sys.Obj import Obj


class ConcurrentMap(Obj):
    """Thread-safe map implementation wrapping Python dict with RLock.

    Provides high-performance concurrent access similar to Java's ConcurrentHashMap.
    """

    def __init__(self, initialCapacity=256):
        super().__init__()
        self._lock = threading.RLock()
        self._map = {}

    @staticmethod
    def make(initialCapacity=256):
        return ConcurrentMap(initialCapacity)

    def isEmpty(self):
        """Return if size is zero."""
        with self._lock:
            return len(self._map) == 0

    def size(self):
        """Return size."""
        with self._lock:
            return len(self._map)

    def get(self, key):
        """Get a value by its key or return null."""
        with self._lock:
            return self._map.get(key, None)

    def set(self, key, val):
        """Set a value by key."""
        with self._lock:
            self._map[key] = val

    def getAndSet(self, key, val):
        """Set a value by key and return old value."""
        with self._lock:
            old = self._map.get(key, None)
            self._map[key] = val
            return old

    def add(self, key, val):
        """Add a value by key, raise exception if key was already mapped."""
        with self._lock:
            if key in self._map:
                from fan.sys.Err import Err
                raise Err(f"Key already mapped: {key}")
            self._map[key] = val

    def getOrAdd(self, key, defVal):
        """Get the value for key, or add with defVal if not present."""
        with self._lock:
            if key not in self._map:
                self._map[key] = defVal
            return self._map[key]

    def setAll(self, m):
        """Append the specified map to this map."""
        with self._lock:
            # Handle both Fantom Map and Python dict
            if hasattr(m, '_map'):
                self._map.update(m._map)
            else:
                self._map.update(m)
        return self

    def remove(self, key):
        """Remove a value by key, ignore if key not mapped."""
        with self._lock:
            return self._map.pop(key, None)

    def clear(self):
        """Remove all key/value pairs."""
        with self._lock:
            self._map.clear()

    def each(self, f):
        """Iterate the map's key value pairs."""
        with self._lock:
            items = list(self._map.items())
        for key, val in items:
            f(val, key)

    def eachWhile(self, f):
        """Iterate until function returns non-null."""
        with self._lock:
            items = list(self._map.items())
        for key, val in items:
            result = f(val, key)
            if result is not None:
                return result
        return None

    def containsKey(self, key):
        """Return true if the specified key is mapped."""
        with self._lock:
            return key in self._map

    def keys(self, of=None):
        """Return list of keys."""
        from fan.sys.List import List as FanList
        with self._lock:
            return FanList.fromList(list(self._map.keys()), of)

    def vals(self, of=None):
        """Return list of values."""
        from fan.sys.List import List as FanList
        with self._lock:
            return FanList.fromList(list(self._map.values()), of)

    def __getitem__(self, key):
        """Support bracket syntax: val = map[key]"""
        return self.get(key)

    def __setitem__(self, key, val):
        """Support bracket syntax: map[key] = val"""
        self.set(key, val)

    def toStr(self):
        with self._lock:
            return str(self._map)

    def __str__(self):
        return self.toStr()


# Type metadata registration for reflection
from fan.sys.Type import Type
from fan.sys.Param import Param

_t = Type.find('concurrent::ConcurrentMap')
_t.tf_({'sys::Js': {}})
_t.am_('make', 257, 'concurrent::ConcurrentMap', [Param('initialCapacity', Type.find('sys::Int'), True)], {})
_t.am_('isEmpty', 1, 'sys::Bool', [], {})
_t.am_('size', 1, 'sys::Int', [], {})
_t.am_('get', 1, 'sys::Obj?', [Param('key', Type.find('sys::Obj'), False)], {})
_t.am_('set', 1, 'sys::Void', [Param('key', Type.find('sys::Obj'), False), Param('val', Type.find('sys::Obj'), False)], {})
_t.am_('getAndSet', 1, 'sys::Obj?', [Param('key', Type.find('sys::Obj'), False), Param('val', Type.find('sys::Obj'), False)], {})
_t.am_('add', 1, 'sys::Void', [Param('key', Type.find('sys::Obj'), False), Param('val', Type.find('sys::Obj'), False)], {})
_t.am_('getOrAdd', 1, 'sys::Obj', [Param('key', Type.find('sys::Obj'), False), Param('defVal', Type.find('sys::Obj'), False)], {})
_t.am_('setAll', 1, 'concurrent::ConcurrentMap', [Param('m', Type.find('sys::Map'), False)], {})
_t.am_('remove', 1, 'sys::Obj?', [Param('key', Type.find('sys::Obj'), False)], {})
_t.am_('clear', 1, 'sys::Void', [], {})
_t.am_('containsKey', 1, 'sys::Bool', [Param('key', Type.find('sys::Obj'), False)], {})
_t.am_('keys', 1, 'sys::Obj[]', [Param('of', Type.find('sys::Type'), False)], {})
_t.am_('vals', 1, 'sys::Obj[]', [Param('of', Type.find('sys::Type'), False)], {})
