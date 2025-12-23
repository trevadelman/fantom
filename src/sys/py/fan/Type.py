#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Type(Obj):
    """Type class - Fantom type reflection"""

    # Cache of Type instances by qname for identity comparison
    _cache = {}

    # Value types
    _VAL_TYPES = {"sys::Bool", "sys::Int", "sys::Float"}
    # Generic types
    _GENERIC_TYPES = {"sys::List", "sys::Map", "sys::Func"}
    # Abstract types
    _ABSTRACT_TYPES = {"sys::Test", "sys::Obj"}
    # Final types
    _FINAL_TYPES = {"sys::Bool", "sys::Int", "sys::Float", "sys::Str", "sys::Duration"}
    # Known types (sys pod types we know about)
    _KNOWN_TYPES = {
        "sys::Obj", "sys::Num", "sys::Int", "sys::Float", "sys::Bool", "sys::Str",
        "sys::List", "sys::Map", "sys::Func", "sys::Type", "sys::Pod", "sys::Slot",
        "sys::Field", "sys::Method", "sys::Range", "sys::Duration", "sys::Void",
        "sys::Err", "sys::Test", "sys::Decimal", "sys::Buf", "sys::File", "sys::Uri",
        "sys::InStream", "sys::OutStream", "sys::DateTime", "sys::Date", "sys::Time",
        "sys::TimeZone", "sys::Locale", "sys::Env", "sys::Version", "sys::Depend",
    }
    # Base type mapping
    _BASE_TYPES = {
        "sys::Int": "sys::Num",
        "sys::Float": "sys::Num",
        "sys::Decimal": "sys::Num",
        "sys::Num": "sys::Obj",
        "sys::Enum": "sys::Obj",  # Enum extends Obj
        # Slot hierarchy
        "sys::Slot": "sys::Obj",  # Slot extends Obj
        "sys::Field": "sys::Slot",  # Field extends Slot
        "sys::Method": "sys::Slot",  # Method extends Slot
        # Stream hierarchy
        "sys::SysOutStream": "sys::OutStream",  # SysOutStream extends OutStream
        "sys::SysInStream": "sys::InStream",    # SysInStream extends InStream
        # System enums
        "sys::Weekday": "sys::Enum",
        "sys::Month": "sys::Enum",
        "sys::Endian": "sys::Enum",
        "sys::LogLevel": "sys::Enum",
        # Concurrent pod hierarchy
        "concurrent::ActorFuture": "concurrent::Future",
        "concurrent::FutureStatus": "sys::Enum",
    }

    # Known enum types - for isEnum() check
    _ENUM_TYPES = {
        "sys::Weekday", "sys::Month", "sys::Endian", "sys::LogLevel",
    }

    def __init__(self, qname="sys::Obj"):
        self._qname = qname
        self._name = qname.split("::")[-1] if "::" in qname else qname
        self._nullable = None  # Lazily created NullableType
        self._listOf = None    # Lazily created ListType
        self._emptyList = None  # Lazily created empty list
        # Reflection infrastructure (like JS af$/am$ pattern)
        self._slots_info = []  # List of Field/Method metadata added via af_/am_
        self._reflected = False  # Whether reflection has been processed
        self._slots_by_name = {}  # name -> Slot lookup
        self._slot_list = []  # All slots in order
        self._field_list = []  # All fields
        self._method_list = []  # All methods
        self._type_facets = {}  # Type-level facets dict: {'sys::Serializable': {'simple': True}}
        # Type metadata from transpiler (set via tf_)
        self._type_flags = 0  # Type flags (Mixin, Facet, Internal, etc.)
        self._mixin_types = []  # List of mixin Type qnames
        self._base_qname = None  # Base type qname from transpiler

    @staticmethod
    def of(obj):
        """Get type of object"""
        if obj is None:
            return None
        # Check for Fantom objects with typeof() method
        if hasattr(obj, 'typeof') and callable(obj.typeof):
            return obj.typeof()
        # Return cached Type instance for primitives
        if isinstance(obj, bool):
            return Type.find("sys::Bool")
        if isinstance(obj, int):
            return Type.find("sys::Int")
        if isinstance(obj, float):
            return Type.find("sys::Float")
        if isinstance(obj, str):
            return Type.find("sys::Str")
        if isinstance(obj, list):
            return Type.find("sys::List")
        if isinstance(obj, dict):
            return Type.find("sys::Map")
        # For custom objects, try to get fantom type
        if hasattr(obj, '__class__'):
            cls = obj.__class__
            # Check for module path to get pod name
            module = cls.__module__
            if module.startswith('fan.'):
                parts = module.split('.')
                if len(parts) >= 3:
                    pod = parts[1]  # e.g., 'sys', 'testSys'
                    return Type.find(f"{pod}::{cls.__name__}")
            return Type.find(f"sys::{cls.__name__}")
        return Type.find("sys::Obj")

    # Generic type parameter names
    _GENERIC_PARAM_NAMES = {"V", "K", "R", "A", "B", "C", "D", "E", "F", "G", "H", "L", "M"}

    @staticmethod
    def find(qname, checked=True):
        """Find type by qname - returns cached singleton"""
        if qname in Type._cache:
            return Type._cache[qname]

        # Check for generic parameter types like sys::V, sys::K
        if qname.startswith("sys::"):
            param_name = qname[5:]  # Remove "sys::"
            if param_name in Type._GENERIC_PARAM_NAMES:
                gpt = GenericParamType.get(param_name)
                Type._cache[qname] = gpt
                return gpt

        # Parse list types like "sys::Int[]"
        if qname.endswith("[]"):
            elem_qname = qname[:-2]
            elem_type = Type.find(elem_qname, checked)
            if elem_type is None:
                return None
            list_type = ListType(elem_type)
            Type._cache[qname] = list_type
            return list_type

        # Parse nullable types like "sys::Int?"
        if qname.endswith("?"):
            base_qname = qname[:-1]
            base_type = Type.find(base_qname, checked)
            if base_type is None:
                return None
            nullable_type = base_type.toNullable()
            Type._cache[qname] = nullable_type
            return nullable_type

        # Parse func types like "|sys::Int->sys::Void|" or "|sys::Int,sys::Str->sys::Obj|"
        if qname.startswith("|") and qname.endswith("|"):
            inner = qname[1:-1]  # Remove | delimiters
            # Find the -> separator for return type
            arrow_idx = inner.rfind("->")
            if arrow_idx >= 0:
                params_str = inner[:arrow_idx]
                ret_str = inner[arrow_idx+2:]
            else:
                # No return type means ->Void
                params_str = inner
                ret_str = "sys::Void"

            # Parse parameter types (comma-separated)
            param_types = []
            if params_str:
                # Split by comma, but be careful with nested types
                params = Type._splitParams(params_str)
                for p in params:
                    p = p.strip()
                    if p:
                        pt = Type.find(p, checked)
                        if pt is None:
                            return None
                        param_types.append(pt)

            # Parse return type
            ret_type = Type.find(ret_str, checked)
            if ret_type is None:
                return None

            func_type = FuncType(param_types, ret_type)
            Type._cache[qname] = func_type
            return func_type

        # Parse map types like "[sys::Int:sys::Str]"
        if qname.startswith("[") and qname.endswith("]"):
            inner = qname[1:-1]
            # Find the colon that separates key:value
            # Need to find colon that is NOT part of pod::type pattern
            # Look for pattern like ]:key or type]:value
            # The separator colon has :: before it (from key type) and something after
            colon_idx = -1
            i = 0
            while i < len(inner):
                if inner[i] == ':':
                    # Check if this is :: (pod separator) or : (map separator)
                    if i + 1 < len(inner) and inner[i+1] == ':':
                        # This is :: - skip both
                        i += 2
                        continue
                    else:
                        # This is the map separator
                        colon_idx = i
                        break
                i += 1
            if colon_idx > 0:
                key_qname = inner[:colon_idx]
                val_qname = inner[colon_idx+1:]
                key_type = Type.find(key_qname, checked)
                val_type = Type.find(val_qname, checked)
                if key_type is None or val_type is None:
                    return None
                map_type = MapType(key_type, val_type)
                Type._cache[qname] = map_type
                return map_type

        # For checked=false, return None for unknown sys types
        if not checked:
            pod = qname.split("::")[0] if "::" in qname else None
            if pod == "sys" and qname not in Type._KNOWN_TYPES:
                return None
            # For non-sys pods, we don't know them - return None
            if pod and pod != "sys" and not qname.startswith("testSys::"):
                return None

        t = Type(qname)
        Type._cache[qname] = t

        # Try to import the module to trigger tf_() metadata registration
        # This ensures that Type.find('pod::Name') has proper type flags
        if "::" in qname:
            parts = qname.split("::")
            if len(parts) == 2:
                pod, name = parts
                try:
                    module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                    # The import triggers the class definition which calls tf_()
                except ImportError:
                    # For util:: types, try to find them in sys namespace
                    if pod == "util":
                        try:
                            module = __import__(f'fan.sys.{name}', fromlist=[name])
                        except ImportError:
                            pass

        return t

    def name(self):
        return self._name

    def qname(self):
        return self._qname

    def signature(self):
        """Return signature string"""
        return self._qname

    def pod(self):
        """Return Pod object for this type"""
        from .Pod import Pod
        if "::" in self._qname:
            pod_name = self._qname.split("::")[0]
            return Pod.find(pod_name)
        return Pod.find("sys")

    def base(self):
        """Return base type"""
        # First check transpiler-provided base type
        if self._base_qname is not None:
            return Type.find(self._base_qname)
        if self._qname in Type._BASE_TYPES:
            return Type.find(Type._BASE_TYPES[self._qname])
        # Check if this is an enum by looking up the class
        if self.isEnum():
            return Type.find("sys::Enum")
        # Check if this is an Err subclass
        if self._qname != "sys::Err" and self.isErr():
            # Find the immediate parent Err type
            return self._findErrBase()
        return Type.find("sys::Obj")

    def isErr(self):
        """Check if this type is Err or an Err subclass"""
        if self._qname == "sys::Err":
            return True
        # Try to import the class and check if it extends Err
        try:
            if "::" in self._qname:
                parts = self._qname.split("::")
                if len(parts) == 2:
                    pod, name = parts
                    # Try importing the class
                    module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                    cls = getattr(module, name, None)
                    if cls is not None:
                        from .Err import Err
                        if isinstance(cls, type) and issubclass(cls, Err):
                            return True
                    # Try importing from Err module for sys Err subclasses
                    if pod == "sys":
                        try:
                            module = __import__('fan.sys.Err', fromlist=[name])
                            cls = getattr(module, name, None)
                            if cls is not None:
                                from .Err import Err
                                if isinstance(cls, type) and issubclass(cls, Err):
                                    return True
                        except:
                            pass
        except:
            pass
        return False

    def _findErrBase(self):
        """Find the immediate Err parent type for an Err subclass"""
        try:
            if "::" in self._qname:
                parts = self._qname.split("::")
                if len(parts) == 2:
                    pod, name = parts
                    cls = None
                    # Try importing the class
                    try:
                        module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                        cls = getattr(module, name, None)
                    except:
                        pass
                    # Try importing from Err module for sys Err subclasses
                    if cls is None and pod == "sys":
                        try:
                            module = __import__('fan.sys.Err', fromlist=[name])
                            cls = getattr(module, name, None)
                        except:
                            pass
                    if cls is not None:
                        from .Err import Err
                        # Walk up the MRO to find the immediate Err parent
                        for parent in cls.__mro__[1:]:
                            if parent is Err:
                                return Type.find("sys::Err")
                            if isinstance(parent, type) and issubclass(parent, Err) and parent is not Err:
                                # Found an intermediate Err subclass
                                parent_module = parent.__module__
                                parent_name = parent.__name__
                                if parent_module.startswith('fan.'):
                                    parent_pod = parent_module.split('.')[1]
                                    return Type.find(f"{parent_pod}::{parent_name}")
        except:
            pass
        return Type.find("sys::Err")

    def make(self, args=None):
        """Create instance - supports constructor args.

        Args:
            args: Optional list of arguments to pass to constructor.
                  For types with |This| factory constructors, this can
                  include functions that modify the instance.

        Returns:
            New instance of this type
        """
        # Handle primitive types
        if self._qname == "sys::Bool":
            return False
        if self._qname == "sys::Int":
            return 0
        if self._qname == "sys::Float":
            return 0.0
        if self._qname == "sys::Str":
            return ""
        if self._qname == "sys::Duration":
            from .Duration import Duration
            return Duration.defVal()
        if self._qname == "sys::Date":
            from .DateTime import Date
            return Date.defVal()
        if self._qname == "sys::DateTime":
            from .DateTime import DateTime
            return DateTime.defVal()
        if self._qname == "sys::Time":
            from .DateTime import Time
            return Time.defVal()

        # Try to import and instantiate the class
        if "::" in self._qname:
            parts = self._qname.split("::")
            if len(parts) == 2:
                pod, name = parts
                cls = None
                try:
                    module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                    cls = getattr(module, name, None)
                except ImportError:
                    # For util:: types, try to find them in sys namespace
                    if pod == "util":
                        try:
                            module = __import__(f'fan.sys.{name}', fromlist=[name])
                            cls = getattr(module, name, None)
                        except ImportError:
                            pass

                if cls is not None:
                    # If args provided, call make() with them
                    if args is not None and hasattr(cls, 'make'):
                        # Get unwrapped args (from cvar if needed)
                        unwrapped_args = []
                        if hasattr(args, '__iter__') and not isinstance(args, str):
                            for arg in args:
                                if hasattr(arg, '_val'):
                                    unwrapped_args.append(arg._val)
                                else:
                                    unwrapped_args.append(arg)
                        else:
                            unwrapped_args = [args]

                        # Call make with args
                        return cls.make(*unwrapped_args)
                    elif hasattr(cls, 'make'):
                        return cls.make()
                    else:
                        return cls()

        return None

    def fits(self, that):
        """Check if this type fits (is subtype of) that type"""
        return self.is_(that)

    def is_(self, that):
        """Check if this type is assignable to that type"""
        # Handle nullable
        if isinstance(that, NullableType):
            that = that._root
        if self._qname == that._qname:
            return True
        # Void is special - doesn't fit anything except itself
        if self._qname == "sys::Void" or that._qname == "sys::Void":
            return False
        # Everything fits Obj
        if that._qname == "sys::Obj":
            return True
        # Check inheritance chain
        for t in self.inheritance():
            if t._qname == that._qname:
                return True
        # Check mixins (this type implements the mixin)
        for m in self.mixins():
            if m._qname == that._qname:
                return True
            # Also check mixin's inheritance (transitive mixins)
            if m.is_(that):
                return True
        return False

    # Nullable support
    def isNullable(self):
        return False

    def toNullable(self):
        """Return nullable version of this type"""
        if self._nullable is None:
            self._nullable = NullableType(self)
        return self._nullable

    def toNonNullable(self):
        """Return non-nullable version of this type"""
        return self

    # Generic/List/Map support
    def toListOf(self):
        """Return list type with this as element type (e.g., Int -> Int[])"""
        if self._listOf is None:
            self._listOf = ListType(self)
            # Cache it so Type.find returns the same instance
            Type._cache[self._listOf.signature()] = self._listOf
        return self._listOf

    def isGenericType(self):
        return False

    def isGenericInstance(self):
        return False

    def isGenericParameter(self):
        return False

    def isImmutable(self):
        """Types are always immutable"""
        return True

    def toImmutable(self):
        """Types are already immutable, return self"""
        return self

    def toStr(self):
        return self.signature()

    def toLocale(self):
        """Return locale string for type - same as signature for now"""
        return self.signature()

    # Type flags
    def isVal(self):
        """Check if value type (Bool, Int, Float)"""
        base = self.toNonNullable()
        return base._qname in Type._VAL_TYPES

    def isAbstract(self):
        return self._qname in Type._ABSTRACT_TYPES

    def isClass(self):
        return not self.isMixin() and not self.isEnum()

    def isEnum(self):
        # Check if this is a known enum type
        if self._qname in Type._ENUM_TYPES:
            return True
        # Check if base is Enum (for non-sys enums like testSys::EnumAbc)
        if self._qname in Type._BASE_TYPES:
            return Type._BASE_TYPES[self._qname] == "sys::Enum"
        # Check by trying to import the class and see if it extends Enum
        try:
            if "::" in self._qname:
                parts = self._qname.split("::")
                if len(parts) == 2:
                    pod, name = parts
                    # Try importing the class
                    module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                    cls = getattr(module, name, None)
                    if cls is not None:
                        # Check if it has _make_enum (our transpiled enums do)
                        if hasattr(cls, '_make_enum') and hasattr(cls, 'vals'):
                            return True
                        # Check if parent is Enum
                        from .Enum import Enum
                        if issubclass(cls, Enum):
                            return True
        except:
            pass
        return False

    def isFacet(self):
        """Check if this type is a facet. Uses transpiler flags if available."""
        # Check transpiler-provided flag (0x80000 = Facet)
        if self._type_flags & 0x80000:
            return True
        return False

    def isFinal(self):
        return self._qname in Type._FINAL_TYPES

    def isInternal(self):
        """Check if this type is internal. Uses transpiler flags if available."""
        # Check transpiler-provided flag (0x8 = Internal)
        if self._type_flags & 0x00000008:
            return True
        return False

    def isMixin(self):
        """Check if this type is a mixin. Uses transpiler flags if available."""
        # Check transpiler-provided flag (0x20000 = Mixin)
        if self._type_flags & 0x20000:
            return True
        return False

    # Known const types in sys - these are always immutable (const class in Fantom)
    _CONST_TYPES = {
        "sys::DateTime", "sys::Duration", "sys::Date", "sys::Time", "sys::TimeZone",
        "sys::Uri", "sys::Version", "sys::Uuid", "sys::Unit", "sys::MimeType", "sys::Locale",
        "sys::Type", "sys::Pod", "sys::Method", "sys::Field", "sys::Slot", "sys::Param",
        "sys::Depend", "sys::Range", "sys::Regex", "sys::Str", "sys::Bool", "sys::Int",
        "sys::Float", "sys::Decimal", "sys::Num",
    }

    def isConst(self):
        """Check if this type is a const class (immutable).

        Const classes are always immutable. This checks:
        1. Transpiler-provided flag (0x00000002 = Const per FConst.js)
        2. Known const types in sys (for hand-written runtime classes)
        """
        # Check transpiler-provided flag (0x00000002 = Const per FConst.js)
        if self._type_flags & 0x00000002:
            return True
        # For hand-written sys types, check known const types
        return self._qname in Type._CONST_TYPES

    def isPublic(self):
        """Check if this type is public."""
        # Internal means not public
        return not self.isInternal()

    def isSynthetic(self):
        return "$" in self._name

    def isGeneric(self):
        """Check if this is a generic type (List, Map, Func)"""
        return self._qname in Type._GENERIC_TYPES

    # Reflection - mixins, inheritance
    def mixins(self):
        """Return list of mixin types from transpiler metadata."""
        from .List import List as FanList
        # Convert stored qnames to Type objects
        result = []
        for qname in self._mixin_types:
            t = Type.find(qname, False)
            if t is not None:
                result.append(t)
        return FanList.fromLiteral(result, "sys::Type").toImmutable()

    def inheritance(self):
        """Return inheritance chain from this type to Obj, including mixins.

        Follows the JS pattern from Type.js#buildInheritance:
        1. Add self
        2. Add base class's inheritance chain
        3. Add each mixin's inheritance chain
        """
        from .List import List as FanList

        # Handle Void as special case
        if self._qname == "sys::Void":
            return FanList.fromLiteral([self], "sys::Type").toImmutable()

        seen = {self._qname}
        result = [self]

        # Add base class inheritance (recursively gets all base classes)
        base = self.base()
        if base is not None and base._qname != self._qname:
            for t in base.inheritance():
                if t._qname not in seen:
                    seen.add(t._qname)
                    result.append(t)

        # Add mixin inheritance (each mixin's full inheritance chain)
        for mixin in self.mixins():
            for t in mixin.inheritance():
                if t._qname not in seen:
                    seen.add(t._qname)
                    result.append(t)

        return FanList.fromLiteral(result, "sys::Type").toImmutable()

    # Generic type support
    def params(self):
        """Return generic parameters map - empty by default, always read-only"""
        from .Map import Map
        return Map.fromLiteral([], [], "sys::Str", "sys::Type").toImmutable()

    def parameterize(self, params):
        """Create parameterized type from parameter map.

        Args:
            params: Map of param name (Str) to Type, e.g., {"V": Bool#}

        Returns:
            Parameterized type (e.g., Bool[]# for List with V=Bool)
        """
        from .Err import UnsupportedErr, ArgErr

        # Handle Map (the params argument)
        if hasattr(params, '_data'):
            params = params._data
        elif hasattr(params, 'items'):
            pass  # Already a dict-like
        else:
            params = dict(params)

        # Only List, Map, Func support parameterization
        if self._qname == "sys::List":
            # List requires V parameter
            v_type = params.get("V")
            if v_type is None:
                raise ArgErr.make("List.parameterize requires 'V' parameter")
            # Validate no extra params
            for key in params:
                if key != "V":
                    raise ArgErr.make(f"Unknown parameter '{key}' for List")
            return v_type.toListOf()

        elif self._qname == "sys::Map":
            # Map requires K and V parameters
            k_type = params.get("K")
            v_type = params.get("V")
            if k_type is None:
                raise ArgErr.make("Map.parameterize requires 'K' parameter")
            if v_type is None:
                raise ArgErr.make("Map.parameterize requires 'V' parameter")
            # Validate no extra params
            for key in params:
                if key not in ("K", "V"):
                    raise ArgErr.make(f"Unknown parameter '{key}' for Map")
            map_type = MapType(k_type, v_type)
            Type._cache[map_type.signature()] = map_type
            return map_type

        elif self._qname == "sys::Func":
            # Func requires R (return), optionally A, B, C, etc for params
            r_type = params.get("R")
            if r_type is None:
                raise ArgErr.make("Func.parameterize requires 'R' parameter")

            # Collect param types in order A, B, C, D, E, F, G, H
            param_types = []
            param_names = ["A", "B", "C", "D", "E", "F", "G", "H"]
            for name in param_names:
                if name in params:
                    param_types.append(params[name])
                else:
                    break  # Stop at first missing param

            # Validate no unknown params
            valid_params = set(param_names) | {"R"}
            for key in params:
                if key not in valid_params:
                    raise ArgErr.make(f"Unknown parameter '{key}' for Func")

            func_type = FuncType(param_types, r_type)
            Type._cache[func_type.signature()] = func_type
            return func_type

        raise UnsupportedErr.make("parameterize not supported on " + self._qname)

    def emptyList(self):
        """Return empty immutable list of this type (e.g., Str.emptyList returns Str[])"""
        if self._emptyList is None:
            from .List import List as FanList
            # Create empty list with this type as element type
            self._emptyList = FanList.fromLiteral([], self._qname).toImmutable()
        return self._emptyList

    #########################################################################
    # Slot Reflection - Dynamic Discovery for Hand-Written Sys Types
    #########################################################################

    # Hand-written sys types that use dynamic reflection (not transpiler-generated)
    _SYS_TYPES = {
        "sys::Int", "sys::Str", "sys::Bool", "sys::Float", "sys::List",
        "sys::Map", "sys::Range", "sys::Duration", "sys::Obj", "sys::Num",
        "sys::Decimal", "sys::Uri", "sys::Regex", "sys::Version", "sys::Uuid",
        "sys::DateTime", "sys::Date", "sys::Time", "sys::TimeZone", "sys::Month",
        "sys::Weekday", "sys::Endian", "sys::LogLevel", "sys::Buf", "sys::InStream",
        "sys::OutStream", "sys::File", "sys::Locale", "sys::Env", "sys::Depend",
        "sys::MimeType", "sys::Unit", "sys::Log", "sys::Err", "sys::Func",
        "sys::Type", "sys::Pod", "sys::Slot", "sys::Field", "sys::Method", "sys::Param",
        "sys::Test", "sys::Enum",
    }

    # Known static const fields in sys types - these are NOT methods
    # In Python they're implemented as @staticmethod functions, but in Fantom they're fields
    _SYS_CONST_FIELDS = {
        "sys::Float": {"pi", "e", "posInf", "negInf", "nan"},
        "sys::Int": {"maxVal", "minVal", "defVal"},
        "sys::Duration": {"defVal", "minVal", "maxVal"},
        "sys::Str": {"defVal"},
        "sys::Bool": {"defVal"},
    }

    def _discover_sys_metadata(self):
        """Dynamically discover metadata for hand-written sys types.

        Uses Python's inspect module to scan the runtime class for:
        - Static methods (become Fantom static methods)
        - Method signatures and parameters

        This matches the JavaScript transpiler pattern where hand-written
        sys types don't have explicit metadata registration.

        Returns:
            List of discovered Method/Field objects
        """
        # Handle generic types specially - they need proper generic param types
        if self._qname == "sys::List":
            return self._list_metadata()
        if self._qname == "sys::Map":
            return self._map_metadata()
        if self._qname == "sys::Obj":
            return self._obj_metadata()
        if self._qname == "sys::Func":
            return self._func_metadata()

        # Only for sys pod hand-written types
        if self._qname not in Type._SYS_TYPES:
            return []

        # Don't re-discover if we already have slots registered via af_/am_
        if self._slots_info:
            return []

        # Import the Python runtime class
        type_name = self._name
        py_class = None

        # Try different import paths (generated vs source directory)
        for module_path in [f'fan.sys.{type_name}', f'fan.{type_name}']:
            try:
                module = __import__(module_path, fromlist=[type_name])
                py_class = getattr(module, type_name, None)
                if py_class is not None:
                    break
            except ImportError:
                continue

        if py_class is None:
            return []

        discovered = []
        import inspect

        # Get known const fields for this type (these should NOT be discovered as methods)
        const_fields = Type._SYS_CONST_FIELDS.get(self._qname, set())

        # Discover static methods
        for name in dir(py_class):
            # Skip private/dunder methods
            if name.startswith('_'):
                continue

            # Skip known const fields - these are fields, not methods
            if name in const_fields:
                continue

            try:
                attr = getattr(py_class, name)
            except AttributeError:
                continue

            # Check if it's a static method
            raw_attr = inspect.getattr_static(py_class, name)
            is_static_method = isinstance(raw_attr, staticmethod)

            if is_static_method and callable(attr):
                method = self._create_method_from_function(name, attr, is_static=True)
                if method:
                    discovered.append(method)

        return discovered

    def _create_method_from_function(self, name, func, is_static=True):
        """Create a Method object from a Python function.

        Args:
            name: Method name
            func: Python function/method
            is_static: Whether this is a static method (Python @staticmethod)

        Returns:
            Method object or None if can't be created

        Note: For sys types, Python uses @staticmethod with 'self' as the first
        parameter (because we can't add methods to native Python types like str).
        From Fantom's perspective, these are INSTANCE methods, not static methods.
        We detect this pattern and treat them as instance methods in Fantom.
        """
        from .Method import Method
        from .Param import Param
        import inspect

        try:
            sig = inspect.signature(func)
        except (ValueError, TypeError):
            # Can't get signature, create method with no params
            flags = 0x0001  # Public
            if is_static:
                flags |= 0x0800  # Static
            return Method(self, name, flags, Type.find("sys::Obj"), [], {}, func)

        # Check if first param is 'self' - if so, this is an instance method
        # in Fantom terms, even though it's a Python staticmethod
        param_list = list(sig.parameters.items())
        has_self_param = len(param_list) > 0 and param_list[0][0] == 'self'

        # Determine Fantom static flag: only true if Python static AND no 'self' param
        fantom_is_static = is_static and not has_self_param

        params = []
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter - it's the instance, not a declared param
            if param_name == 'self':
                continue

            # Determine parameter type
            param_type = self._infer_param_type(param_name, param, name)

            # Check for default value
            has_default = param.default is not inspect.Parameter.empty

            params.append(Param(param_name, param_type, has_default))

        # Infer return type from method name
        returns_type = self._infer_return_type(name)

        # Build flags
        flags = 0x0001  # Public
        if fantom_is_static:
            flags |= 0x0800  # Static

        return Method(self, name, flags, returns_type, params, {}, func)

    def _infer_param_type(self, param_name, param, method_name):
        """Infer Fantom type for a parameter based on naming and context.

        Args:
            param_name: Parameter name
            param: inspect.Parameter object
            method_name: Name of the method this param belongs to

        Returns:
            Type object
        """
        import inspect

        # Check for type annotation
        if param.annotation is not inspect.Parameter.empty:
            return self._python_type_to_fantom(param.annotation)

        # Common parameter name patterns
        name_lower = param_name.lower()

        # Boolean parameters
        if name_lower in ('checked', 'inclusive', 'exclusive', 'ro', 'trimmed'):
            return Type.find("sys::Bool")

        # String parameters
        if name_lower in ('s', 'str', 'pattern', 'sep', 'delim', 'key', 'name', 'val', 'msg'):
            return Type.find("sys::Str")

        # Integer parameters
        if name_lower in ('i', 'n', 'index', 'start', 'end', 'radix', 'base', 'width',
                          'ch', 'b', 'exp', 'min', 'max', 'min_val', 'max_val', 'that'):
            return Type.find("sys::Int")

        # Float parameters
        if name_lower in ('f', 'val') and 'float' in method_name.lower():
            return Type.find("sys::Float")

        # Range parameters
        if name_lower in ('r', 'range'):
            return Type.find("sys::Range?")

        # Func/Closure parameters
        if name_lower in ('f', 'func', 'c', 'closure'):
            return Type.find("sys::Func")

        # Type parameters
        if name_lower in ('t', 'type', 'of'):
            return Type.find("sys::Type")

        # List parameters
        if name_lower in ('list', 'args'):
            return Type.find("sys::List")

        # Locale parameters
        if name_lower == 'locale':
            return Type.find("sys::Locale?")

        # TimeZone parameters
        if name_lower == 'tz':
            return Type.find("sys::TimeZone?")

        # Default to nullable Obj
        return Type.find("sys::Obj?")

    def _infer_return_type(self, method_name):
        """Infer Fantom return type from method name patterns.

        Args:
            method_name: Name of the method

        Returns:
            Type object
        """
        name = method_name.lower()

        # Boolean return patterns
        if name.startswith('is') or name.startswith('has') or name.startswith('can'):
            return Type.find("sys::Bool")
        if name in ('equals', 'contains', 'startswith', 'endswith'):
            return Type.find("sys::Bool")

        # Void return patterns
        if name in ('each', 'times', 'eachwhiletrue'):
            return Type.find("sys::Void")

        # Int return patterns
        if name in ('hash', 'compare', 'size', 'index', 'find', 'indexof',
                    'upper', 'lower', 'abs', 'min', 'max', 'clamp'):
            return Type.find("sys::Int")

        # String return patterns
        if name.startswith('to') and name != 'tofloat' and name != 'toint':
            if name in ('tostr', 'tohex', 'tocode', 'toradix', 'tochar', 'tolocale'):
                return Type.find("sys::Str")

        # Float return patterns
        if name == 'tofloat':
            return Type.find("sys::Float")

        # Int return patterns
        if name == 'toint':
            return Type.find("sys::Int")

        # Duration return patterns
        if name == 'toduration':
            return Type.find("sys::Duration")

        # DateTime return patterns
        if name == 'todatetime':
            return Type.find("sys::DateTime")

        # Type return patterns
        if name == 'typeof':
            return Type.find("sys::Type")

        # fromStr patterns (nullable)
        if name == 'fromstr':
            # Return nullable version of parent type
            return self.toNullable()

        # defVal pattern
        if name == 'defval':
            return self

        # Default based on parent type for common operations
        if name in ('plus', 'minus', 'mult', 'div', 'mod', 'negate',
                    'and', 'or', 'xor', 'not', 'shiftl', 'shiftr', 'shifta'):
            return self

        # Default to parent type for most methods
        return Type.find("sys::Obj")

    def _python_type_to_fantom(self, py_type):
        """Convert Python type annotation to Fantom Type.

        Args:
            py_type: Python type or type annotation

        Returns:
            Type object
        """
        type_map = {
            bool: "sys::Bool",
            int: "sys::Int",
            float: "sys::Float",
            str: "sys::Str",
            list: "sys::List",
            dict: "sys::Map",
            type(None): "sys::Void",
        }

        fantom_qname = type_map.get(py_type, "sys::Obj")
        return Type.find(fantom_qname)

    def _list_metadata(self):
        """Return metadata for sys::List with correct generic param types.

        List<V> has methods like:
        - get(Int): V
        - first: V?
        - last: V?
        - set(Int, V): L (this list type)
        - add(V): L (this list type)
        """
        from .Method import Method
        from .Param import Param

        V = GenericParamType.get("V")
        L = GenericParamType.get("L")  # L represents "this list type"
        V_nullable = V.toNullable()
        methods = []

        # get(Int index): V
        methods.append(Method(self, "get", 0x0001, V, [Param("index", Type.find("sys::Int"), False)], {}))
        # getSafe(Int index, V? def): V?
        methods.append(Method(self, "getSafe", 0x0001, V_nullable, [Param("index", Type.find("sys::Int"), False), Param("def", V_nullable, True)], {}))
        # first: V?
        methods.append(Method(self, "first", 0x0001, V_nullable, [], {}))
        # last: V?
        methods.append(Method(self, "last", 0x0001, V_nullable, [], {}))
        # set(Int, V): L (this list type)
        methods.append(Method(self, "set", 0x0001, L, [Param("index", Type.find("sys::Int"), False), Param("val", V, False)], {}))
        # add(V): L (this list type)
        methods.append(Method(self, "add", 0x0001, L, [Param("val", V, False)], {}))
        # insert(Int, V): L (this list type)
        methods.append(Method(self, "insert", 0x0001, L, [Param("index", Type.find("sys::Int"), False), Param("val", V, False)], {}))
        # remove(V): V?
        methods.append(Method(self, "remove", 0x0001, V_nullable, [Param("val", V, False)], {}))
        # removeAt(Int): V
        methods.append(Method(self, "removeAt", 0x0001, V, [Param("index", Type.find("sys::Int"), False)], {}))
        # size: Int
        methods.append(Method(self, "size", 0x0001, Type.find("sys::Int"), [], {}))
        # isEmpty: Bool
        methods.append(Method(self, "isEmpty", 0x0001, Type.find("sys::Bool"), [], {}))
        # contains(V): Bool
        methods.append(Method(self, "contains", 0x0001, Type.find("sys::Bool"), [Param("val", V, False)], {}))
        # index(V): Int?
        methods.append(Method(self, "index", 0x0001, Type.find("sys::Int?"), [Param("val", V, False)], {}))
        # each(|V,Int| f): Void - closure receives (val, index)
        eachFuncType = FuncType([V, Type.find("sys::Int")], Type.find("sys::Void"))
        methods.append(Method(self, "each", 0x0001, Type.find("sys::Void"), [Param("f", eachFuncType, False)], {}))

        # Additional methods used by testReflect
        # Use R for map's return element type
        R = GenericParamType.get("R")

        # map(|V,Int->R| f): R[]
        mapFuncType = FuncType([V, Type.find("sys::Int")], R)
        methods.append(Method(self, "map", 0x0001, R.toListOf(), [Param("f", mapFuncType, False)], {}))

        # flatMap(|V,Int->R[]| f): R[]
        flatMapFuncType = FuncType([V, Type.find("sys::Int")], R.toListOf())
        methods.append(Method(self, "flatMap", 0x0001, R.toListOf(), [Param("f", flatMapFuncType, False)], {}))

        return methods

    def _map_metadata(self):
        """Return metadata for sys::Map with correct generic param types.

        Map<K,V> has methods like:
        - get(K, V?): V?
        - set(K, V): M (this map type)
        """
        from .Method import Method
        from .Param import Param

        K = GenericParamType.get("K")
        V = GenericParamType.get("V")
        M = GenericParamType.get("M")  # M represents "this map type"
        V_nullable = V.toNullable()
        methods = []

        # get(K, V? def): V?
        methods.append(Method(self, "get", 0x0001, V_nullable, [Param("key", K, False), Param("def", V_nullable, True)], {}))
        # getSafe(K, V?): V?
        methods.append(Method(self, "getSafe", 0x0001, V_nullable, [Param("key", K, False), Param("def", V_nullable, True)], {}))
        # set(K, V): M (This map type)
        methods.append(Method(self, "set", 0x0001, M, [Param("key", K, False), Param("val", V, False)], {}))
        # add(K, V): M (This map type)
        methods.append(Method(self, "add", 0x0001, M, [Param("key", K, False), Param("val", V, False)], {}))
        # remove(K): V?
        methods.append(Method(self, "remove", 0x0001, V_nullable, [Param("key", K, False)], {}))
        # containsKey(K): Bool
        methods.append(Method(self, "containsKey", 0x0001, Type.find("sys::Bool"), [Param("key", K, False)], {}))
        # size: Int
        methods.append(Method(self, "size", 0x0001, Type.find("sys::Int"), [], {}))
        # isEmpty: Bool
        methods.append(Method(self, "isEmpty", 0x0001, Type.find("sys::Bool"), [], {}))
        # keys: K[]
        methods.append(Method(self, "keys", 0x0001, K.toListOf(), [], {}))
        # vals: V[]
        methods.append(Method(self, "vals", 0x0001, V.toListOf(), [], {}))
        # each(|V,K| f): Void - closure receives (val, key) - V not V?
        eachFuncType = FuncType([V, K], Type.find("sys::Void"))
        methods.append(Method(self, "each", 0x0001, Type.find("sys::Void"), [Param("f", eachFuncType, False)], {}))
        # def: V? - the default value for missing keys
        from .Field import Field
        fields = []
        fields.append(Field(self, "def", 0x0001, V_nullable, {}, None))
        return methods + fields

    def _obj_metadata(self):
        """Return metadata for sys::Obj with its slots.

        Obj has:
        - protected new make() - constructor
        - virtual Bool equals(Obj? that)
        - virtual Int compare(Obj that)
        - virtual Int hash()
        - virtual Str toStr()
        - virtual Obj? trap(Str name, Obj?[]? args := null)
        - Bool isImmutable()
        - Type typeof()
        - static Void echo(Obj? x := "")
        """
        from .Method import Method
        from .Param import Param

        methods = []

        # make(): Obj - protected constructor
        # In Fantom, make is the constructor and appears as a slot
        # Use 0x0004 (Protected) | 0x0100 (Ctor) = 0x0104
        methods.append(Method(self, "make", 0x0104, self, [], {}))

        # equals(Obj? that): Bool
        methods.append(Method(self, "equals", 0x1001, Type.find("sys::Bool"),
                              [Param("that", Type.find("sys::Obj?"), False)], {}))

        # compare(Obj that): Int
        methods.append(Method(self, "compare", 0x1001, Type.find("sys::Int"),
                              [Param("that", Type.find("sys::Obj"), False)], {}))

        # hash(): Int
        methods.append(Method(self, "hash", 0x1001, Type.find("sys::Int"), [], {}))

        # toStr(): Str
        methods.append(Method(self, "toStr", 0x1001, Type.find("sys::Str"), [], {}))

        # trap(Str name, Obj?[]? args): Obj?
        methods.append(Method(self, "trap", 0x1001, Type.find("sys::Obj?"),
                              [Param("name", Type.find("sys::Str"), False),
                               Param("args", Type.find("sys::Obj?[]?"), True)], {}))

        # isImmutable(): Bool
        methods.append(Method(self, "isImmutable", 0x0001, Type.find("sys::Bool"), [], {}))

        # toImmutable(): Obj
        methods.append(Method(self, "toImmutable", 0x0001, self, [], {}))

        # typeof(): Type
        methods.append(Method(self, "typeof", 0x0001, Type.find("sys::Type"), [], {}))

        # with(|This| f): This
        methods.append(Method(self, "with", 0x0001, self,
                              [Param("f", Type.find("sys::Func"), False)], {}))

        # echo(Obj? x): Void - static
        methods.append(Method(self, "echo", 0x0801, Type.find("sys::Void"),
                              [Param("x", Type.find("sys::Obj?"), True)], {}))

        return methods

    def _func_metadata(self):
        """Return metadata for sys::Func with its slots.

        Func has generic return type R which gets parameterized for each FuncType.
        - R call(A a := null, B b := null, ...)
        - R callList(Obj?[]? args)
        - R callOn(Obj? target, Obj?[]? args)
        - Param[] params()
        - Type returns()
        - Int arity()
        - Func bind(Obj?[] args)
        - Func retype(Type t)
        """
        from .Method import Method
        from .Param import Param

        methods = []

        # Get generic param types for parameterization
        R = GenericParamType.get("R")
        A = GenericParamType.get("A")
        B = GenericParamType.get("B")
        C = GenericParamType.get("C")
        D = GenericParamType.get("D")
        E = GenericParamType.get("E")
        F = GenericParamType.get("F")
        G = GenericParamType.get("G")
        H = GenericParamType.get("H")

        # call(...): R - virtual, takes variable args with defaults
        # Uses generic params so FuncType can parameterize them
        # Params are non-nullable generic types - nullability comes from the actual FuncType
        methods.append(Method(self, "call", 0x1001, R,
                              [Param("a", A, True),
                               Param("b", B, True),
                               Param("c", C, True),
                               Param("d", D, True),
                               Param("e", E, True),
                               Param("f", F, True),
                               Param("g", G, True),
                               Param("h", H, True)], {}))

        # callList(Obj?[]? args): R
        methods.append(Method(self, "callList", 0x1001, R,
                              [Param("args", Type.find("sys::Obj?[]?"), True)], {}))

        # callOn(Obj? target, Obj?[]? args): R
        methods.append(Method(self, "callOn", 0x1001, R,
                              [Param("target", Type.find("sys::Obj?"), False),
                               Param("args", Type.find("sys::Obj?[]?"), True)], {}))

        # params(): Param[]
        methods.append(Method(self, "params", 0x0001, Type.find("sys::Param[]"), [], {}))

        # returns(): Type
        methods.append(Method(self, "returns", 0x0001, Type.find("sys::Type"), [], {}))

        # arity(): Int
        methods.append(Method(self, "arity", 0x0001, Type.find("sys::Int"), [], {}))

        # bind(Obj?[] args): Func
        methods.append(Method(self, "bind", 0x0001, Type.find("sys::Func"),
                              [Param("args", Type.find("sys::Obj?[]"), False)], {}))

        # retype(Type t): Func
        methods.append(Method(self, "retype", 0x0001, Type.find("sys::Func"),
                              [Param("t", Type.find("sys::Type"), False)], {}))

        # typeof(): Type - inherited from Obj but included for completeness
        methods.append(Method(self, "typeof", 0x0001, Type.find("sys::Type"), [], {}))

        # toImmutable(): Func
        methods.append(Method(self, "toImmutable", 0x0001, Type.find("sys::Func"), [], {}))

        # isImmutable(): Bool
        methods.append(Method(self, "isImmutable", 0x0001, Type.find("sys::Bool"), [], {}))

        return methods

    #########################################################################
    # Slot Reflection - Metadata Registration (like JS af$/am$ pattern)
    #########################################################################

    def af_(self, name, flags, type_sig, facets=None, setter_flags=None):
        """Add field metadata (equivalent to JS af$).

        Called by transpiler-generated code to register field metadata:
          SomeType.type_().af_('fieldName', flags, 'sys::Int', {}, setter_flags)

        Args:
            name: Field name
            flags: Slot flags (FConst values) - used for field and getter
            type_sig: Type signature string (e.g., 'sys::Int', 'sys::Str?')
            facets: Optional dict of facet metadata
            setter_flags: Optional setter-specific flags (for 'public { private set }' pattern)

        Returns:
            self for method chaining
        """
        from .Field import Field
        field_type = Type.find(type_sig, False)
        if field_type is None:
            field_type = Type.find("sys::Obj")
        f = Field(self, name, flags or 0, field_type, facets or {}, setter_flags)
        self._slots_info.append(f)
        return self

    def am_(self, name, flags, returns_sig, params=None, facets=None):
        """Add method metadata (equivalent to JS am$).

        Called by transpiler-generated code to register method metadata:
          SomeType.type_().am_('methodName', flags, 'sys::Void', params, {})

        Args:
            name: Method name
            flags: Slot flags (FConst values)
            returns_sig: Return type signature string
            params: List of Param objects (or None for no params)
            facets: Optional dict of facet metadata

        Returns:
            self for method chaining
        """
        from .Method import Method
        returns_type = Type.find(returns_sig, False)
        if returns_type is None:
            returns_type = Type.find("sys::Obj")
        m = Method(self, name, flags or 0, returns_type, params or [], facets or {})
        self._slots_info.append(m)
        return self

    def tf_(self, facets, flags=0, mixins=None, base=None):
        """Add type-level facet metadata (equivalent to JS tf$).

        Called by transpiler-generated code to register type facets:
          SomeType.type_().tf_({...}, flags, ['testSys::MxA'], 'testSys::TypeB')

        Args:
            facets: Dict of facet metadata {'facet_qname': {'field': value}}
            flags: Type flags (Mixin=0x20000, Facet=0x80000, Internal=0x8)
            mixins: List of mixin qnames
            base: Base type qname (e.g., 'testSys::TypeB')

        Returns:
            self for method chaining
        """
        self._type_facets = facets or {}
        self._type_flags = flags
        self._mixin_types = mixins or []
        self._base_qname = base
        return self

    def _reflect(self):
        """Process metadata into organized slot structures (equivalent to JS doReflect$).

        This builds the slot lookup structures from:
        1. Inherited slots from base type and mixins
        2. This type's own slots from _slots_info OR dynamically discovered (for sys types)

        After calling, the type has populated:
        - _slot_list: All slots in order
        - _field_list: All fields
        - _method_list: All methods
        - _slots_by_name: name -> Slot lookup
        """
        if self._reflected:
            return self
        self._reflected = True

        from .Field import Field
        from .Method import Method

        slots = []
        slots_by_name = {}
        name_to_index = {}

        # Merge inherited slots from base type (including Obj)
        # Skip constructors - they are not inherited
        base = self.base()
        if base is not None and base._qname != self._qname:
            base._reflect()  # Ensure base is reflected
            for inherited_slot in base._slot_list:
                # Skip constructors (Ctor flag = 0x0100) - they are not inherited
                if hasattr(inherited_slot, '_flags') and (inherited_slot._flags & 0x0100):
                    continue
                self._merge_slot(inherited_slot, slots, slots_by_name, name_to_index)

        # Merge slots from mixins
        for mixin in self.mixins():
            if hasattr(mixin, '_reflect'):
                mixin._reflect()
                for inherited_slot in mixin._slot_list:
                    self._merge_slot(inherited_slot, slots, slots_by_name, name_to_index)

        # Merge in this type's own slots from _slots_info (transpiled types)
        for slot in self._slots_info:
            self._merge_slot(slot, slots, slots_by_name, name_to_index)

        # For hand-written sys types, dynamically discover methods
        # Only if no slots were registered via af_/am_ (transpiler pattern)
        if not self._slots_info and self._qname in Type._SYS_TYPES:
            discovered_slots = self._discover_sys_metadata()
            for slot in discovered_slots:
                self._merge_slot(slot, slots, slots_by_name, name_to_index)

        # Break out into fields and methods
        fields = []
        methods = []
        for slot in slots:
            if isinstance(slot, Field):
                fields.append(slot)
            elif isinstance(slot, Method):
                methods.append(slot)

        # Store results
        self._slot_list = slots
        self._field_list = fields
        self._method_list = methods
        self._slots_by_name = slots_by_name

        return self

    def _merge_slot(self, slot, slots, slots_by_name, name_to_index):
        """Merge a slot into the slot lists, handling overrides."""
        name = slot.name()
        existing_idx = name_to_index.get(name)

        if existing_idx is not None:
            # Slot with this name already exists - this is an override
            # Replace the existing slot with the new one
            slots_by_name[name] = slot
            slots[existing_idx] = slot
        else:
            # New slot - add it
            slots_by_name[name] = slot
            slots.append(slot)
            name_to_index[name] = len(slots) - 1

    #########################################################################
    # Slot Reflection - Lookup Methods
    #########################################################################

    def slots(self):
        """Return all slots as a read-only list."""
        self._reflect()
        from .List import List as FanList
        return FanList.fromLiteral(self._slot_list, "sys::Slot").toImmutable()

    def slot(self, name, checked=True):
        """Find slot by name.

        Args:
            name: Slot name to find
            checked: If True, raise UnknownSlotErr if not found

        Returns:
            Slot instance or None (if checked=False and not found)
        """
        self._reflect()
        slot = self._slots_by_name.get(name)
        if slot is not None:
            return slot
        if checked:
            from .Err import UnknownSlotErr
            raise UnknownSlotErr.make(f"{self._qname}.{name}")
        return None

    def fields(self):
        """Return all fields as a read-only list."""
        self._reflect()
        from .List import List as FanList
        return FanList.fromLiteral(self._field_list, "sys::Field").toImmutable()

    def field(self, name, checked=True):
        """Find field by name.

        Args:
            name: Field name to find
            checked: If True, raise UnknownSlotErr if not found

        Returns:
            Field instance or None (if checked=False and not found)
        """
        from .Field import Field
        slot = self.slot(name, checked)
        if slot is None:
            return None
        if isinstance(slot, Field):
            return slot
        if checked:
            from .Err import UnknownSlotErr
            raise UnknownSlotErr.make(f"{self._qname}.{name} is not a field")
        return None

    def methods(self):
        """Return all methods as a read-only list."""
        self._reflect()
        from .List import List as FanList
        return FanList.fromLiteral(self._method_list, "sys::Method").toImmutable()

    def method(self, name, checked=True):
        """Find method by name.

        Args:
            name: Method name to find
            checked: If True, raise UnknownSlotErr if not found

        Returns:
            Method instance or None (if checked=False and not found)
        """
        from .Method import Method
        slot = self.slot(name, checked)
        if slot is None:
            return None
        if isinstance(slot, Method):
            return slot
        if checked:
            from .Err import UnknownSlotErr
            raise UnknownSlotErr.make(f"{self._qname}.{name} is not a method")
        return None

    def hasFacet(self, facetType):
        """Check if this type has a facet.

        Args:
            facetType: Type of facet to check for

        Returns:
            True if facet is present, False otherwise
        """
        facet_qname = facetType.qname() if hasattr(facetType, 'qname') else str(facetType)
        return facet_qname in self._type_facets

    def facet(self, facetType, checked=True):
        """Get facet value.

        Args:
            facetType: Type of facet to get
            checked: If True, raise error if not found

        Returns:
            Facet instance or None
        """
        facet_qname = facetType.qname() if hasattr(facetType, 'qname') else str(facetType)
        if facet_qname in self._type_facets:
            facet_data = self._type_facets[facet_qname]

            # For marker facets (no values), return the singleton defVal() instance
            # This ensures identity equality: type.facet(FacetM1#) === FacetM1.defVal()
            if not facet_data:
                # Try to import the facet class and get defVal()
                try:
                    parts = facet_qname.split("::")
                    if len(parts) == 2:
                        pod, name = parts
                        module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                        cls = getattr(module, name, None)
                        if cls is not None and hasattr(cls, 'defVal'):
                            return cls.defVal()
                except:
                    pass
                # Fallback to FacetInstance
                return FacetInstance(facetType, facet_data)

            # For facets with values, create an instance with the stored values
            return FacetInstance(facetType, facet_data)
        if checked:
            from .Err import UnknownFacetErr
            raise UnknownFacetErr.make(f"Facet not found: {facetType}")
        return None

    def facets(self):
        """Return list of all facets.

        Returns:
            Immutable List of Facet instances
        """
        from .List import List as FanList
        result = []
        for facet_qname, facet_data in self._type_facets.items():
            # Use checked=True to create the type even if not in KNOWN_TYPES
            facet_type = Type.find(facet_qname, True)
            result.append(FacetInstance(facet_type, facet_data))
        # Return immutable Fantom List with Facet element type
        return FanList.fromLiteral(result, "sys::Facet").toImmutable()

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, Type):
            return self.signature() == other.signature()
        return False

    def equals(self, other):
        """Fantom equals method - delegates to __eq__"""
        return self.__eq__(other)

    def __hash__(self):
        return hash(self.signature())

    def __repr__(self):
        return f"Type({self._qname})"

    @staticmethod
    def _splitParams(s):
        """Split comma-separated parameter types, handling nested generics"""
        result = []
        depth = 0
        current = ""
        for ch in s:
            if ch in "|[":
                depth += 1
                current += ch
            elif ch in "|]":
                depth -= 1
                current += ch
            elif ch == "," and depth == 0:
                result.append(current)
                current = ""
            else:
                current += ch
        if current:
            result.append(current)
        return result


class NullableType(Type):
    """Nullable wrapper for a type - adds ? suffix"""

    def __init__(self, root):
        super().__init__(root._qname + "?")
        self._root = root

    @property
    def root(self):
        return self._root

    def name(self):
        return self._root.name()

    def qname(self):
        return self._root.qname()

    def signature(self):
        return f"{self._root.signature()}?"

    def pod(self):
        return self._root.pod()

    def base(self):
        return self._root.base()

    def isNullable(self):
        return True

    def toNullable(self):
        return self

    def toNonNullable(self):
        return self._root

    def is_(self, that):
        return self._root.is_(that)

    def fits(self, that):
        return self._root.fits(that)

    def isGenericParameter(self):
        return self._root.isGenericParameter()

    def isVal(self):
        return self._root.isVal()

    def toListOf(self):
        """Return list type with this as element type"""
        return ListType(self)


class ListType(Type):
    """List type with element type - e.g., Int[] or Str[]"""

    def __init__(self, v):
        """v is the element type (value type)"""
        self._v = v
        sig = f"{v.signature()}[]"
        super().__init__(sig)

    @property
    def v(self):
        """Element type"""
        return self._v

    def signature(self):
        return f"{self._v.signature()}[]"

    def name(self):
        return "List"

    def qname(self):
        return "sys::List"

    def pod(self):
        from .Pod import Pod
        return Pod.find("sys")

    def base(self):
        return Type.find("sys::List")

    def isNullable(self):
        return False

    def toNullable(self):
        if self._nullable is None:
            self._nullable = NullableType(self)
        return self._nullable

    def toNonNullable(self):
        return self

    def isGenericInstance(self):
        return True

    def params(self):
        """Return generic parameters map for List<V>: {V: elem_type, L: this}"""
        from .Map import Map
        return Map.fromLiteral(["V", "L"], [self._v, self], "sys::Str", "sys::Type").toImmutable()

    def is_(self, that):
        """Check if this list type is assignable to that type"""
        if isinstance(that, NullableType):
            that = that._root

        if isinstance(that, ListType):
            # List types match if element types match
            if that._v.qname() == "sys::Obj":
                return True
            return self._v.is_(that._v)

        if isinstance(that, Type):
            if that.qname() == "sys::List":
                return True
            if that.qname() == "sys::Obj":
                return True

        return False

    def __eq__(self, other):
        if isinstance(other, ListType):
            return self._v == other._v
        return False

    def __hash__(self):
        return hash(self.signature())

    def method(self, name, checked=True):
        """Get method with type parameters substituted.

        When you get 'get' from Str[], returns method with:
        - Return type: Str (not V)
        """
        # Get method from base List type
        baseListType = Type.find("sys::List")
        baseMethod = baseListType.method(name, False)
        if baseMethod is None:
            if checked:
                from .Err import UnknownSlotErr
                raise UnknownSlotErr.make(f"{self.qname()}.{name}")
            return None
        # Return parameterized method wrapper (using V=elem, K=None)
        return ParameterizedListMethod(baseMethod, self._v, self)


class ParameterizedListMethod:
    """Wrapper around a generic List Method that substitutes type parameters."""

    def __init__(self, baseMethod, elemType, owner):
        self._base = baseMethod
        self._v = elemType  # V (value/element type)
        self._owner = owner

    def _substituteType(self, t):
        """Substitute V, L, and R in a type signature.

        V -> element type (value type)
        L -> this list type
        R -> Obj? (generic return type for closures, defaults to Obj?)
        """
        if t is None:
            return t

        sig = t.signature() if hasattr(t, 'signature') else str(t)

        # Check for V type parameter
        if sig == "sys::V" or sig == "V":
            return self._v
        if sig == "sys::V?" or sig == "V?":
            return self._v.toNullable() if hasattr(self._v, 'toNullable') else self._v

        # Check for L (list type itself)
        if sig == "sys::L" or sig == "L":
            return self._owner

        # Check for R (closure return type) - defaults to Obj?
        if sig == "sys::R" or sig == "R":
            return Type.find("sys::Obj?")
        if sig == "sys::R?" or sig == "R?":
            return Type.find("sys::Obj?")

        # Handle FuncType - substitute V/R in params and return type
        if isinstance(t, FuncType):
            new_params = []
            for p in t._params:
                new_params.append(self._substituteType(p))
            new_ret = self._substituteType(t._ret)
            return FuncType(new_params, new_ret)

        # Handle ListType - substitute V/R in element type
        if isinstance(t, ListType):
            new_elem = self._substituteType(t._v)
            if new_elem != t._v:
                return ListType(new_elem)
            return t

        return t

    def name(self):
        return self._base.name()

    def qname(self):
        return f"{self._owner.qname()}.{self._base.name()}"

    def returns(self):
        """Return type with V substituted"""
        baseRet = self._base.returns()
        return self._substituteType(baseRet)

    def params(self):
        """Parameters with V substituted"""
        baseParams = self._base.params()
        if baseParams is None:
            return []
        # Return wrapper params that substitute types
        return [ParameterizedListParam(p, self) for p in baseParams]

    def isStatic(self):
        return self._base.isStatic() if hasattr(self._base, 'isStatic') else False

    def isPublic(self):
        return self._base.isPublic() if hasattr(self._base, 'isPublic') else True

    def call(self, *args):
        return self._base.call(*args)


class ParameterizedListParam:
    """Wrapper around a Param that substitutes type parameters for List."""

    def __init__(self, baseParam, method):
        self._base = baseParam
        self._method = method

    def name(self):
        return self._base.name()

    def type_(self):
        """Type with V substituted"""
        baseType = self._base.type_()
        return self._method._substituteType(baseType)


class MapType(Type):
    """Map type with key and value types - e.g., [Int:Str]"""

    def __init__(self, k, v):
        """k is key type, v is value type"""
        self._k = k
        self._v = v
        sig = f"[{k.signature()}:{v.signature()}]"
        super().__init__(sig)

    @property
    def k(self):
        """Key type"""
        return self._k

    @property
    def v(self):
        """Value type"""
        return self._v

    def signature(self):
        return f"[{self._k.signature()}:{self._v.signature()}]"

    def name(self):
        return "Map"

    def qname(self):
        return "sys::Map"

    def pod(self):
        from .Pod import Pod
        return Pod.find("sys")

    def base(self):
        return Type.find("sys::Map")

    def isNullable(self):
        return False

    def toNullable(self):
        if self._nullable is None:
            self._nullable = NullableType(self)
        return self._nullable

    def toNonNullable(self):
        return self

    def isGenericInstance(self):
        return True

    def params(self):
        """Return generic parameters map for Map<K,V>: {K: key_type, V: val_type, M: this}"""
        from .Map import Map
        return Map.fromLiteral(["K", "V", "M"], [self._k, self._v, self], "sys::Str", "sys::Type").toImmutable()

    def is_(self, that):
        """Check if this map type is assignable to that type"""
        if isinstance(that, NullableType):
            that = that._root

        if isinstance(that, MapType):
            # Key types must match exactly or this key fits that key
            # Value types must match - this value fits that value
            k_fits = self._k.is_(that._k) or that._k.qname() == "sys::Obj"
            v_fits = self._v.is_(that._v) or that._v.qname() == "sys::Obj"
            return k_fits and v_fits

        if isinstance(that, Type):
            if that.qname() == "sys::Map":
                return True
            if that.qname() == "sys::Obj":
                return True

        return False

    def __eq__(self, other):
        if isinstance(other, MapType):
            return self._k == other._k and self._v == other._v
        return False

    def __hash__(self):
        return hash(self.signature())

    def method(self, name, checked=True):
        """Get method with type parameters substituted.

        When you get 'get' from [Int:Str], returns method with:
        - Return type: Str? (not V?)
        - Param types: Int, Str? (not K, V?)
        """
        # Get method from base Map type
        baseMapType = Type.find("sys::Map")
        baseMethod = baseMapType.method(name, False)
        if baseMethod is None:
            if checked:
                from .Err import UnknownSlotErr
                raise UnknownSlotErr.make(f"{self.qname()}.{name}")
            return None
        # Return parameterized method wrapper
        return ParameterizedMethod(baseMethod, self._k, self._v, self)

    def field(self, name, checked=True):
        """Get field with type parameters substituted.

        When you get 'def' from [Int:Str], returns field with:
        - Type: Str? (not V?)
        """
        # Get field from base Map type
        baseMapType = Type.find("sys::Map")
        baseField = baseMapType.field(name, False)
        if baseField is None:
            if checked:
                from .Err import UnknownSlotErr
                raise UnknownSlotErr.make(f"{self.qname()}.{name}")
            return None
        # Return parameterized field wrapper
        return ParameterizedField(baseField, self._k, self._v, self)


class ParameterizedMethod:
    """Wrapper around a generic Method that substitutes type parameters.

    Used by MapType/ListType to return methods with concrete types
    instead of generic K, V, etc.
    """

    def __init__(self, baseMethod, keyType, valType, owner):
        self._base = baseMethod
        self._k = keyType
        self._v = valType
        self._owner = owner

    def _substituteType(self, t):
        """Substitute K and V in a type signature"""
        if t is None:
            return t

        sig = t.signature() if hasattr(t, 'signature') else str(t)

        # Check for K and V type parameters
        if sig == "sys::K" or sig == "K":
            return self._k
        if sig == "sys::V" or sig == "V":
            return self._v
        if sig == "sys::K?" or sig == "K?":
            return self._k.toNullable() if hasattr(self._k, 'toNullable') else self._k
        if sig == "sys::V?" or sig == "V?":
            return self._v.toNullable() if hasattr(self._v, 'toNullable') else self._v

        # Check for M (map type itself)
        if sig == "sys::M" or sig == "M":
            return self._owner

        # Handle FuncType - substitute K/V in params and return type
        if isinstance(t, FuncType):
            new_params = []
            for p in t._params:
                new_params.append(self._substituteType(p))
            new_ret = self._substituteType(t._ret)
            return FuncType(new_params, new_ret)

        # Handle ListType - substitute K/V in element type (e.g., K[] -> Int[])
        if isinstance(t, ListType):
            new_elem = self._substituteType(t._v)
            if new_elem != t._v:
                return ListType(new_elem)
            return t

        # For other complex types, return as-is
        return t

    def name(self):
        return self._base.name()

    def qname(self):
        return f"{self._owner.qname()}.{self._base.name()}"

    def returns(self):
        """Return type with K/V substituted"""
        baseRet = self._base.returns()
        return self._substituteType(baseRet)

    def params(self):
        """Parameters with K/V substituted"""
        baseParams = self._base.params()
        if baseParams is None:
            return []
        # Return wrapper params that substitute types
        return [ParameterizedParam(p, self) for p in baseParams]

    def isStatic(self):
        return self._base.isStatic() if hasattr(self._base, 'isStatic') else False

    def isPublic(self):
        return self._base.isPublic() if hasattr(self._base, 'isPublic') else True

    def call(self, *args):
        return self._base.call(*args)


class ParameterizedParam:
    """Wrapper around a Param that substitutes type parameters."""

    def __init__(self, baseParam, method):
        self._base = baseParam
        self._method = method

    def name(self):
        return self._base.name()

    def type_(self):
        """Type with K/V substituted"""
        baseType = self._base.type_()
        return self._method._substituteType(baseType)


class ParameterizedField:
    """Wrapper around a generic Field that substitutes type parameters.

    Used by MapType to return fields with concrete types instead of K, V, etc.
    """

    def __init__(self, baseField, keyType, valType, owner):
        self._base = baseField
        self._k = keyType
        self._v = valType
        self._owner = owner

    def _substituteType(self, t):
        """Substitute K and V in a type signature"""
        if t is None:
            return t

        sig = t.signature() if hasattr(t, 'signature') else str(t)

        # Check for K and V type parameters
        if sig == "sys::K" or sig == "K":
            return self._k
        if sig == "sys::V" or sig == "V":
            return self._v
        if sig == "sys::K?" or sig == "K?":
            return self._k.toNullable() if hasattr(self._k, 'toNullable') else self._k
        if sig == "sys::V?" or sig == "V?":
            return self._v.toNullable() if hasattr(self._v, 'toNullable') else self._v

        # Check for M (map type itself)
        if sig == "sys::M" or sig == "M":
            return self._owner

        return t

    def name(self):
        return self._base.name()

    def qname(self):
        return f"{self._owner.qname()}.{self._base.name()}"

    def type_(self):
        """Type with K/V substituted"""
        baseType = self._base.type_()
        return self._substituteType(baseType)

    def isStatic(self):
        return self._base.isStatic() if hasattr(self._base, 'isStatic') else False

    def isPublic(self):
        return self._base.isPublic() if hasattr(self._base, 'isPublic') else True


class FuncType(Type):
    """Function type with parameter types and return type - e.g., |Int,Str->Bool|"""

    def __init__(self, params, ret):
        """params is list of parameter types, ret is return type"""
        self._params = params  # List of Type
        self._ret = ret  # Return Type
        sig = self._buildSignature()
        super().__init__(sig)

    def _buildSignature(self):
        """Build the function type signature like |sys::Int,sys::Str->sys::Bool|"""
        params_sig = ",".join(p.signature() for p in self._params)
        return f"|{params_sig}->{self._ret.signature()}|"

    @property
    def params(self):
        """Parameter types"""
        return self._params

    @property
    def ret(self):
        """Return type"""
        return self._ret

    def signature(self):
        return self._buildSignature()

    def name(self):
        return "Func"

    def qname(self):
        return "sys::Func"

    def pod(self):
        from .Pod import Pod
        return Pod.find("sys")

    def base(self):
        return Type.find("sys::Func")

    def isNullable(self):
        return False

    def toNullable(self):
        if self._nullable is None:
            self._nullable = NullableType(self)
        return self._nullable

    def toNonNullable(self):
        return self

    def isGenericInstance(self):
        return True

    def returns(self):
        """Alias for ret - used in FuncTest"""
        return self._ret

    def arity(self):
        """Number of parameters"""
        return len(self._params)

    def params(self):
        """Return generic parameters map for Func: {A: param0, B: param1, ..., R: return}"""
        from .Map import Map
        param_names = ["A", "B", "C", "D", "E", "F", "G", "H"]
        keys = []
        vals = []
        for i, pt in enumerate(self._params):
            if i < len(param_names):
                keys.append(param_names[i])
                vals.append(pt)
        keys.append("R")
        vals.append(self._ret)
        return Map.fromLiteral(keys, vals, "sys::Str", "sys::Type").toImmutable()

    def is_(self, that):
        """Check if this func type is assignable to that type.

        Function type fitting rules (contravariant params, covariant return):
        - |Num->Void| fits |Int->Void| because params are contravariant
          (a func accepting Num can handle Int)
        - |->Int| fits |->Num| because return is covariant
          (a func returning Int can be used where Num expected)
        - |Int a| fits |Int a, Int b| because extra target params are optional
        """
        if isinstance(that, NullableType):
            that = that._root

        if isinstance(that, FuncType):
            # Check parameter count - this can have fewer or equal params than that
            # (target can have extra params that go unused)
            if len(self._params) > len(that._params):
                return False

            # Parameters are CONTRAVARIANT: that.param must fit this.param
            # Because if target expects Int, source must accept Int or wider (Num, Obj)
            for i in range(len(self._params)):
                if not that._params[i].is_(self._params[i]):
                    return False

            # Return type is COVARIANT: this.ret must fit that.ret
            # Void return on target means we don't care about source return
            if that._ret.signature() == "sys::Void":
                return True
            # But Void return on source can't satisfy non-Void target
            if self._ret.signature() == "sys::Void":
                return False
            if not self._ret.is_(that._ret):
                return False

            return True

        if isinstance(that, Type):
            if that.qname() == "sys::Func":
                return True
            if that.qname() == "sys::Obj":
                return True

        return False

    def _reflect(self):
        """Process reflection for FuncType.

        FuncType is a generic instance - its methods need to be parameterized
        with the actual type parameters (A, B, C... for params, R for return).

        For example, |Int->Str|.method("call") should return Method with:
        - params: [Int a, ...]
        - returns: Str (not Obj?)
        """
        if self._reflected:
            return self
        self._reflected = True

        from .Method import Method
        from .Param import Param

        # Get base Func's slots
        base_func = Type.find("sys::Func")
        base_func._reflect()

        slots = []
        slots_by_name = {}
        name_to_index = {}

        # Parameterize each slot from base Func
        for base_slot in base_func._slot_list:
            if isinstance(base_slot, Method):
                slot = self._parameterize_method(base_slot)
            else:
                slot = base_slot
            self._merge_slot(slot, slots, slots_by_name, name_to_index)

        # Break out into fields and methods
        fields = []
        methods = []
        for slot in slots:
            if hasattr(slot, '_type') and isinstance(slot, type) and issubclass(slot.__class__.__name__, 'Field'):
                fields.append(slot)
            else:
                methods.append(slot)

        self._slot_list = slots
        self._field_list = fields
        self._method_list = methods
        self._slots_by_name = slots_by_name

        return self

    def _parameterize_method(self, method):
        """Parameterize a method from base Func with this FuncType's types.

        Replaces:
        - Return type R -> actual return type
        - Param types A, B, C... -> actual param types
        """
        from .Method import Method
        from .Param import Param

        # Parameterize return type
        ret = method._returns
        if ret is not None and hasattr(ret, 'isGenericParameter') and ret.isGenericParameter():
            ret = self._parameterize_type(ret)

        # Parameterize params
        new_params = []
        for p in method._params:
            p_type = p._type if hasattr(p, '_type') else None
            if p_type is not None and hasattr(p_type, 'isGenericParameter') and p_type.isGenericParameter():
                p_type = self._parameterize_type(p_type)
            new_params.append(Param(p._name, p_type, p._hasDefault if hasattr(p, '_hasDefault') else False))

        return Method(self, method._name, method._flags, ret, new_params, method._facets if hasattr(method, '_facets') else {})

    def _parameterize_type(self, t):
        """Map generic parameter type to actual type.

        R -> self._ret (return type)
        A, B, C... -> self._params[0, 1, 2...] or Obj if param doesn't exist

        For nullable types like A?, the nullability is preserved on the result.
        """
        if t is None:
            return t

        # Handle nullable types - we need to get the root to check if it's generic
        is_nullable = t.isNullable() if hasattr(t, 'isNullable') else False
        root = t
        if is_nullable and hasattr(t, 'toNonNullable'):
            root = t.toNonNullable()

        # Check if this is a generic param (sys::A, sys::B, sys::R, etc.)
        if not (hasattr(root, 'isGenericParameter') and root.isGenericParameter()):
            # Not a generic param - return as-is
            return t

        # Map generic param to actual type
        param_name = root.name() if hasattr(root, 'name') and callable(root.name) else str(root)

        if param_name == "R":
            # R maps to the func's return type
            result = self._ret
        elif param_name in "ABCDEFGH":
            # A, B, C... map to param types (if they exist)
            idx = ord(param_name) - ord("A")
            if idx < len(self._params):
                result = self._params[idx]
                # Apply original nullability to result ONLY if we found an actual param
                if is_nullable and hasattr(result, 'toNullable'):
                    return result.toNullable()
                return result
            else:
                # No such param - use Obj as fallback (without original nullability)
                # Because the fallback Obj represents "accepts anything"
                return Type.find("sys::Obj")
        else:
            return Type.find("sys::Obj")

        return result

    def __eq__(self, other):
        if isinstance(other, FuncType):
            if len(self._params) != len(other._params):
                return False
            for i in range(len(self._params)):
                if self._params[i] != other._params[i]:
                    return False
            return self._ret == other._ret
        return False

    def __hash__(self):
        return hash(self.signature())


class GenericParamType(Type):
    """Generic type parameter like V, K, A, B, etc.

    These represent the placeholder types in generic definitions:
    - List<V> has parameter V
    - Map<K,V> has parameters K and V
    - Func<A,B,C,...,R> has parameters for each arg and return

    In Fantom, these are real Type instances with qname like "sys::V"
    """

    # Singleton instances for each generic param
    _instances = {}

    def __init__(self, name):
        super().__init__(f"sys::{name}")
        self._param_name = name

    @staticmethod
    def get(name):
        """Get or create the singleton GenericParamType for a param name"""
        if name not in GenericParamType._instances:
            GenericParamType._instances[name] = GenericParamType(name)
        return GenericParamType._instances[name]

    def name(self):
        return self._param_name

    def qname(self):
        return f"sys::{self._param_name}"

    def signature(self):
        return f"sys::{self._param_name}"

    def pod(self):
        # Return the sys Pod object for identity comparison
        from .Pod import Pod
        return Pod.find("sys")

    def base(self):
        return Type.find("sys::Obj")

    def isGenericParameter(self):
        return True

    def mixins(self):
        from .List import List as FanList
        return FanList.fromLiteral([], "sys::Type").toImmutable()


class FacetInstance(Obj):
    """Runtime representation of a facet instance.

    Allows accessing facet field values via trap (->).
    E.g., type.facet(Serializable#)->simple returns true/false

    Also stores field values as _fieldName attributes to match
    how transpiled facet classes access them (e.g., facet._val).
    """

    def __init__(self, facet_type, facet_data):
        """Create a facet instance.

        Args:
            facet_type: The Type of this facet
            facet_data: Dict of field name -> value
        """
        self._facet_type = facet_type
        self._facet_data = facet_data or {}

        # Try to load the actual facet class to get default values
        # for fields not explicitly set in facet_data
        try:
            qname = facet_type.qname() if hasattr(facet_type, 'qname') else str(facet_type)
            parts = qname.split("::")
            if len(parts) == 2:
                pod, name = parts
                module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                cls = getattr(module, name, None)
                if cls is not None:
                    # Create a default instance to get field defaults
                    # Use object.__new__ to avoid constructor side effects
                    default_inst = object.__new__(cls)
                    # Initialize with super().__init__() if possible
                    try:
                        Obj.__init__(default_inst)
                    except:
                        pass
                    # Copy default field values for any _fieldName attributes
                    for attr_name in dir(cls):
                        if attr_name.startswith('_') and not attr_name.startswith('__'):
                            field_name = attr_name[1:]  # Remove leading underscore
                            if field_name not in self._facet_data:
                                try:
                                    # Get the default value from class or instance init
                                    default_val = getattr(cls, attr_name, None)
                                    if default_val is not None and not callable(default_val):
                                        setattr(self, attr_name, default_val)
                                except:
                                    pass
        except:
            pass

        # Set _fieldName attributes for each explicitly provided field
        for field_name, value in self._facet_data.items():
            setattr(self, f"_{field_name}", value)

    def typeof(self):
        """Return the facet type"""
        return self._facet_type

    def trap(self, name, args=None):
        """Dynamic field access via -> operator"""
        if args is None:
            args = []
        if name in self._facet_data:
            return self._facet_data[name]
        # Check for method-style access (no args)
        if not args:
            return self._facet_data.get(name)
        from .Err import UnknownSlotErr
        raise UnknownSlotErr.make(f"{self._facet_type}.{name}")

    def __getattr__(self, name):
        """Allow Python attribute access to facet fields"""
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        if name in self._facet_data:
            return self._facet_data[name]
        raise AttributeError(f"Facet has no field: {name}")

    def equals(self, other):
        """Check equality based on facet type"""
        if other is None:
            return False
        if isinstance(other, FacetInstance):
            return self._facet_type.qname() == other._facet_type.qname()
        return False

    def __eq__(self, other):
        return self.equals(other)

    def __hash__(self):
        return hash(self._facet_type.qname())

    def toStr(self):
        return f"@{self._facet_type.qname()}"


# Pre-populate static type$ fields for common types
# These will be set after module initialization
def _init_type_fields():
    """Initialize static type$ fields on type classes"""
    pass  # Will be called by runtime initialization
