#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#
# Refactored to extend Obj + MutableMapping
#

from collections.abc import MutableMapping
from .Obj import Obj


class Map(Obj, MutableMapping):
    """Fantom Map - extends Obj, implements Python's MutableMapping ABC.

    This follows the architecture where Map is a pure Fantom class that
    extends sys::Obj and wraps an internal Python dict rather than inheriting
    from Python's dict directly.
    """

    def __init__(self):
        """Create a new Map with internal dict storage."""
        # Note: Don't call Obj.__init__ as Obj doesn't define __init__
        self._map = {}  # Internal storage
        self._def = None  # Default value
        self._ro = False  # Read-only flag
        self._immutable = False  # Immutable flag (distinct from ro)
        self._ordered = False  # Ordered flag
        self._caseInsensitive = False  # Case-insensitive keys
        self._keyType = None  # Fantom key type
        self._valueType = None  # Fantom value type
        self._mapType = None  # Cached MapType
        self._roView = None  # Cached read-only view

    #################################################################
    # ABC Required Methods (MutableMapping)
    #################################################################

    def _find_key(self, key):
        """Find the actual key in the map, handling case-insensitivity"""
        if key in self._map:
            return key
        if self._caseInsensitive and isinstance(key, str):
            key_lower = key.lower()
            for k in self._map:
                if isinstance(k, str) and k.lower() == key_lower:
                    return k
        return None

    def __getitem__(self, key):
        """Get value by key, return default/null if not found"""
        actual_key = self._find_key(key)
        if actual_key is not None:
            return self._map[actual_key]
        # Return default if set, otherwise return None (Fantom null semantics)
        return self._def

    def __setitem__(self, key, value):
        """Set value by key"""
        self._check_readonly()
        # Check if key is immutable (required for Map keys)
        from .ObjUtil import ObjUtil
        if not ObjUtil.is_immutable(key):
            from .Err import NotImmutableErr
            from .Type import Type
            raise NotImmutableErr.make(f"Map key is not immutable: {Type.of(key)}")
        # Invalidate ro cache when modified
        self._roView = None
        # Handle case-insensitive keys
        if self._caseInsensitive and isinstance(key, str):
            actual_key = self._find_key(key)
            if actual_key is not None:
                self._map[actual_key] = value
                return
        self._map[key] = value

    def __delitem__(self, key):
        """Delete by key"""
        self._check_readonly()
        self._roView = None
        actual_key = self._find_key(key)
        if actual_key is not None:
            del self._map[actual_key]
        else:
            del self._map[key]  # Will raise KeyError if not found

    def __len__(self):
        """Return number of entries"""
        return len(self._map)

    def __iter__(self):
        """Iterate over keys"""
        return iter(self._map)

    def __contains__(self, key):
        """Check if key exists, handling case-insensitivity"""
        return self._find_key(key) is not None

    #################################################################
    # Additional Python Protocol Methods
    #################################################################

    def __repr__(self):
        return f"Map({self._map})"

    def __str__(self):
        return self.to_str()

    def __eq__(self, other):
        """Equality comparison - maps must have same type and content"""
        from .ObjUtil import ObjUtil
        if other is self:
            return True
        if other is None:
            return False
        # Handle comparison with plain dicts or Maps
        if isinstance(other, Map):
            # Check type equality - only if BOTH maps have explicit types
            # (Maps without type info, like URI query maps, compare by content only)
            if self._mapType is not None and other._mapType is not None:
                if self._mapType != other._mapType:
                    return False
            other_items = other._map
        elif isinstance(other, dict):
            other_items = other
        else:
            return False
        if len(self._map) != len(other_items):
            return False
        for k, v in self._map.items():
            if k not in other_items:
                return False
            if not ObjUtil.equals(v, other_items[k]):
                return False
        return True

    def equals(self, other):
        """Fantom equals - delegates to __eq__"""
        return self.__eq__(other)

    def __hash__(self):
        """Make Map hashable for use as map keys (like Fantom immutable maps)"""
        if not self._immutable:
            return id(self)
        try:
            return hash(frozenset(self._map.items()))
        except TypeError:
            return id(self)

    #################################################################
    # Read-only Check
    #################################################################

    def _check_readonly(self):
        """Check if map is readonly - override in subclasses"""
        if self._ro:
            from .Err import ReadonlyErr
            raise ReadonlyErr("Map is read-only")

    #################################################################
    # Static Factory Methods
    #################################################################

    @staticmethod
    def make(type_param=None, capacity=None):
        """Create a new map with optional type and capacity."""
        from .Type import Type, MapType
        result = Map()
        # Handle the case where first param is the Map class itself
        if type_param is Map:
            if capacity is not None:
                type_param = capacity
                capacity = None
            else:
                return result
        # Extract key/value types from MapType
        if type_param is not None:
            if isinstance(type_param, MapType):
                # Validate key type is not nullable (Fantom requirement)
                keyTypeSig = type_param.k.signature() if hasattr(type_param.k, 'signature') else str(type_param.k)
                if keyTypeSig.endswith("?"):
                    from .Err import ArgErr
                    raise ArgErr(f"Map key type cannot be nullable: {keyTypeSig}")
                result._mapType = type_param
                result._keyType = type_param.k
                result._valueType = type_param.v
            elif isinstance(type_param, Type) and hasattr(type_param, 'k'):
                # Validate key type is not nullable
                keyTypeSig = type_param.k.signature() if hasattr(type_param.k, 'signature') else str(type_param.k)
                if keyTypeSig.endswith("?"):
                    from .Err import ArgErr
                    raise ArgErr(f"Map key type cannot be nullable: {keyTypeSig}")
                result._mapType = type_param
                result._keyType = type_param.k
                result._valueType = type_param.v
        return result

    @staticmethod
    def make_with_type(keyType, valType):
        """Create a Map with explicit key and value types.

        Args:
            keyType: Key type as string qname or Type
            valType: Value type as string qname or Type

        Returns:
            New Map with the specified types
        """
        from .Type import Type, MapType
        result = Map()
        if isinstance(keyType, str):
            keyType = Type.find(keyType)
        if isinstance(valType, str):
            valType = Type.find(valType)
        result._keyType = keyType
        result._valueType = valType
        result._mapType = MapType(keyType, valType)
        return result

    @staticmethod
    def from_literal(keys, vals, keyType, valueType):
        """Create map from parallel key/value arrays."""
        from .Type import Type, MapType
        result = Map()
        if isinstance(keyType, str):
            keyType = Type.find(keyType)
        if isinstance(valueType, str):
            valueType = Type.find(valueType)
        result._keyType = keyType
        result._valueType = valueType
        result._mapType = MapType(keyType, valueType)
        for k, v in zip(keys, vals):
            result._map[k] = v
        return result

    @staticmethod
    def from_dict(d):
        """Create a Map from a Python dict"""
        result = Map()
        if d is not None:
            for k, v in d.items():
                result._map[k] = v
        return result

    #################################################################
    # Properties
    #################################################################

    def size(self):
        """Return number of entries"""
        return len(self._map)

    def is_empty(self):
        """Return true if map is empty"""
        return len(self._map) == 0

    @property
    def def_(self):
        """Get default value"""
        return self._def

    @def_.setter
    def def_(self, val):
        """Set default value - must be immutable"""
        self._check_readonly()
        if val is not None:
            from .ObjUtil import ObjUtil
            if not ObjUtil.is_immutable(val):
                from .Err import NotImmutableErr
                raise NotImmutableErr.make("Map default value is not immutable")
        self._def = val

    @property
    def ordered(self):
        """Get ordered flag"""
        return self._ordered

    @ordered.setter
    def ordered(self, val):
        """Set ordered flag"""
        self._check_readonly()
        if len(self._map) > 0:
            from .Err import UnsupportedErr
            raise UnsupportedErr.make("Map not empty")
        if val and self._caseInsensitive:
            from .Err import UnsupportedErr
            raise UnsupportedErr.make("Map cannot be caseInsensitive and ordered")
        self._ordered = val

    @property
    def case_insensitive(self):
        """Get case-insensitive flag"""
        return self._caseInsensitive

    @case_insensitive.setter
    def case_insensitive(self, val):
        """Set case-insensitive flag"""
        self._check_readonly()
        if self._keyType is not None:
            sig = self._keyType.signature() if hasattr(self._keyType, 'signature') else str(self._keyType)
            if sig != "sys::Str":
                from .Err import UnsupportedErr
                raise UnsupportedErr.make(f"Map not keyed by Str: {sig}")
        if len(self._map) > 0:
            from .Err import UnsupportedErr
            raise UnsupportedErr.make("Map not empty")
        if val and self._ordered:
            from .Err import UnsupportedErr
            raise UnsupportedErr.make("Map cannot be caseInsensitive and ordered")
        self._caseInsensitive = val

    #################################################################
    # Accessor Methods
    #################################################################

    def get(self, key, default=None):
        """Get value by key, return default if not found"""
        actual_key = self._find_key(key)
        if actual_key is not None:
            return self._map[actual_key]
        if default is not None:
            return default
        return self._def

    def get_or_throw(self, key):
        """Get value or throw if not found"""
        if key in self:
            return self[key]
        from .Err import UnknownKeyErr
        raise UnknownKeyErr(f"Key not found: {key}")

    def get_checked(self, key, checked=True):
        """Get value, throw UnknownKeyErr if not found and checked=True.

        Uses multi-pass lookup to support both Fantom names (camelCase) and
        Python names (snake_case). This enables reflection-based lookups
        where Fantom code uses camelCase names but Python stores snake_case.

        Pass 1: exact match
        Pass 2: camelCase -> snake_case conversion
        Pass 3: Python builtin escaping (map -> map_)
        Pass 4: Combined snake_case + builtin escaping
        """
        # Pass 1: exact match
        if key in self:
            return self[key]

        if isinstance(key, str):
            from .Type import _camel_to_snake, _PYTHON_BUILTINS

            # Pass 2: try camelCase -> snake_case conversion
            # This handles Fantom reflection APIs where names like "parseBool"
            # need to find functions stored as "parse_bool"
            snake_key = _camel_to_snake(key)
            if snake_key != key and snake_key in self:
                return self[snake_key]

            # Pass 3: try Python builtin escaping (map -> map_)
            # This handles Fantom names that conflict with Python builtins
            if key in _PYTHON_BUILTINS:
                escaped_key = key + '_'
                if escaped_key in self:
                    return self[escaped_key]

            # Pass 4: try snake_case + builtin escaping
            # This handles camelCase names that become Python builtins after conversion
            if snake_key in _PYTHON_BUILTINS:
                escaped_snake_key = snake_key + '_'
                if escaped_snake_key in self:
                    return self[escaped_snake_key]

        if checked:
            from .Err import UnknownKeyErr
            raise UnknownKeyErr(f"Key not found: {key}")
        return None

    def contains_key(self, key):
        """Check if map contains key"""
        return key in self

    def keys(self):
        """Return keys as List"""
        from .List import List
        return List.from_literal(list(self._map.keys()), self._keyType or "sys::Obj")

    def vals(self):
        """Return values as List"""
        from .List import List
        return List.from_literal(list(self._map.values()), self._valueType or "sys::Obj")

    #################################################################
    # Modification Methods
    #################################################################

    def set_(self, key, val):
        """Set key-value pair, return self"""
        self[key] = val
        return self

    def add(self, key, val):
        """Add key-value pair (throws if key exists)"""
        if key in self:
            from .Err import ArgErr
            raise ArgErr(f"Key already mapped: {key}")
        self[key] = val
        return self

    def add_not_null(self, key, val):
        """Add entry only if value is not null"""
        if val is not None:
            self[key] = val
        return self

    def set_not_null(self, key, val):
        """Set entry only if value is not null"""
        if val is not None:
            self[key] = val
        return self

    def remove(self, key):
        """Remove key and return its value"""
        self._check_readonly()
        if key in self:
            val = self[key]
            del self[key]
            return val
        return None

    def clear(self):
        """Clear all entries"""
        self._check_readonly()
        self._map.clear()
        self._roView = None
        return self

    def set_all(self, other):
        """Add all entries from another map"""
        for k, v in other.items():
            self[k] = v
        return self

    def add_all(self, other):
        """Add all entries (throws if any key exists)"""
        for k in other:
            if k in self:
                from .Err import ArgErr
                raise ArgErr(f"Key already mapped: {k}")
        for k, v in other.items():
            self[k] = v
        return self

    def get_or_add(self, key, valFunc):
        """Get value or add default if not present"""
        if key in self:
            return self[key]
        val = valFunc(key)
        self[key] = val
        return val

    def set_list(self, list_val, f=None):
        """Set entries from list using optional key transform"""
        if f is None:
            for v in list_val:
                self[v] = v
        else:
            param_count = Map._get_param_count(f)
            for i, v in enumerate(list_val):
                k = f(v, i) if param_count >= 2 else f(v)
                self[k] = v
        return self

    def add_list(self, list_val, f=None):
        """Add entries from list (throws if any key exists)"""
        if f is None:
            for v in list_val:
                if v in self:
                    from .Err import ArgErr
                    raise ArgErr(f"Key already exists: {v}")
                self[v] = v
        else:
            param_count = Map._get_param_count(f)
            for i, v in enumerate(list_val):
                k = f(v, i) if param_count >= 2 else f(v)
                if k in self:
                    from .Err import ArgErr
                    raise ArgErr(f"Key already exists: {k}")
                self[k] = v
        return self

    #################################################################
    # Iteration Methods
    #################################################################

    @staticmethod
    def _get_param_count(f):
        """Get number of required parameters for a function"""
        from .Func import Func
        if isinstance(f, Func):
            return len(f.params())
        import inspect
        try:
            sig = inspect.signature(f)
            return len([p for p in sig.parameters.values()
                       if p.default is inspect.Parameter.empty])
        except:
            return 1

    def each(self, f):
        """Iterate over entries - supports |V| or |V,K| closures"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                f(v, k)  # Fantom: |V val, K key|
        else:
            for v in self._map.values():
                f(v)

    def each_while(self, f):
        """Iterate until f returns non-null"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                result = f(v, k)
                if result is not None:
                    return result
        else:
            for v in self._map.values():
                result = f(v)
                if result is not None:
                    return result
        return None

    def find(self, f):
        """Find first value matching predicate"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                if f(v, k):
                    return v
        else:
            for v in self._map.values():
                if f(v):
                    return v
        return None

    def find_all(self, f):
        """Find all values matching predicate, return as map"""
        result = Map()
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                if f(v, k):
                    result._map[k] = v
        else:
            for k, v in self._map.items():
                if f(v):
                    result._map[k] = v
        return result

    def exclude(self, f):
        """Exclude values matching predicate"""
        result = Map()
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                if not f(v, k):
                    result._map[k] = v
        else:
            for k, v in self._map.items():
                if not f(v):
                    result._map[k] = v
        return result

    def any_(self, f):
        """Return true if any entry matches"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                if f(v, k):
                    return True
        else:
            for v in self._map.values():
                if f(v):
                    return True
        return False

    def all_(self, f):
        """Return true if all entries match"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                if not f(v, k):
                    return False
        else:
            for v in self._map.values():
                if not f(v):
                    return False
        return True

    #################################################################
    # Transformation Methods
    #################################################################

    def map_(self, f):
        """Transform values, return new map"""
        from .Type import MapType
        from .Func import Func
        result = Map()
        result._keyType = self._keyType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        # Get return type from func
        if isinstance(f, Func) and hasattr(f, 'returns'):
            retType = f.returns()
            if retType is not None:
                result._valueType = retType
                if result._keyType is not None:
                    result._mapType = MapType(result._keyType, retType)
        else:
            result._valueType = self._valueType
            result._mapType = self._mapType
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                result._map[k] = f(v, k)
        else:
            for k, v in self._map.items():
                result._map[k] = f(v)
        return result

    def map_not_null(self, f):
        """Transform values, excluding null results"""
        from .Type import MapType
        from .Func import Func
        result = Map()
        result._keyType = self._keyType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        if isinstance(f, Func) and hasattr(f, 'returns'):
            retType = f.returns()
            if retType is not None:
                if hasattr(retType, 'to_non_nullable'):
                    result._valueType = retType.to_non_nullable()
                else:
                    result._valueType = retType
        else:
            result._valueType = self._valueType
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self._map.items():
                mapped = f(v, k)
                if mapped is not None:
                    result._map[k] = mapped
        else:
            for k, v in self._map.items():
                mapped = f(v)
                if mapped is not None:
                    result._map[k] = mapped
        return result

    def find_not_null(self):
        """Return map with non-null values only"""
        from .Type import MapType
        result = Map()
        result._keyType = self._keyType
        if self._valueType is not None and hasattr(self._valueType, 'to_non_nullable'):
            result._valueType = self._valueType.to_non_nullable()
        else:
            result._valueType = self._valueType
        if result._keyType is not None and result._valueType is not None:
            result._mapType = MapType(result._keyType, result._valueType)
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        for k, v in self._map.items():
            if v is not None:
                result._map[k] = v
        return result

    def reduce(self, init, f):
        """Reduce map to single value"""
        acc = init
        param_count = Map._get_param_count(f)
        if param_count >= 3:
            for k, v in self._map.items():
                acc = f(acc, v, k)
        else:
            for v in self._map.values():
                acc = f(acc, v)
        return acc

    def join(self, sep="", f=None):
        """Join values into string"""
        from .ObjUtil import ObjUtil
        if f is None:
            items = [f"{ObjUtil.to_str(k)}: {ObjUtil.to_str(v)}" for k, v in self._map.items()]
        else:
            param_count = Map._get_param_count(f)
            if param_count >= 2:
                items = [f(v, k) for k, v in self._map.items()]
            else:
                items = [f(v) for v in self._map.values()]
        return sep.join(ObjUtil.to_str(item) for item in items)

    def dup(self):
        """Return a duplicate of this map"""
        result = Map()
        result._map = dict(self._map)
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        result._def = self._def
        return result

    #################################################################
    # RO/Immutable Methods
    #################################################################

    def is_ro(self):
        """Check if read-only"""
        return self._ro

    def is_rw(self):
        """Check if read-write"""
        return not self._ro

    def ro(self):
        """Return read-only snapshot of this map"""
        if self._ro:
            return self
        # Create a new immutable snapshot (not cached since original can change)
        return ReadOnlyMap(self)

    def rw(self):
        """Return read-write view (creates a copy if this is RO)"""
        if not self._ro:
            return self
        result = Map()
        result._map = dict(self._map)
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        result._def = self._def
        result._ro = False
        return result

    def is_immutable(self):
        """Check if truly immutable"""
        return self._immutable

    def to_immutable(self):
        """Return immutable copy"""
        from .ObjUtil import ObjUtil
        if self._immutable:
            return self
        result = Map()
        result._ro = True
        result._immutable = True
        result._mapType = self._mapType
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._def = self._def
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        for k, v in self._map.items():
            result._map[k] = ObjUtil.to_immutable(v)
        return result

    #################################################################
    # Utility Methods
    #################################################################

    def to_str(self):
        """Format as Fantom-style string [k:v, k:v]"""
        from .ObjUtil import ObjUtil
        if len(self._map) == 0:
            return "[:]"
        items = [f"{ObjUtil.to_str(k)}:{ObjUtil.to_str(v)}" for k, v in self._map.items()]
        return "[" + ", ".join(items) + "]"

    def to_code(self):
        """Return code representation"""
        from .ObjUtil import ObjUtil
        mapType = self.typeof()
        typeSig = mapType.signature() if hasattr(mapType, 'signature') else "[sys::Obj:sys::Obj?]"
        if len(self._map) == 0:
            return f"{typeSig}[:]"
        items = []
        for k, v in self._map.items():
            kStr = f'"{k}"' if isinstance(k, str) else ObjUtil.to_str(k)
            vStr = ObjUtil.to_code(v) if hasattr(ObjUtil, 'to_code') else ObjUtil.to_str(v)
            items.append(f"{kStr}:{vStr}")
        return f"{typeSig}[" + ", ".join(items) + "]"

    def hash_(self):
        """Return hash code"""
        h = 0
        from .ObjUtil import ObjUtil
        for k, v in self._map.items():
            h ^= ObjUtil.hash_(k) ^ ObjUtil.hash_(v)
        return h

    def typeof(self):
        """Return Fantom Type for Map"""
        from .Type import Type
        if self._mapType is not None:
            return self._mapType
        return Type.find("sys::Map")

    def trap(self, name, args=None):
        """Dynamic method invocation"""
        if args is None:
            args = []
        # Handle properties
        attr = getattr(type(self), name, None)
        if isinstance(attr, property):
            if args:
                setattr(self, name, args[0])
                return None
            else:
                return getattr(self, name)
        # Handle methods
        method = getattr(self, name, None)
        if method and callable(method):
            return method(*args)
        raise AttributeError(f"Map.{name}")

    def with_(self, f):
        """Apply it-block closure to map"""
        f(self)
        return self

    def literal_encode(self, out):
        """Encode for serialization"""
        out.write_map(self)

    #################################################################
    # Python Interop (to_py / from_py)
    #################################################################

    def to_py(self, deep=False):
        """Convert to native Python dict.

        Args:
            deep: If True, recursively convert nested Fantom types (List, Map,
                  DateTime, Duration, Date, Time) to their Python equivalents.
                  If False (default), return a dict with Fantom values.

        Returns:
            A Python dict containing the map's key-value pairs.

        Example:
            >>> fantom_map.to_py()
            {'name': 'test', 'count': 42}

            >>> fantom_map.to_py(deep=True)  # Converts nested Lists/Maps too
            {'items': [1, 2, 3], 'meta': {'key': 'value'}}
        """
        if not deep:
            return dict(self._map)

        # Deep conversion - recursively convert Fantom types
        result = {}
        for k, v in self._map.items():
            result[k] = _to_py_deep(v)
        return result


#################################################################
# ReadOnlyMap - Read-only view of a Map
#################################################################

class ReadOnlyMap(Map):
    """Read-only snapshot of a Map - throws ReadonlyErr on modification"""

    def __init__(self, source):
        """Create read-only snapshot of source map"""
        super().__init__()
        self._source = source
        self._map = dict(source._map)  # COPY the dict for snapshot semantics
        self._ro = True
        self._keyType = source._keyType
        self._valueType = source._valueType
        self._mapType = source._mapType
        self._ordered = source._ordered
        self._caseInsensitive = source._caseInsensitive
        self._def = source._def

    def _check_readonly(self):
        from .Err import ReadonlyErr
        raise ReadonlyErr("Map is read-only")

    def is_ro(self):
        return True

    def is_rw(self):
        return False

    def ro(self):
        return self

    def rw(self):
        """Return mutable copy"""
        result = Map()
        result._map = dict(self._map)
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        result._def = self._def
        result._ro = False
        return result


#################################################################
# Helper: Deep Python conversion
#################################################################

def _to_py_deep(val):
    """Recursively convert a Fantom value to its Python equivalent.

    Handles: Map, List, DateTime, Duration, Date, Time.
    Other values are returned as-is.
    """
    if val is None:
        return None

    # Map -> dict
    if isinstance(val, Map):
        return val.to_py(deep=True)

    # List -> list (import here to avoid circular)
    from .List import List
    if isinstance(val, List):
        return val.to_py(deep=True)

    # DateTime -> datetime.datetime
    from .DateTime import DateTime
    if isinstance(val, DateTime):
        return val.to_py()

    # Duration -> datetime.timedelta
    from .Duration import Duration
    if isinstance(val, Duration):
        return val.to_py()

    # Date -> datetime.date
    from .Date import Date
    if isinstance(val, Date):
        return val.to_py()

    # Time -> datetime.time
    from .Time import Time
    if isinstance(val, Time):
        return val.to_py()

    # Other values (str, int, float, bool, etc.) - return as-is
    return val
