#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


#########################################################################
# Name Conversion Helpers (Two-Pass Lookup Approach)
#########################################################################

# Python builtins that get trailing underscore in transpilation
# Used by Map.get_checked() and Type.slot() for two-pass lookup
_PYTHON_BUILTINS = {'hash', 'print', 'abs', 'min', 'max', 'set', 'map',
                    'list', 'dir', 'oct', 'open', 'vars', 'match',
                    'all', 'any', 'pow', 'round', 'type', 'id', 'and', 'or', 'not'}


def _camel_to_snake(name):
    """Convert camelCase to snake_case.

    This is a Python port of PyUtil.toSnakeCase() from the transpiler.
    Used by Type.slot() for two-pass lookup to accept both Fantom names
    (camelCase) and Python names (snake_case).

    Examples:
        fromStr -> from_str
        isEmpty -> is_empty
        XMLParser -> xml_parser
        getHTTPResponse -> get_http_response
        utf16BE -> utf16_be
    """
    # Fast path: if no uppercase, return as-is
    if not any(c.isupper() for c in name):
        return name

    result = []
    prev = ''
    for i, ch in enumerate(name):
        if ch.isupper():
            next_ch = name[i + 1] if i + 1 < len(name) else ''
            prev_is_lower = prev.islower()
            prev_is_digit = prev.isdigit()
            next_is_lower = next_ch.islower()
            # Add underscore before uppercase if:
            # 1. Previous char was lowercase (camelCase boundary): toStr -> to_str
            # 2. We're in an acronym and next char is lowercase (end of acronym): XMLParser -> xml_parser
            # 3. Previous char was a digit (number to uppercase): utf16BE -> utf16_be
            if i > 0 and (prev_is_lower or prev_is_digit or (prev.isupper() and next_is_lower)):
                result.append('_')
            result.append(ch.lower())
        else:
            result.append(ch)
        prev = ch
    return ''.join(result)


def _snake_to_camel(name):
    """Convert snake_case to camelCase.

    Used by ObjEncoder for cross-platform serialization compatibility.
    Reverses the _camel_to_snake() transformation.

    Examples:
        from_str -> fromStr
        is_empty -> isEmpty
        xml_parser -> xmlParser
        hash_ -> hash (removes Python builtin escape)
    """
    # Handle trailing underscore (Python builtin escape)
    # These are Python reserved words/builtins that got _ appended
    _PYTHON_BUILTINS = {'hash', 'print', 'abs', 'min', 'max', 'set', 'map',
                        'list', 'dir', 'oct', 'open', 'vars', 'match',
                        'all', 'any', 'pow', 'round'}
    if name.endswith('_') and name[:-1] in _PYTHON_BUILTINS:
        name = name[:-1]

    # Split by underscore and capitalize each part except first
    parts = name.split('_')
    if len(parts) == 1:
        return name
    return parts[0] + ''.join(p.capitalize() for p in parts[1:] if p)


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
        self._inheritance_cache = None  # Lazily computed inheritance chain (like JS inheritance$)
        # Reflection infrastructure (like JS af$/am$ pattern)
        self._slots_info = []  # List of Field/Method metadata added via af_/am_
        self._reflected = False  # Whether reflection has been processed
        self._slots_by_name = {}  # name -> Slot lookup
        self._slot_list = []  # All slots in order
        self._field_list = []  # All fields
        self._method_list = []  # All methods
        self._type_facets = {}  # Type-level facets dict: {'sys::Serializable': {'simple': True}}
        self._facets_list = None  # Cached list for facets() - for identity comparison
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
            # Skip Python implementation details that aren't Fantom types
            # Cvar is a helper class for closure variable wrapping
            if cls.__name__ in ('Cvar', 'CvarWrapper'):
                return None
            # Check for module path to get pod name
            module = cls.__module__
            if module.startswith('fan.'):
                parts = module.split('.')
                if len(parts) >= 3:
                    pod = parts[1]  # e.g., 'sys', 'testSys'
                    # Convert Python pod name to Fantom pod name
                    # Python uses 'def_' because 'def' is a reserved word
                    pod = Type._py_pod_to_fantom(pod)
                    return Type.find(f"{pod}::{cls.__name__}")
            return Type.find(f"sys::{cls.__name__}")
        return Type.find("sys::Obj")

    # Generic type parameter names
    _GENERIC_PARAM_NAMES = {"V", "K", "R", "A", "B", "C", "D", "E", "F", "G", "H", "L", "M"}

    # Python pod names that differ from Fantom pod names
    # Python uses trailing underscore for reserved words (e.g., 'def' -> 'def_')
    _PY_POD_TO_FANTOM = {
        "def_": "def",  # 'def' is a Python keyword
    }

    # Reverse mapping: Fantom pod name -> Python module name
    _FANTOM_POD_TO_PY = {
        "def": "def_",  # 'def' is a Python keyword
    }

    @staticmethod
    def _py_pod_to_fantom(py_pod):
        """Convert Python pod name to Fantom pod name.

        Python uses underscore suffix for reserved words (e.g., 'def_' -> 'def').
        """
        return Type._PY_POD_TO_FANTOM.get(py_pod, py_pod)

    @staticmethod
    def _fantom_pod_to_py(fantom_pod):
        """Convert Fantom pod name to Python module name.

        Python uses underscore suffix for reserved words (e.g., 'def' -> 'def_').
        """
        return Type._FANTOM_POD_TO_PY.get(fantom_pod, fantom_pod)

    @staticmethod
    def find(qname, checked=True):
        """Find type by qname - returns cached singleton"""
        from .Err import ArgErr, UnknownTypeErr, UnknownPodErr

        if qname in Type._cache:
            return Type._cache[qname]

        # Handle Java FFI types (sanitized by transpiler with java_ffi_fail. prefix)
        # These are placeholders for Java types that can't exist in Python
        # Always return None to allow type metadata registration to proceed
        # (the actual methods using these types will fail at call time if invoked)
        if qname.startswith("java_ffi_fail."):
            return None

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
            # "[]" alone is invalid - empty element type
            if not elem_qname:
                raise ArgErr.make(f"Invalid type signature '{qname}', use <pod>::<type>")
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
            nullable_type = base_type.to_nullable()
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
                params = Type._split_params(params_str)
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

        # Validate basic type signature format: must have pod::type
        if "::" not in qname:
            raise ArgErr.make(f"Invalid type signature '{qname}', use <pod>::<type>")

        colon_idx = qname.find("::")
        pod_name = qname[:colon_idx]
        type_name_part = qname[colon_idx+2:]

        # Validate: "sys::" (empty type name) or "::sys" (empty pod name)
        if not pod_name or not type_name_part:
            raise ArgErr.make(f"Invalid type signature '{qname}', use <pod>::<type>")

        # For checked=true with sys pod and unknown type, throw UnknownTypeErr
        # Exception: internal implementation types (NullableType, ListType, etc.)
        # Also allow 'type' - Python's builtin that sometimes gets passed through
        _INTERNAL_TYPES = {"NullableType", "ListType", "MapType", "FuncType", "GenericParamType", "type"}
        if pod_name == "sys" and qname not in Type._KNOWN_TYPES and type_name_part not in _INTERNAL_TYPES:
            # Check if module can be imported
            try:
                __import__(f'fan.sys.{type_name_part}', fromlist=[type_name_part])
            except ImportError:
                if checked:
                    raise UnknownTypeErr.make(f"Unknown type: {qname}")
                return None

        # For unknown pods, throw UnknownPodErr (only if checked=True)
        # Let Pod.find() handle pod discovery dynamically via import
        from .Pod import Pod
        pod = Pod.find(pod_name, False)  # checked=False to avoid recursion
        if pod is None:
            if checked:
                raise UnknownPodErr.make(f"Unknown pod: {pod_name}")
            return None

        t = Type(qname)
        Type._cache[qname] = t

        # Register type with its Pod so Pod.type(name) works
        if "::" in qname:
            parts = qname.split("::")
            if len(parts) == 2:
                pod_name, type_name = parts
                from .Pod import Pod
                pod = Pod.find(pod_name, False)
                if pod is not None:
                    pod._register_type(t)

        # Try to import the module to trigger tf_() metadata registration
        # This ensures that Type.find('pod::Name') has proper type flags
        if "::" in qname:
            parts = qname.split("::")
            if len(parts) == 2:
                pod, name = parts
                # Convert Fantom pod name to Python module name (e.g., 'def' -> 'def_')
                py_pod = Type._fantom_pod_to_py(pod)
                try:
                    module = __import__(f'fan.{py_pod}.{name}', fromlist=[name])
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
        if self.is_enum():
            return Type.find("sys::Enum")
        # Check if this is an Err subclass
        if self._qname != "sys::Err" and self.is_err():
            # Find the immediate parent Err type
            return self._find_err_base()
        return Type.find("sys::Obj")

    def is_err(self):
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

    def _find_err_base(self):
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
            return Duration.def_val()
        if self._qname == "sys::Date":
            from .DateTime import Date
            return Date.def_val()
        if self._qname == "sys::DateTime":
            from .DateTime import DateTime
            return DateTime.def_val()
        if self._qname == "sys::Time":
            from .DateTime import Time
            return Time.def_val()

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
    def is_nullable(self):
        return False

    def to_nullable(self):
        """Return nullable version of this type"""
        if self._nullable is None:
            self._nullable = NullableType(self)
        return self._nullable

    def to_non_nullable(self):
        """Return non-nullable version of this type"""
        return self

    # Generic/List/Map support
    def to_list_of(self):
        """Return list type with this as element type (e.g., Int -> Int[])"""
        if self._listOf is None:
            self._listOf = ListType(self)
            # Cache it so Type.find returns the same instance
            Type._cache[self._listOf.signature()] = self._listOf
        return self._listOf

    def is_generic_type(self):
        return False

    def is_generic_instance(self):
        return False

    def is_generic_parameter(self):
        return False

    def is_immutable(self):
        """Types are always immutable"""

    def literal_encode(self, out):
        """Encode for serialization.

        Type literals are written as: sys::Str#
        """
        out.w(self.signature())
        out.w("#")
        return True

    def to_immutable(self):
        """Types are already immutable, return self"""
        return self

    def to_str(self):
        return self.signature()

    def to_locale(self):
        """Return locale string for type - same as signature for now"""
        return self.signature()

    # Type flags
    def is_val(self):
        """Check if value type (Bool, Int, Float)"""
        base = self.to_non_nullable()
        return base._qname in Type._VAL_TYPES

    def is_abstract(self):
        return self._qname in Type._ABSTRACT_TYPES

    def is_class(self):
        return not self.is_mixin() and not self.is_enum()

    def is_enum(self):
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

    def is_facet(self):
        """Check if this type is a facet. Uses transpiler flags if available."""
        # Check transpiler-provided flag (0x80000 = Facet)
        if self._type_flags & 0x80000:
            return True
        return False

    def is_final(self):
        return self._qname in Type._FINAL_TYPES

    def is_internal(self):
        """Check if this type is internal. Uses transpiler flags if available."""
        # Check transpiler-provided flag (0x8 = Internal)
        if self._type_flags & 0x00000008:
            return True
        return False

    def is_mixin(self):
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
        "sys::Float", "sys::Decimal", "sys::Num", "sys::File", "sys::FileStore", "sys::Log",
        "sys::Charset", "sys::Endian",
    }

    def is_const(self):
        """Check if this type is a const class (immutable).

        Const classes are always immutable. This checks:
        1. Transpiler-provided flag (0x00002000 = FConst.Const)
        2. Known const types in sys (for hand-written runtime classes)
        """
        # Check transpiler-provided flag (0x00002000 = FConst.Const)
        if self._type_flags & 0x00002000:
            return True
        # For hand-written sys types, check known const types
        return self._qname in Type._CONST_TYPES

    def is_public(self):
        """Check if this type is public."""
        # Internal means not public
        return not self.is_internal()

    def is_synthetic(self):
        return "$" in self._name

    def is_generic(self):
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
        return FanList.from_literal(result, "sys::Type").to_immutable()

    def inheritance(self):
        """Return inheritance chain from this type to Obj, including mixins.

        Follows the JS pattern from Type.js#buildInheritance:
        1. Add self
        2. Add base class's inheritance chain
        3. Add each mixin's inheritance chain

        Results are cached (like JS inheritance$) because this is called
        millions of times during type checking.
        """
        # Return cached result if available (like JS: if (this.inheritance$ == null) ...)
        if self._inheritance_cache is not None:
            return self._inheritance_cache

        from .List import List as FanList

        # Handle Void as special case
        if self._qname == "sys::Void":
            self._inheritance_cache = FanList.from_literal([self], "sys::Type").to_immutable()
            return self._inheritance_cache

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

        # Cache and return
        self._inheritance_cache = FanList.from_literal(result, "sys::Type").to_immutable()
        return self._inheritance_cache

    # Generic type support
    def params(self):
        """Return generic parameters map - empty by default, always read-only"""
        from .Map import Map
        return Map.from_literal([], [], "sys::Str", "sys::Type").to_immutable()

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
            return v_type.to_list_of()

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

    def empty_list(self):
        """Return empty immutable list of this type (e.g., Str.emptyList returns Str[])"""
        if self._emptyList is None:
            from .List import List as FanList
            # Create empty list with this type as element type
            self._emptyList = FanList.from_literal([], self._qname).to_immutable()
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
        "sys::Test", "sys::Enum", "sys::Charset", "sys::Depend",
    }

    # Known static const fields in sys types - these are NOT methods
    # In Python they're implemented as @staticmethod functions, but in Fantom they're fields
    _SYS_CONST_FIELDS = {
        "sys::Float": {"pi", "e", "posInf", "negInf", "nan"},
        "sys::Int": {"maxVal", "minVal", "def_val"},
        "sys::Duration": {"def_val", "minVal", "maxVal"},
        "sys::Str": {"def_val"},
        "sys::Bool": {"def_val"},
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

        # Discover methods (both static and instance)
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

            # Check what kind of method/attribute this is
            raw_attr = inspect.getattr_static(py_class, name)
            is_static_method = isinstance(raw_attr, staticmethod)
            is_regular_function = inspect.isfunction(raw_attr)

            if is_static_method and callable(attr):
                # Static method
                method = self._create_method_from_function(name, attr, is_static=True)
                if method:
                    discovered.append(method)
            elif is_regular_function:
                # Instance method (regular function defined in class)
                method = self._create_method_from_function(name, raw_attr, is_static=False)
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
            return self.to_nullable()

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
        V_nullable = V.to_nullable()
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
        methods.append(Method(self, "map", 0x0001, R.to_list_of(), [Param("f", mapFuncType, False)], {}))

        # flatMap(|V,Int->R[]| f): R[]
        flatMapFuncType = FuncType([V, Type.find("sys::Int")], R.to_list_of())
        methods.append(Method(self, "flatMap", 0x0001, R.to_list_of(), [Param("f", flatMapFuncType, False)], {}))

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
        V_nullable = V.to_nullable()
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
        methods.append(Method(self, "keys", 0x0001, K.to_list_of(), [], {}))
        # vals: V[]
        methods.append(Method(self, "vals", 0x0001, V.to_list_of(), [], {}))
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

        Note: Slot names use snake_case (Python convention) to match transpiled code.
        Type.slot() lookup handles camelCase -> snake_case conversion.
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

        # hash(): Int - uses hash_ because hash is a Python builtin
        methods.append(Method(self, "hash_", 0x1001, Type.find("sys::Int"), [], {}))

        # to_str(): Str
        methods.append(Method(self, "to_str", 0x1001, Type.find("sys::Str"), [], {}))

        # trap(Str name, Obj?[]? args): Obj?
        methods.append(Method(self, "trap", 0x1001, Type.find("sys::Obj?"),
                              [Param("name", Type.find("sys::Str"), False),
                               Param("args", Type.find("sys::Obj?[]?"), True)], {}))

        # is_immutable(): Bool
        methods.append(Method(self, "is_immutable", 0x0001, Type.find("sys::Bool"), [], {}))

        # to_immutable(): Obj
        methods.append(Method(self, "to_immutable", 0x0001, self, [], {}))

        # typeof(): Type
        methods.append(Method(self, "typeof", 0x0001, Type.find("sys::Type"), [], {}))

        # with(|This| f): This - 'with' is a Python keyword so it's with_
        methods.append(Method(self, "with_", 0x0001, self,
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

    def _create_const_field(self, field_name):
        """Create a Field object for a known const field in a sys type.

        Args:
            field_name: Name of the const field (e.g., 'nan', 'pi', 'maxVal')

        Returns:
            Field object or None
        """
        from .Field import Field

        # Determine field type based on parent type
        if self._qname == "sys::Float":
            field_type = Type.find("sys::Float")
        elif self._qname == "sys::Int":
            field_type = Type.find("sys::Int")
        elif self._qname == "sys::Duration":
            field_type = Type.find("sys::Duration")
        elif self._qname == "sys::Str":
            field_type = Type.find("sys::Str")
        elif self._qname == "sys::Bool":
            field_type = Type.find("sys::Bool")
        else:
            field_type = self

        # Static const field: Public (0x0001) | Static (0x0800) | Const (0x0002)
        flags = 0x0001 | 0x0800 | 0x0002

        return Field(self, field_name, flags, field_type, {}, None)

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
        # Use _slots_by_name as guard (like JS slotsByName$)
        # But also re-reflect if _slots_info has grown since last reflection
        # This handles the case where Type.find() creates the Type before the module
        # imports and registers its slots via am_()
        if self._slots_by_name:
            # Count how many of our own slots were reflected last time
            own_slots_count = sum(1 for s in self._slot_list if s._parent is self)
            if len(self._slots_info) <= own_slots_count:
                return self
            # More slots have been added via am_() - need to re-reflect
            # Clear all cached slot data
            self._slots_by_name = {}
            self._slot_list = []
            self._field_list = []
            self._method_list = []

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

            # Add known const fields for sys types (like Float.nan, Int.maxVal)
            const_fields = Type._SYS_CONST_FIELDS.get(self._qname, set())
            if const_fields:
                for field_name in const_fields:
                    field = self._create_const_field(field_name)
                    if field:
                        self._merge_slot(field, slots, slots_by_name, name_to_index)

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
        return FanList.from_literal(self._slot_list, "sys::Slot").to_immutable()

    def slot(self, name, checked=True):
        """Find slot by name using two-pass lookup.

        This method accepts both Fantom names (camelCase) and Python names
        (snake_case) for slot lookup. This enables:
        1. Serialization to work (ObjDecoder passes Fantom names from files)
        2. Transpiled code to work (uses snake_case)
        3. Existing code using camelCase to continue working

        Args:
            name: Slot name to find (camelCase or snake_case)
            checked: If True, raise UnknownSlotErr if not found

        Returns:
            Slot instance or None (if checked=False and not found)
        """
        self._reflect()

        # First pass: exact match (works for both snake_case and camelCase if stored)
        slot = self._slots_by_name.get(name)
        if slot is not None:
            return slot

        # Second pass: try camelCase -> snake_case conversion
        # This handles the case where name is a Fantom name (e.g., "fromStr")
        # but the slot is registered with Python name (e.g., "from_str")
        snake_name = _camel_to_snake(name)
        if snake_name != name:
            slot = self._slots_by_name.get(snake_name)
            if slot is not None:
                return slot

        # Third pass: try Python builtin escape (bidirectional)
        # This handles both directions:
        #   hash -> hash_ (Fantom name to Python name)
        #   hash_ -> hash (Python name to Fantom name, for hand-written sys types)
        # Python reserved words/builtins get _ appended in the transpiler
        _PYTHON_BUILTINS = {'hash', 'print', 'abs', 'min', 'max', 'set', 'map',
                            'list', 'dir', 'oct', 'open', 'vars', 'match',
                            'all', 'any', 'pow', 'round', 'type', 'id', 'and', 'or', 'not'}
        if name in _PYTHON_BUILTINS:
            # Fantom name -> Python name (hash -> hash_)
            slot = self._slots_by_name.get(name + '_')
            if slot is not None:
                return slot
        elif name.endswith('_') and name[:-1] in _PYTHON_BUILTINS:
            # Python name -> Fantom name (hash_ -> hash)
            slot = self._slots_by_name.get(name[:-1])
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
        return FanList.from_literal(self._field_list, "sys::Field").to_immutable()

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
        return FanList.from_literal(self._method_list, "sys::Method").to_immutable()

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

    def has_facet(self, facetType):
        """Check if this type has a facet.

        Args:
            facetType: Type of facet to check for

        Returns:
            True if facet is present, False otherwise
        """
        facet_qname = facetType.qname() if hasattr(facetType, 'qname') else str(facetType)
        return facet_qname in self._type_facets

    def facet(self, facetType, checked=True):
        """Get facet value including inherited facets.

        Args:
            facetType: Type of facet to get
            checked: If True, raise error if not found

        Returns:
            Facet instance or None
        """
        # Ensure type metadata is loaded (triggers tf_() if needed)
        self._ensure_loaded()

        facet_qname = facetType.qname() if hasattr(facetType, 'qname') else str(facetType)

        # Check own facets first
        if facet_qname in self._type_facets:
            return self._create_facet_instance(facet_qname, self._type_facets[facet_qname])

        # Check inherited facets (only if facet has inherited=true)
        inherited_data = self._find_inherited_facet(facet_qname)
        if inherited_data is not None:
            return self._create_facet_instance(facet_qname, inherited_data)

        if checked:
            from .Err import UnknownFacetErr
            raise UnknownFacetErr.make(f"Facet not found: {facetType}")
        return None

    def _create_facet_instance(self, facet_qname, facet_data):
        """Create a FacetInstance for the given facet qname and data."""
        facet_type = Type.find(facet_qname, True)

        # For marker facets (no values), return the singleton defVal() instance
        # This ensures identity equality: type.facet(FacetM1#) === FacetM1.def_val()
        if not facet_data:
            # Try to import the facet class and get defVal()
            try:
                parts = facet_qname.split("::")
                if len(parts) == 2:
                    pod, name = parts
                    module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                    cls = getattr(module, name, None)
                    if cls is not None and hasattr(cls, 'def_val'):
                        return cls.def_val()
            except:
                pass
            # Fallback to FacetInstance
            return FacetInstance(facet_type, facet_data)

        # For facets with values, create an instance with the stored values
        return FacetInstance(facet_type, facet_data)

    def _find_inherited_facet(self, facet_qname):
        """Find an inherited facet by qname.

        Only returns facets with @FacetMeta{inherited=true}.

        Args:
            facet_qname: Qualified name of facet to find

        Returns:
            Facet data dict if found, None otherwise
        """
        # Only inheritable facets can be inherited
        if not self._is_inherited_facet(facet_qname):
            return None

        # Check mixins
        for mixin in self.mixins():
            mixin._ensure_loaded()
            if facet_qname in mixin._type_facets:
                return mixin._type_facets[facet_qname]
            # Recursively check mixin's parents
            inherited = mixin._find_inherited_facet(facet_qname)
            if inherited is not None:
                return inherited

        # Check base class
        base = self.base()
        if base is not None and base._qname != self._qname and base._qname != "sys::Obj":
            base._ensure_loaded()
            if facet_qname in base._type_facets:
                return base._type_facets[facet_qname]
            # Recursively check base's parents
            inherited = base._find_inherited_facet(facet_qname)
            if inherited is not None:
                return inherited

        return None

    def facets(self):
        """Return list of all facets including inherited facets.

        Facets with @FacetMeta{inherited=true} are inherited from:
        - Mixins (directly implemented)
        - Base class

        Returns:
            Immutable List of Facet instances (cached for identity comparison)
        """
        if self._facets_list is not None:
            return self._facets_list

        from .List import List as FanList

        # Collect facets: own facets first, then inherited
        # Use dict to track by qname (own facets override inherited)
        facet_map = {}  # facet_qname -> (facet_type, facet_data)

        # Collect inherited facets first (so own facets can override)
        self._collect_inherited_facets(facet_map, set())

        # Own facets (override any inherited with same qname)
        for facet_qname, facet_data in self._type_facets.items():
            facet_type = Type.find(facet_qname, True)
            facet_map[facet_qname] = (facet_type, facet_data)

        # Build result list
        result = []
        for facet_qname, (facet_type, facet_data) in facet_map.items():
            result.append(FacetInstance(facet_type, facet_data))

        # Return immutable Fantom List with Facet element type
        self._facets_list = FanList.from_literal(result, "sys::Facet").to_immutable()
        return self._facets_list

    def _collect_inherited_facets(self, facet_map, visited):
        """Collect inherited facets from mixins and base class.

        Only facets with @FacetMeta{inherited=true} are inherited.

        Args:
            facet_map: Dict to accumulate facets (facet_qname -> (type, data))
            visited: Set of already-visited type qnames (prevent cycles)
        """
        if self._qname in visited:
            return
        visited.add(self._qname)

        # Collect from mixins first
        for mixin in self.mixins():
            mixin._ensure_loaded()
            for facet_qname, facet_data in mixin._type_facets.items():
                if self._is_inherited_facet(facet_qname):
                    if facet_qname not in facet_map:
                        facet_type = Type.find(facet_qname, True)
                        facet_map[facet_qname] = (facet_type, facet_data)
            # Recursively collect from mixin's parents
            mixin._collect_inherited_facets(facet_map, visited)

        # Collect from base class
        base = self.base()
        if base is not None and base._qname != self._qname and base._qname != "sys::Obj":
            base._ensure_loaded()
            for facet_qname, facet_data in base._type_facets.items():
                if self._is_inherited_facet(facet_qname):
                    if facet_qname not in facet_map:
                        facet_type = Type.find(facet_qname, True)
                        facet_map[facet_qname] = (facet_type, facet_data)
            # Recursively collect from base's parents
            base._collect_inherited_facets(facet_map, visited)

    def _ensure_loaded(self):
        """Ensure this type's metadata is loaded (trigger tf_() if needed)."""
        # If we already have facets or reflected, we're loaded
        if self._type_facets or self._reflected:
            return

        # Try to import the module to trigger tf_() metadata registration
        if "::" in self._qname:
            parts = self._qname.split("::")
            if len(parts) == 2:
                pod, name = parts
                try:
                    __import__(f'fan.{pod}.{name}', fromlist=[name])
                except ImportError:
                    pass

    def _is_inherited_facet(self, facet_qname):
        """Check if a facet type has @FacetMeta{inherited=true}."""
        # Load the facet type to check its metadata
        facet_type = Type.find(facet_qname, False)
        if facet_type is None:
            return False

        # Ensure facet type is loaded
        facet_type._ensure_loaded()

        # Check if it has @FacetMeta{inherited=true}
        facet_meta = facet_type._type_facets.get("sys::FacetMeta")
        if facet_meta is not None:
            return facet_meta.get("inherited", False) == True

        return False

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
    def _split_params(s):
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

    def is_nullable(self):
        return True

    def to_nullable(self):
        return self

    def to_non_nullable(self):
        return self._root

    def is_(self, that):
        return self._root.is_(that)

    def fits(self, that):
        return self._root.fits(that)

    def is_generic_parameter(self):
        return self._root.is_generic_parameter()

    def is_val(self):
        return self._root.is_val()

    def to_list_of(self):
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

    def is_nullable(self):
        return False

    def to_nullable(self):
        if self._nullable is None:
            self._nullable = NullableType(self)
        return self._nullable

    def to_non_nullable(self):
        return self

    def is_generic_instance(self):
        return True

    def params(self):
        """Return generic parameters map for List<V>: {V: elem_type, L: this}"""
        from .Map import Map
        return Map.from_literal(["V", "L"], [self._v, self], "sys::Str", "sys::Type").to_immutable()

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

    def _substitute_type(self, t):
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
            return self._v.to_nullable() if hasattr(self._v, 'to_nullable') else self._v

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
                new_params.append(self._substitute_type(p))
            new_ret = self._substitute_type(t._ret)
            return FuncType(new_params, new_ret)

        # Handle ListType - substitute V/R in element type
        if isinstance(t, ListType):
            new_elem = self._substitute_type(t._v)
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
        return self._substitute_type(baseRet)

    def params(self):
        """Parameters with V substituted"""
        baseParams = self._base.params()
        if baseParams is None:
            return []
        # Return wrapper params that substitute types
        return [ParameterizedListParam(p, self) for p in baseParams]

    def is_static(self):
        return self._base.is_static() if hasattr(self._base, 'is_static') else False

    def is_public(self):
        return self._base.is_public() if hasattr(self._base, 'is_public') else True

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
        return self._method._substitute_type(baseType)


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

    def is_nullable(self):
        return False

    def to_nullable(self):
        if self._nullable is None:
            self._nullable = NullableType(self)
        return self._nullable

    def to_non_nullable(self):
        return self

    def is_generic_instance(self):
        return True

    def params(self):
        """Return generic parameters map for Map<K,V>: {K: key_type, V: val_type, M: this}"""
        from .Map import Map
        return Map.from_literal(["K", "V", "M"], [self._k, self._v, self], "sys::Str", "sys::Type").to_immutable()

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

    def _substitute_type(self, t):
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
            return self._k.to_nullable() if hasattr(self._k, 'to_nullable') else self._k
        if sig == "sys::V?" or sig == "V?":
            return self._v.to_nullable() if hasattr(self._v, 'to_nullable') else self._v

        # Check for M (map type itself)
        if sig == "sys::M" or sig == "M":
            return self._owner

        # Handle FuncType - substitute K/V in params and return type
        if isinstance(t, FuncType):
            new_params = []
            for p in t._params:
                new_params.append(self._substitute_type(p))
            new_ret = self._substitute_type(t._ret)
            return FuncType(new_params, new_ret)

        # Handle ListType - substitute K/V in element type (e.g., K[] -> Int[])
        if isinstance(t, ListType):
            new_elem = self._substitute_type(t._v)
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
        return self._substitute_type(baseRet)

    def params(self):
        """Parameters with K/V substituted"""
        baseParams = self._base.params()
        if baseParams is None:
            return []
        # Return wrapper params that substitute types
        return [ParameterizedParam(p, self) for p in baseParams]

    def is_static(self):
        return self._base.is_static() if hasattr(self._base, 'is_static') else False

    def is_public(self):
        return self._base.is_public() if hasattr(self._base, 'is_public') else True

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
        return self._method._substitute_type(baseType)


class ParameterizedField:
    """Wrapper around a generic Field that substitutes type parameters.

    Used by MapType to return fields with concrete types instead of K, V, etc.
    """

    def __init__(self, baseField, keyType, valType, owner):
        self._base = baseField
        self._k = keyType
        self._v = valType
        self._owner = owner

    def _substitute_type(self, t):
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
            return self._k.to_nullable() if hasattr(self._k, 'to_nullable') else self._k
        if sig == "sys::V?" or sig == "V?":
            return self._v.to_nullable() if hasattr(self._v, 'to_nullable') else self._v

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
        return self._substitute_type(baseType)

    def is_static(self):
        return self._base.is_static() if hasattr(self._base, 'is_static') else False

    def is_public(self):
        return self._base.is_public() if hasattr(self._base, 'is_public') else True


class FuncType(Type):
    """Function type with parameter types and return type - e.g., |Int,Str->Bool|"""

    def __init__(self, params, ret):
        """params is list of parameter types, ret is return type"""
        self._params = params  # List of Type
        self._ret = ret  # Return Type
        sig = self._build_signature()
        super().__init__(sig)

    def _build_signature(self):
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
        return self._build_signature()

    def name(self):
        return "Func"

    def qname(self):
        return "sys::Func"

    def pod(self):
        from .Pod import Pod
        return Pod.find("sys")

    def base(self):
        return Type.find("sys::Func")

    def is_nullable(self):
        return False

    def to_nullable(self):
        if self._nullable is None:
            self._nullable = NullableType(self)
        return self._nullable

    def to_non_nullable(self):
        return self

    def is_generic_instance(self):
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
        return Map.from_literal(keys, vals, "sys::Str", "sys::Type").to_immutable()

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
        if ret is not None and hasattr(ret, 'is_generic_parameter') and ret.is_generic_parameter():
            ret = self._parameterize_type(ret)

        # Parameterize params
        new_params = []
        for p in method._params:
            p_type = p._type if hasattr(p, '_type') else None
            if p_type is not None and hasattr(p_type, 'is_generic_parameter') and p_type.is_generic_parameter():
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
        is_nullable = t.is_nullable() if hasattr(t, 'is_nullable') else False
        root = t
        if is_nullable and hasattr(t, 'to_non_nullable'):
            root = t.to_non_nullable()

        # Check if this is a generic param (sys::A, sys::B, sys::R, etc.)
        if not (hasattr(root, 'is_generic_parameter') and root.is_generic_parameter()):
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
                if is_nullable and hasattr(result, 'to_nullable'):
                    return result.to_nullable()
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

    def is_generic_parameter(self):
        return True

    def mixins(self):
        from .List import List as FanList
        return FanList.from_literal([], "sys::Type").to_immutable()


class FacetInstance(Obj):
    """Runtime representation of a facet instance.

    This creates a proxy that gets default field values from the actual facet class
    and applies any explicit values from facet_data.

    Allows accessing facet field values via:
    - Direct attribute access: facet._val, facet._b
    - Trap access: facet->val, facet->b
    """

    def __new__(cls, facet_type, facet_data):
        """Create or return cached facet instance.

        For marker facets (empty facet_data), use the singleton defVal().
        For facets with values, create a FacetInstance with proper defaults.
        """
        facet_data = facet_data or {}

        # For marker facets (no values), try to return defVal() singleton
        if not facet_data:
            qname = facet_type.qname() if hasattr(facet_type, 'qname') else str(facet_type)
            try:
                parts = qname.split("::")
                if len(parts) == 2:
                    pod, name = parts
                    module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                    facet_cls = getattr(module, name, None)
                    if facet_cls is not None and hasattr(facet_cls, 'def_val'):
                        return facet_cls.def_val()
            except:
                pass

        # For facets with values, create a FacetInstance
        return object.__new__(cls)

    def __init__(self, facet_type, facet_data):
        """Initialize facet instance with proper field values.

        Creates a proxy that gets default values from the actual facet class
        and applies explicit values from facet_data.
        """
        # Skip if this is a cached marker facet (already initialized by defVal)
        if hasattr(self, '_facet_type') and self._facet_type is not None:
            return

        self._facet_type = facet_type
        self._facet_data = facet_data or {}

        # Try to get default values by creating an actual facet instance
        qname = facet_type.qname() if hasattr(facet_type, 'qname') else str(facet_type)
        try:
            parts = qname.split("::")
            if len(parts) == 2:
                pod, name = parts
                module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                facet_cls = getattr(module, name, None)
                if facet_cls is not None:
                    # Create a default instance to get field defaults
                    try:
                        default_inst = facet_cls.make() if hasattr(facet_cls, 'make') else facet_cls()
                        # Copy all _fieldName attributes from default instance
                        for attr_name in dir(default_inst):
                            if attr_name.startswith('_') and not attr_name.startswith('__'):
                                try:
                                    val = getattr(default_inst, attr_name)
                                    if not callable(val):
                                        setattr(self, attr_name, val)
                                except:
                                    pass
                    except:
                        pass
        except:
            pass

        # Now apply explicit values from facet_data, decoding serialization strings
        for field_name, value in self._facet_data.items():
            decoded_value = self._decode_value(value)
            # Escape Python reserved words (like 'type' -> 'type_')
            escaped_name = self._escape_name(field_name)
            setattr(self, f"_{escaped_name}", decoded_value)

    # Python reserved words that need escaping with trailing underscore
    _RESERVED_WORDS = {
        "and", "as", "assert", "async", "await", "break", "class", "continue",
        "def", "del", "elif", "else", "except", "finally", "for", "from",
        "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
        "or", "pass", "raise", "return", "try", "type", "while", "with", "yield"
    }

    def _escape_name(self, name):
        """Escape Python reserved words by adding trailing underscore."""
        if name in FacetInstance._RESERVED_WORDS:
            return name + "_"
        return name

    def _decode_value(self, value):
        """Decode a facet value from its serialization format.

        Values can be:
        - Python primitives (int, bool, str) - return as-is
        - Fantom serialization strings like "sys::Version(\"9.0\")" - decode
        - Type literals like "sys::Str" - resolve to Type
        - Slot literals like "sys::Float#nan" - resolve to Slot
        - List literals like "[1,2,3]" - decode to List
        """
        # None/null
        if value is None:
            return None

        # Already a Python primitive or Fantom object
        if isinstance(value, (int, float, bool)):
            return value

        # String values may need decoding
        if isinstance(value, str):
            # Empty string means use default
            if not value:
                return None

            # Type literal: "sys::Str" or "sys::Str#"
            if "::" in value and not value.startswith('"') and not value.startswith('['):
                # Check for slot literal (contains #)
                if '#' in value:
                    return self._decode_slot_literal(value)
                # Check for constructor call: "sys::Version(\"9.0\")"
                if '(' in value:
                    return self._decode_ctor_call(value)
                # Plain type literal
                return Type.find(value, False)

            # List literal: "[1,2,3]"
            if value.startswith('[') and value.endswith(']'):
                return self._decode_list_literal(value)

            # Quoted string - extract the actual string value
            if value.startswith('"') and value.endswith('"'):
                return value[1:-1].replace('\\"', '"')

            # Plain string
            return value

        # Not a string - return as-is
        return value

    def _decode_ctor_call(self, s):
        """Decode a constructor call like sys::Version(\"9.0\")"""
        try:
            # Parse: typeName(arg1, arg2, ...)
            paren_idx = s.index('(')
            type_qname = s[:paren_idx]
            args_str = s[paren_idx+1:-1]  # Remove parens

            # Get the type
            t = Type.find(type_qname, False)
            if t is None:
                return s  # Return original string if type not found

            # Parse arguments - for now just handle single string arg
            # Remove quotes from arg
            if args_str.startswith('\\"') and args_str.endswith('\\"'):
                args_str = args_str[2:-2]
            elif args_str.startswith('"') and args_str.endswith('"'):
                args_str = args_str[1:-1]

            # Try fromStr for simple cases
            if type_qname == "sys::Version":
                from .Version import Version
                return Version.from_str(args_str)
            elif type_qname == "sys::Duration":
                from .Duration import Duration
                return Duration.from_str(args_str)
            elif type_qname == "sys::Uri":
                from .Uri import Uri
                return Uri.from_str(args_str)

            # Fallback - try make() with parsed args
            return t.make([args_str])
        except Exception as e:
            return s  # Return original string on error

    def _decode_slot_literal(self, s):
        """Decode a slot literal like sys::Float#nan"""
        try:
            hash_idx = s.index('#')
            type_qname = s[:hash_idx]
            slot_name = s[hash_idx+1:]

            t = Type.find(type_qname, False)
            if t is None:
                return s

            return t.slot(slot_name, False)
        except Exception as e:
            return s

    def _decode_list_literal(self, s):
        """Decode a list literal like [1,2,3]"""
        try:
            from .List import List as FanList

            # Remove brackets
            inner = s[1:-1].strip()
            if not inner:
                return FanList.from_literal([], "sys::Obj")

            # Split by comma and parse each element
            elements = []
            for elem in inner.split(','):
                elem = elem.strip()
                # Try to parse as int
                try:
                    elements.append(int(elem))
                except ValueError:
                    # Try float
                    try:
                        elements.append(float(elem))
                    except ValueError:
                        # Keep as string
                        elements.append(elem)

            # Determine element type
            if all(isinstance(e, int) for e in elements):
                return FanList.from_literal(elements, "sys::Int")
            return FanList.from_literal(elements, "sys::Obj")
        except Exception as e:
            return s

    def typeof(self):
        """Return the facet type"""
        return self._facet_type

    def trap(self, name, args=None):
        """Dynamic field access via -> operator"""
        if args is None:
            args = []
        # Check _fieldName attribute first
        attr_name = f"_{name}"
        if hasattr(self, attr_name):
            return getattr(self, attr_name)
        # Check facet_data
        if name in self._facet_data:
            return self._decode_value(self._facet_data[name])
        # No args means getter - return None if not found
        if not args:
            return None
        from .Err import UnknownSlotErr
        raise UnknownSlotErr.make(f"{self._facet_type}.{name}")

    def __getattr__(self, name):
        """Allow Python attribute access to facet fields"""
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        # Try _fieldName
        attr_name = f"_{name}"
        try:
            return object.__getattribute__(self, attr_name)
        except AttributeError:
            pass
        raise AttributeError(f"Facet has no field: {name}")

    def equals(self, other):
        """Check equality based on facet type and values"""
        if other is None:
            return False
        if isinstance(other, FacetInstance):
            return self._facet_type.qname() == other._facet_type.qname()
        # Also check against actual facet class instances
        if hasattr(other, 'typeof') and callable(other.typeof):
            return self._facet_type.qname() == other.typeof().qname()
        return False

    def __eq__(self, other):
        return self.equals(other)

    def __hash__(self):
        return hash(self._facet_type.qname())

    def to_str(self):
        return f"@{self._facet_type.qname()}"


# Pre-populate static type$ fields for common types
# These will be set after module initialization
def _init_type_fields():
    """Initialize static type$ fields on type classes"""
    pass  # Will be called by runtime initialization
    pass  # Will be called by runtime initialization
    pass  # Will be called by runtime initialization

