#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Map(dict, Obj):
    """Map type - wraps Python dict with Fantom-style methods"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._def = None  # default value
        self._ro = False  # read-only flag
        self._immutable = False  # immutable flag (distinct from ro)
        self._ordered = False  # ordered flag
        self._orderedKeys = []  # Track insertion order when ordered=True
        self._caseInsensitive = False  # case-insensitive keys
        self._keyType = None  # Fantom key type
        self._valueType = None  # Fantom value type
        self._mapType = None  # Cached MapType
        self._roView = None  # Cached read-only view

    @staticmethod
    def make(type_param=None, capacity=None):
        """Create a new map with optional type and capacity.

        Args:
            type_param: Can be either:
                - The Map class itself (ignored, for compatibility)
                - A MapType object
                - A Type object that is a MapType
            capacity: Optional capacity hint (ignored in Python)
        """
        from .Type import Type, MapType

        result = Map()

        # Handle the case where first param is the Map class itself (transpiler artifact)
        if type_param is Map:
            # Second param (capacity) might actually be the type
            if capacity is not None:
                type_param = capacity
                capacity = None
            else:
                return result

        # If we have a type, extract key/value types
        if type_param is not None:
            if isinstance(type_param, MapType):
                # Validate key type is not nullable
                if type_param.k is not None and hasattr(type_param.k, 'isNullable') and type_param.k.isNullable():
                    from .Err import ArgErr
                    raise ArgErr("Map key type cannot be nullable")
                result._mapType = type_param
                result._keyType = type_param.k
                result._valueType = type_param.v
            elif isinstance(type_param, Type):
                # Check if it's a parameterized Map type
                if hasattr(type_param, 'k') and hasattr(type_param, 'v'):
                    result._mapType = type_param
                    result._keyType = type_param.k
                    result._valueType = type_param.v
                elif hasattr(type_param, 'signature'):
                    # Parse signature like "[sys::Str:sys::File]"
                    sig = type_param.signature()
                    if sig.startswith('[') and ':' in sig:
                        # This is a MapType - use it directly
                        result._mapType = type_param
                        # Try to get k/v from the type
                        if hasattr(type_param, 'k'):
                            result._keyType = type_param.k
                        if hasattr(type_param, 'v'):
                            result._valueType = type_param.v

        return result

    @staticmethod
    def makeEmpty():
        """Create an empty map - convenience static factory"""
        return Map()

    @staticmethod
    def fromDict(d):
        """Create a Map from a Python dict"""
        if d is None:
            return Map()
        result = Map()
        for k, v in d.items():
            result[k] = v
        return result

    @staticmethod
    def makeWithType(keyType, valueType, pairs=None):
        """Create type-aware map like JavaScript Map.make()

        Args:
            keyType: The Fantom key type (Type object or string signature)
            valueType: The Fantom value type (Type object or string signature)
            pairs: Initial key-value pairs as dict
        """
        from .Type import Type, MapType

        result = Map(pairs or {})

        # Convert string signatures to Type objects if needed
        if isinstance(keyType, str):
            keyType = Type.find(keyType)
        if isinstance(valueType, str):
            valueType = Type.find(valueType)

        result._keyType = keyType
        result._valueType = valueType
        result._mapType = MapType(keyType, valueType)
        return result

    @staticmethod
    def fromLiteral(keys, vals, keyType, valueType):
        """Create map from parallel key/value arrays like JavaScript Map.fromLiteral()

        Args:
            keys: List of keys
            vals: List of values
            keyType: The Fantom key type
            valueType: The Fantom value type
        """
        from .Type import Type, MapType

        result = Map()

        # Convert string signatures to Type objects if needed
        if isinstance(keyType, str):
            keyType = Type.find(keyType)
        if isinstance(valueType, str):
            valueType = Type.find(valueType)

        result._keyType = keyType
        result._valueType = valueType
        result._mapType = MapType(keyType, valueType)

        # Populate map
        for k, v in zip(keys, vals):
            result[k] = v

        return result

    @property
    def def_(self):
        """Get default value"""
        return self._def

    @def_.setter
    def def_(self, val):
        """Set default value"""
        if self._ro:
            from .Err import ReadonlyErr
            raise ReadonlyErr("Map is read-only")
        self._def = val

    @property
    def _def_(self):
        """Alias for _def for direct assignment"""
        return self._def

    @_def_.setter
    def _def_(self, val):
        """Alias for _def for direct assignment"""
        self._def = val

    @staticmethod
    def _get_param_count(f):
        """Get number of required parameters for a function"""
        # Check if f is a Func instance - use its params() method
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

    def size(self):
        return len(self)

    def isEmpty(self):
        return len(self) == 0

    def _findKey(self, key):
        """Find the actual key in the dict, handling case-insensitivity"""
        if key in dict.keys(self):
            return key
        if self._caseInsensitive and isinstance(key, str):
            key_lower = key.lower()
            for k in dict.keys(self):
                if isinstance(k, str) and k.lower() == key_lower:
                    return k
        return None

    def __contains__(self, key):
        """Check if key exists, handling case-insensitivity"""
        return self._findKey(key) is not None

    def __getitem__(self, key):
        """Get value by key, return default if not found"""
        actual_key = self._findKey(key)
        if actual_key is not None:
            return super().__getitem__(actual_key)
        return self._def

    def __setitem__(self, key, value):
        """Set value by key, handling case-insensitivity"""
        # Check if map is read-only
        if self._ro:
            from .Err import ReadonlyErr
            raise ReadonlyErr("Map is read-only")

        # Invalidate ro cache when modified
        self._roView = None

        # Handle case-insensitive keys - update existing key if found
        if self._caseInsensitive and isinstance(key, str):
            actual_key = self._findKey(key)
            if actual_key is not None:
                # Update existing key's value
                super().__setitem__(actual_key, value)
                return
        super().__setitem__(key, value)

    def __delitem__(self, key):
        """Delete by key, handling case-insensitivity and cache invalidation"""
        # Invalidate ro cache when modified
        self._roView = None

        actual_key = self._findKey(key)
        if actual_key is not None:
            super().__delitem__(actual_key)
        else:
            super().__delitem__(key)  # Will raise KeyError if not found

    def get(self, key, default=None):
        """Get value by key, return default if not found"""
        actual_key = self._findKey(key)
        if actual_key is not None:
            return super().__getitem__(actual_key)
        return default

    def getOrThrow(self, key):
        """Get value or throw if not found"""
        if key in self:
            return self[key]
        raise KeyError(f"Key not found: {key}")

    def set(self, key, val):
        self[key] = val
        return self

    def add(self, key, val):
        """Add key-value pair (throws ArgErr if key already exists)"""
        if key in self:
            from .Err import ArgErr
            raise ArgErr(f"Key already mapped: {key}")
        self[key] = val
        return self

    def containsKey(self, key):
        return key in self

    def keys(self):
        """Return keys as list (override dict.keys to return list)"""
        return list(super().keys())

    def vals(self):
        """Return values as list"""
        return list(super().values())

    def each(self, f):
        """Iterate over entries - supports |V| or |V,K| closures"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                f(v, k)  # Fantom: |V val, K key|
        else:
            for v in self.values():
                f(v)

    def eachWhile(self, f):
        """Iterate until f returns non-null"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                result = f(v, k)
                if result is not None:
                    return result
        else:
            for v in self.values():
                result = f(v)
                if result is not None:
                    return result
        return None

    def find(self, f):
        """Find first value matching predicate"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                if f(v, k):
                    return v
        elif param_count == 1:
            for v in self.values():
                if f(v):
                    return v
        else:
            # 0-param closure
            for v in self.values():
                if f():
                    return v
        return None

    def findAll(self, f):
        """Find all values matching predicate, return as map"""
        result = Map()
        # Preserve type information
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                if f(v, k):
                    result[k] = v
        else:
            for k, v in self.items():
                if f(v):
                    result[k] = v
        return result

    def exclude(self, f):
        """Exclude values matching predicate"""
        result = Map()
        # Preserve type information
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                if not f(v, k):
                    result[k] = v
        else:
            for k, v in self.items():
                if not f(v):
                    result[k] = v
        return result

    def any(self, f):
        """Return true if any entry matches"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                if f(v, k):
                    return True
        else:
            for v in self.values():
                if f(v):
                    return True
        return False

    def all(self, f):
        """Return true if all entries match"""
        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                if not f(v, k):
                    return False
        else:
            for v in self.values():
                if not f(v):
                    return False
        return True

    def map_(self, f):
        """Transform values, return new map"""
        from .Type import Type, MapType
        from .Func import Func

        result = Map()
        # Preserve key type and flags
        result._keyType = self._keyType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive

        # Get the return type from the func to determine new value type
        newValueType = None
        if isinstance(f, Func) and hasattr(f, 'returns'):
            retType = f.returns()
            if retType is not None:
                newValueType = retType

        if newValueType is not None:
            result._valueType = newValueType
            if result._keyType is not None:
                result._mapType = MapType(result._keyType, newValueType)
        else:
            result._valueType = self._valueType
            result._mapType = self._mapType

        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                result[k] = f(v, k)
        else:
            for k, v in self.items():
                result[k] = f(v)
        return result

    def mapNotNull(self, f):
        """Transform values, excluding null results"""
        from .Type import Type, MapType
        from .Func import Func

        result = Map()
        # Preserve key type and flags
        result._keyType = self._keyType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive

        # Get the return type from the func to determine new value type
        newValueType = None
        if isinstance(f, Func) and hasattr(f, 'returns'):
            retType = f.returns()
            if retType is not None:
                # Get non-nullable version since mapNotNull excludes nulls
                if hasattr(retType, 'toNonNullable'):
                    newValueType = retType.toNonNullable()
                else:
                    newValueType = retType

        if newValueType is not None:
            result._valueType = newValueType
            if result._keyType is not None:
                result._mapType = MapType(result._keyType, newValueType)
        else:
            result._valueType = self._valueType
            result._mapType = self._mapType

        param_count = Map._get_param_count(f)
        if param_count >= 2:
            for k, v in self.items():
                mapped = f(v, k)
                if mapped is not None:
                    result[k] = mapped
        else:
            for k, v in self.items():
                mapped = f(v)
                if mapped is not None:
                    result[k] = mapped
        return result

    def reduce(self, init, f):
        """Reduce map to single value"""
        acc = init
        param_count = Map._get_param_count(f)
        if param_count >= 3:
            for k, v in self.items():
                acc = f(acc, v, k)
        else:
            for v in self.values():
                acc = f(acc, v)
        return acc

    def join(self, sep="", f=None):
        """Join values into string with optional transform function"""
        from .ObjUtil import ObjUtil
        if f is None:
            items = [f"{ObjUtil.toStr(k)}: {ObjUtil.toStr(v)}" for k, v in self.items()]
        else:
            param_count = Map._get_param_count(f)
            if param_count >= 2:
                items = [f(v, k) for k, v in self.items()]
            else:
                items = [f(v) for v in super().values()]
        return sep.join(ObjUtil.toStr(item) for item in items)

    def toStr(self):
        """Format as Fantom-style string [k:v, k:v]"""
        from .ObjUtil import ObjUtil
        if len(self) == 0:
            return "[:]"
        items = [f"{ObjUtil.toStr(k)}:{ObjUtil.toStr(v)}" for k, v in self.items()]
        return "[" + ", ".join(items) + "]"

    def __str__(self):
        """Override to call our toStr instead of dict's"""
        return self.toStr()

    def equals(self, that):
        """Check equality with another map.

        Maps must have matching types and equal contents to be equal.
        Empty maps with different declared types are NOT equal.
        """
        if that is None:
            return False
        if not isinstance(that, dict):
            return False

        # Check type signatures - maps with different declared types are NOT equal
        selfType = self.typeof()
        thatType = that.typeof() if hasattr(that, 'typeof') else None
        if selfType and thatType:
            selfSig = selfType.signature() if hasattr(selfType, 'signature') else str(selfType)
            thatSig = thatType.signature() if hasattr(thatType, 'signature') else str(thatType)
            if selfSig != thatSig:
                return False

        if len(self) != len(that):
            return False
        for k, v in self.items():
            if k not in that:
                return False
            from .ObjUtil import ObjUtil
            if not ObjUtil.equals(v, that[k]):
                return False
        return True

    def hash(self):
        """Hash code for the map"""
        h = 0
        from .ObjUtil import ObjUtil
        for k, v in self.items():
            h ^= ObjUtil.hash(k) ^ ObjUtil.hash(v)
        return h

    def clear(self):
        """Clear all entries"""
        # Check if map is read-only
        if self._ro:
            from .Err import ReadonlyErr
            raise ReadonlyErr("Map is read-only")
        super().clear()
        return self

    def dup(self):
        """Return a duplicate of this map"""
        result = Map(self)
        # Preserve type information
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        result._def = self._def
        return result

    def remove(self, key):
        """Remove a key and return its value"""
        # Check if map is read-only
        if self._ro:
            from .Err import ReadonlyErr
            raise ReadonlyErr("Map is read-only")
        if key in self:
            val = self[key]
            del self[key]
            return val
        return None

    def setAll(self, other):
        """Add all entries from another map"""
        for k, v in other.items():
            self[k] = v
        return self

    def addAll(self, other):
        """Add all entries from another map (throws ArgErr if any key exists)"""
        for k, v in other.items():
            if k in self:
                from .Err import ArgErr
                raise ArgErr(f"Key already mapped: {k}")
        # Now add all (after validation)
        for k, v in other.items():
            self[k] = v
        return self

    def getOrAdd(self, key, valFunc):
        """Get value or add default if not present.

        Args:
            key: The key to look up
            valFunc: A function |K->V| that generates the value from the key
        """
        if key in self:
            return self[key]
        # Call the function to generate the value
        val = valFunc(key)
        self[key] = val
        return val

    def isRO(self):
        """Check if read-only"""
        return self._ro

    def isRW(self):
        """Check if read-write"""
        return not self._ro

    def ro(self):
        """Return read-only view of this map"""
        if self._ro:
            return self
        # Return cached ro view if available and still valid
        if self._roView is not None:
            return self._roView
        # Create new read-only view
        self._roView = ReadOnlyMap(self)
        return self._roView

    def rw(self):
        """Return read-write view (creates a copy if this is RO)"""
        if not self._ro:
            return self
        # Make a mutable copy
        result = Map(self)
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        result._def = self._def
        result._ro = False
        return result

    @property
    def ordered(self):
        """Get ordered flag"""
        return self._ordered

    @ordered.setter
    def ordered(self, val):
        """Set ordered flag"""
        if self._ro:
            from .Err import ReadonlyErr
            raise ReadonlyErr("Map is read-only")
        self._ordered = val

    @property
    def caseInsensitive(self):
        """Get case-insensitive flag"""
        return self._caseInsensitive

    @caseInsensitive.setter
    def caseInsensitive(self, val):
        """Set case-insensitive flag - throws UnsupportedErr if:
        - map has keys already
        - key type is not Str
        """
        if len(self) > 0:
            from .Err import UnsupportedErr
            raise UnsupportedErr("Cannot change caseInsensitive after map has keys")
        # Check if key type supports case-insensitivity (must be Str)
        if val and self._keyType is not None:
            sig = self._keyType.signature() if hasattr(self._keyType, 'signature') else str(self._keyType)
            if sig != "sys::Str":
                from .Err import UnsupportedErr
                raise UnsupportedErr("caseInsensitive requires Str keys")
        if self._ro:
            from .Err import ReadonlyErr
            raise ReadonlyErr("Map is read-only")
        self._caseInsensitive = val

    def getChecked(self, key, checked=True):
        """Get value, throw UnknownKeyErr if not found and checked=True"""
        if key in self:
            return self[key]
        if checked:
            from .Err import UnknownKeyErr
            raise UnknownKeyErr(f"Key not found: {key}")
        return None

    def toImmutable(self):
        """Return immutable copy, preserving type information.
        If already immutable, returns self.
        Note: Handles case where transpiler incorrectly calls Map.toImmutable on a List.
        """
        from .ObjUtil import ObjUtil

        # Handle transpiler bug: Map.toImmutable called on a List
        # This happens due to incorrect method dispatch in generated code
        from .List import List, ImmutableList
        if isinstance(self, (list, ImmutableList)) and not isinstance(self, Map):
            return List.toImmutable(self)

        # If already immutable, return self
        if self._ro and hasattr(self, '_immutable') and self._immutable:
            return self

        result = Map()
        result._ro = True
        result._immutable = True

        # Preserve type information
        if hasattr(self, '_mapType'):
            result._mapType = self._mapType
        if hasattr(self, '_keyType'):
            result._keyType = self._keyType
        if hasattr(self, '_valueType'):
            result._valueType = self._valueType
        if hasattr(self, '_def'):
            result._def = self._def
        # Preserve ordered and caseInsensitive flags
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive

        # Make values immutable too
        for k, v in self.items():
            dict.__setitem__(result, k, ObjUtil.toImmutable(v))

        return result

    def isImmutable(self):
        """Check if truly immutable (not just read-only view).

        In Fantom:
        - ro() creates a read-only VIEW - NOT immutable (reflects source changes)
        - toImmutable() creates a truly immutable COPY
        """
        return getattr(self, '_immutable', False)

    @staticmethod
    def with_(m, f):
        """Apply it-block closure to map and return map.
        Fantom: [K:V][:] { it.ordered = true }
        """
        # Call the closure with the map as argument
        f(m)
        return m

    def toCode(self):
        """Return code representation with type signature prefix"""
        from .ObjUtil import ObjUtil
        # Get type signature
        mapType = self.typeof()
        if hasattr(mapType, 'signature'):
            typeSig = mapType.signature()
        else:
            typeSig = "[sys::Obj:sys::Obj?]"

        if len(self) == 0:
            return f"{typeSig}[:]"

        # Format items with proper code representation
        items = []
        for k, v in self.items():
            kStr = ObjUtil.toStr(k) if not isinstance(k, str) else f'"{k}"' if '"' not in k else repr(k)
            vStr = ObjUtil.toCode(v) if hasattr(ObjUtil, 'toCode') else ObjUtil.toStr(v)
            items.append(f"{kStr}:{vStr}")
        return f"{typeSig}[" + ", ".join(items) + "]"

    def setList(self, list_val, f=None):
        """Set entries from list using optional key transform"""
        if f is None:
            for v in list_val:
                self[v] = v
        else:
            param_count = Map._get_param_count(f)
            for i, v in enumerate(list_val):
                if param_count >= 2:
                    k = f(v, i)
                else:
                    k = f(v)
                self[k] = v
        return self

    def addList(self, list_val, f=None):
        """Add entries from list using optional key transform"""
        if f is None:
            for v in list_val:
                if v in self:
                    from .Err import ArgErr
                    raise ArgErr(f"Key already exists: {v}")
                self[v] = v
        else:
            param_count = Map._get_param_count(f)
            for i, v in enumerate(list_val):
                if param_count >= 2:
                    k = f(v, i)
                else:
                    k = f(v)
                if k in self:
                    from .Err import ArgErr
                    raise ArgErr(f"Key already exists: {k}")
                self[k] = v
        return self

    def addNotNull(self, key, val):
        """Add entry only if value is not null"""
        if val is not None:
            self[key] = val
        return self

    def setNotNull(self, key, val):
        """Set entry only if value is not null"""
        if val is not None:
            self[key] = val
        return self

    def findNotNull(self):
        """Return map with non-null values only, with non-nullable value type"""
        from .Type import Type, MapType

        result = Map()
        # Preserve type information, making value type non-nullable
        result._keyType = self._keyType
        if self._valueType is not None and hasattr(self._valueType, 'toNonNullable'):
            result._valueType = self._valueType.toNonNullable()
        else:
            result._valueType = self._valueType
        # Create new MapType with non-nullable value type
        if result._keyType is not None and result._valueType is not None:
            result._mapType = MapType(result._keyType, result._valueType)
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive

        for k, v in self.items():
            if v is not None:
                result[k] = v
        return result

    def trap(self, name, args=None):
        """Dynamic method dispatch"""
        if hasattr(self, name):
            method = getattr(self, name)
            if callable(method):
                if args:
                    return method(*args)
                return method()
        raise AttributeError(f"Unknown slot: {name}")

    def typeof(self):
        """Return Fantom Type for Map"""
        from .Type import Type, MapType
        # If we have stored MapType, use it
        if hasattr(self, '_mapType') and self._mapType is not None:
            return self._mapType
        # Otherwise return generic Map type
        return Type.find("sys::Map")


class ReadOnlyMap(Map):
    """Read-only view of a Map - throws ReadonlyErr on modification"""

    def __init__(self, source):
        """Create read-only view of source map"""
        super().__init__(source)
        self._source = source
        self._ro = True
        # Copy metadata from source
        self._keyType = source._keyType
        self._valueType = source._valueType
        self._mapType = source._mapType
        self._ordered = source._ordered
        self._caseInsensitive = source._caseInsensitive
        self._def = source._def

    def _checkModify(self):
        """Throw ReadonlyErr if trying to modify"""
        from .Err import ReadonlyErr
        raise ReadonlyErr("Map is read-only")

    def __setitem__(self, key, value):
        self._checkModify()

    def __delitem__(self, key):
        self._checkModify()

    def set(self, key, val):
        self._checkModify()

    def add(self, key, val):
        self._checkModify()

    def clear(self):
        self._checkModify()

    def remove(self, key):
        self._checkModify()

    def setAll(self, other):
        self._checkModify()

    def addAll(self, other):
        self._checkModify()

    def setList(self, list_val, f=None):
        self._checkModify()

    def addList(self, list_val, f=None):
        self._checkModify()

    def addNotNull(self, key, val):
        self._checkModify()

    def setNotNull(self, key, val):
        self._checkModify()

    def getOrAdd(self, key, valFunc):
        """Get value - if not present and RO, throw instead of adding"""
        if key in self:
            return self[key]
        self._checkModify()

    @property
    def ordered(self):
        return self._ordered

    @ordered.setter
    def ordered(self, val):
        self._checkModify()

    @property
    def caseInsensitive(self):
        return self._caseInsensitive

    @caseInsensitive.setter
    def caseInsensitive(self, val):
        self._checkModify()

    @property
    def def_(self):
        return self._def

    @def_.setter
    def def_(self, val):
        self._checkModify()

    def isRO(self):
        return True

    def isRW(self):
        return False

    def ro(self):
        return self

    def rw(self):
        """Return mutable copy"""
        result = Map(self)
        result._keyType = self._keyType
        result._valueType = self._valueType
        result._mapType = self._mapType
        result._ordered = self._ordered
        result._caseInsensitive = self._caseInsensitive
        result._def = self._def
        result._ro = False
        return result
