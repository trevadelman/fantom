#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#


class ObjUtil:
    """Utility methods for object operations"""

    @staticmethod
    def hash(obj):
        if obj is None:
            return 0
        if isinstance(obj, bool):
            from .Bool import Bool
            return Bool.hash(obj)
        # Check for hash_ first (Fantom transpiled name to avoid Python builtin conflict)
        if hasattr(obj, "hash_") and callable(obj.hash_):
            return obj.hash_()
        if hasattr(obj, "hash") and callable(obj.hash):
            return obj.hash()
        return hash(obj)

    @staticmethod
    def hash_(obj):
        """Hash method aliased with underscore"""
        return ObjUtil.hash(obj)

    @staticmethod
    def equals(a, b):
        if a is None:
            return b is None
        if b is None:
            return False
        # NaN equality in Fantom: NaN == NaN is true
        if isinstance(a, float) and isinstance(b, float):
            import math
            if math.isnan(a) and math.isnan(b):
                return True
        if hasattr(a, "equals") and callable(getattr(a, "equals", None)):
            return a.equals(b)
        return a == b

    @staticmethod
    def same(a, b):
        """Check if two objects are the same instance (Fantom === semantics).

        Fantom identity semantics:
        - Strings: Use object identity (methods return same object when unchanged)
        - Numbers (int, float, bool): Value types - equal values are "same"
        - Value types (Duration, etc.): Use equals() - same value means same identity
        - Other objects: Python object identity
        """
        if a is None:
            return b is None
        if b is None:
            return False
        # Numbers are value types in Fantom - equal values are "same"
        if isinstance(a, (int, float, bool)):
            if type(a) == type(b):
                return a == b
            # Also handle int/float comparison
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                if not isinstance(a, bool) and not isinstance(b, bool):
                    return a == b
            return False
        # Value types use equals() for identity - same value means same identity
        # Types opt-in to value semantics by defining _same_uses_equals = True
        # This includes Duration, Date, Time, Uri, etc. where 5ns === 5ns is true
        # Reference types (File, Buf, etc.) use object identity even if immutable
        if hasattr(a, '_same_uses_equals') and a._same_uses_equals:
            if type(a) == type(b) and hasattr(a, 'equals'):
                return a.equals(b)
        # For strings and other reference types, use object identity
        return a is b

    @staticmethod
    def compare(a, b):
        if a is None:
            return -1 if b is not None else 0
        if b is None:
            return 1
        # Dispatch to Float.compare for floats (handles NaN)
        if isinstance(a, float):
            from .Float import Float
            return Float.compare(a, b)
        if hasattr(a, "compare") and callable(a.compare):
            return a.compare(b)
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    @staticmethod
    def compare_ne(a, b):
        return not ObjUtil.equals(a, b)

    @staticmethod
    def compare_lt(a, b):
        # NaN comparisons always return false (except for ==)
        import math
        if isinstance(a, float) and math.isnan(a):
            return False
        if isinstance(b, float) and math.isnan(b):
            return False
        return ObjUtil.compare(a, b) < 0

    @staticmethod
    def compare_le(a, b):
        # NaN comparisons always return false
        import math
        if isinstance(a, float) and math.isnan(a):
            return False
        if isinstance(b, float) and math.isnan(b):
            return False
        return ObjUtil.compare(a, b) <= 0

    @staticmethod
    def compare_ge(a, b):
        # NaN comparisons always return false
        import math
        if isinstance(a, float) and math.isnan(a):
            return False
        if isinstance(b, float) and math.isnan(b):
            return False
        return ObjUtil.compare(a, b) >= 0

    @staticmethod
    def compare_gt(a, b):
        # NaN comparisons always return false
        import math
        if isinstance(a, float) and math.isnan(a):
            return False
        if isinstance(b, float) and math.isnan(b):
            return False
        return ObjUtil.compare(a, b) > 0

    @staticmethod
    def to_str(obj):
        if obj is None:
            return "null"
        if isinstance(obj, bool):
            return "true" if obj else "false"
        if isinstance(obj, str):
            return obj
        if isinstance(obj, float):
            from .Float import Float
            return Float.to_str(obj)
        if isinstance(obj, int):
            return str(obj)
        if hasattr(obj, "to_str") and callable(getattr(obj, "to_str", None)):
            return obj.to_str()
        return str(obj)

    @staticmethod
    def to_code(obj):
        """Convert object to Fantom code representation"""
        if obj is None:
            return "null"
        if isinstance(obj, bool):
            return "true" if obj else "false"
        if isinstance(obj, str):
            from .Str import Str
            return Str.to_code(obj)
        if isinstance(obj, float):
            # Check if it has a toCode method (e.g., Float or Decimal wrapper)
            if hasattr(obj, "to_code") and callable(getattr(obj, "to_code", None)):
                return obj.to_code()
            # Default: treat Python floats as Float with 'f' suffix
            from .Float import Float
            return Float.to_str(obj) + "f"
        if isinstance(obj, int) and not isinstance(obj, bool):
            return str(obj)
        # Handle lists - use List.toCode static method
        if isinstance(obj, list):
            from .List import List
            return List.to_code(obj)
        # Handle maps - use Map.toCode method
        from .Map import Map
        if isinstance(obj, Map):
            return obj.to_code()
        # Check for toCode method
        if hasattr(obj, "to_code") and callable(getattr(obj, "to_code", None)):
            return obj.to_code()
        return ObjUtil.to_str(obj)

    @staticmethod
    def typeof(obj):
        """Return Fantom Type for object"""
        from .Type import Type
        if obj is None:
            return None
        # Check for Fantom objects with typeof() method
        if hasattr(obj, "typeof") and callable(getattr(obj, "typeof", None)):
            return obj.typeof()
        # Map Python primitives to Fantom types
        if isinstance(obj, bool):
            return Type.find("sys::Bool")
        if isinstance(obj, int):
            return Type.find("sys::Int")
        if isinstance(obj, float):
            return Type.find("sys::Float")
        if isinstance(obj, str):
            return Type.find("sys::Str")
        if isinstance(obj, list):
            # For plain Python lists without type info, infer from contents
            return ObjUtil._infer_list_type(obj)
        if isinstance(obj, dict):
            # For plain Python dicts without type info, return generic Map
            return Type.find("[sys::Obj:sys::Obj?]")
        # For other objects, use Type.of()
        return Type.of(obj)

    @staticmethod
    def _infer_list_type(lst):
        """Infer Fantom list type from list contents"""
        from .Type import Type
        if len(lst) == 0:
            # Empty list - Fantom convention is Obj?[] for untyped empty lists
            return Type.find("sys::Obj?[]")

        # Check if all elements are same type
        first_type = None
        all_same = True
        has_null = False

        for item in lst:
            if item is None:
                has_null = True
                continue
            item_type = ObjUtil.typeof(item)
            if item_type is None:
                continue
            if first_type is None:
                first_type = item_type
            elif first_type.signature() != item_type.signature():
                all_same = False
                break

        if first_type is None:
            # All nulls
            return Type.find("sys::Obj?[]")

        # Use the common type
        sig = first_type.signature()
        if has_null and not sig.endswith("?"):
            sig = sig + "?"
        return Type.find(f"{sig}[]")

    @staticmethod
    def _is_list(obj):
        """Check if obj is a Fantom List (our List class or Python list)"""
        from .List import List
        return isinstance(obj, (list, List))

    @staticmethod
    def _is_map(obj):
        """Check if obj is a Fantom Map"""
        from .Map import Map
        return isinstance(obj, (dict, Map))

    @staticmethod
    def is_(obj, type_):
        """Runtime type check (Fantom 'is' operator)"""
        if obj is None:
            return False

        # Get type qname string
        if hasattr(type_, '_qname'):
            qname = type_._qname
        else:
            qname = str(type_)

        # Check against common types
        if qname == "sys::Obj":
            return True
        if qname == "sys::Num":
            return isinstance(obj, (int, float)) and not isinstance(obj, bool)
        if qname == "sys::Int":
            return isinstance(obj, int) and not isinstance(obj, bool)
        if qname == "sys::Float":
            return isinstance(obj, float)
        if qname == "sys::Bool":
            return isinstance(obj, bool)
        if qname == "sys::Str":
            return isinstance(obj, str)
        if qname == "sys::List":
            return ObjUtil._is_list(obj)
        # Parameterized list types like Obj[], Str[], etc.
        if qname.endswith("[]"):
            if not ObjUtil._is_list(obj):
                return False
            # For explicit type-aware lists, check element type compatibility
            # Otherwise be permissive (like Fantom 'as' behavior)
            from .Type import Type

            # Get list's declared element type
            objElemType = None
            if hasattr(obj, '_elementType') and obj._elementType is not None:
                objElemType = obj._elementType
            elif hasattr(obj, '_of') and obj._of is not None:
                objElemType = obj._of

            # If no declared type, be permissive (like 'as')
            if objElemType is None:
                return True

            targetElemSig = qname[:-2]  # Remove trailing []
            # Handle nullable element types (Str?[], Obj?[])
            targetNullable = targetElemSig.endswith("?")
            if targetNullable:
                targetElemSig = targetElemSig[:-1]  # Remove trailing ?
            targetElemType = Type.find(targetElemSig, False)
            if targetElemType is None:
                return True  # Unknown type, be permissive

            # Check if list's element type FITS target element type
            objElemSig = objElemType.signature() if hasattr(objElemType, 'signature') else str(objElemType)
            objNullable = objElemSig.endswith("?")
            if objNullable:
                objElemSig = objElemSig[:-1]
            objElemTypeBase = Type.find(objElemSig, False)
            if objElemTypeBase is None:
                return True  # Unknown type, be permissive

            # Check if objElemType extends targetElemType
            return objElemTypeBase.fits(targetElemType)
        if qname == "sys::Map":
            return ObjUtil._is_map(obj)
        # Parameterized map types like [Int:Str]
        if qname.startswith("[") and ":" in qname:
            if not ObjUtil._is_map(obj):
                return False
            # Check type parameters for covariance
            # Map<K1,V1> is Map<K2,V2> if K1 extends K2 AND V1 extends V2
            from .Type import Type, MapType
            targetType = Type.find(qname, False)
            if targetType is None or not isinstance(targetType, MapType):
                return ObjUtil._is_map(obj)
            # Get object's map type
            objType = None
            if hasattr(obj, 'typeof'):
                objType = obj.typeof()
            if objType is None or not isinstance(objType, MapType):
                return ObjUtil._is_map(obj)  # Can't verify types, assume ok
            # Check K1 extends K2 (object key type must extend target key type)
            if not objType.k.fits(targetType.k):
                return False
            # Check V1 extends V2 (object value type must extend target value type)
            if not objType.v.fits(targetType.v):
                return False
            return True

        # For other types, check if object's type fits the target type (including inheritance)
        from .Type import Type
        objType = Type.of(obj)
        if objType is None:
            return False
        # Use Type.is_ to check inheritance chain
        targetType = Type.find(qname, False)
        if targetType is None:
            return False
        return objType.is_(targetType)

    @staticmethod
    def as_(obj, type_):
        """Runtime type cast (Fantom 'as' operator) - returns obj if it fits type, else None

        Note: 'as' is more permissive than 'is' for parameterized types.
        An empty [Obj:Obj?] map can be cast to [Int:Int] because there's nothing
        in it that would violate the type constraint.
        """
        if obj is None:
            return None

        # Get type qname string
        if hasattr(type_, '_qname'):
            qname = type_._qname
        else:
            qname = str(type_)

        # For parameterized map types, be permissive (just check if it's a map)
        # Fantom's 'as' allows casting maps to more specific map types
        if qname.startswith("[") and ":" in qname:
            if ObjUtil._is_map(obj):
                return obj
            return None

        # For parameterized list types, be permissive (just check if it's a list)
        if qname.endswith("[]"):
            if ObjUtil._is_list(obj):
                return obj
            return None

        # For other types, use is_ for strict checking
        if ObjUtil.is_(obj, type_):
            return obj
        return None

    @staticmethod
    def coerce(obj, type_):
        """Runtime coercion with error - throws CastErr if obj doesn't fit type"""
        # Get type qname string
        if hasattr(type_, '_qname'):
            qname = type_._qname
        elif isinstance(type_, str):
            qname = type_
        else:
            qname = str(type_)

        # Handle null case
        if obj is None:
            # Null can only be coerced to nullable types (ending with ?)
            if qname.endswith('?'):
                return obj
            # Coercing null to non-nullable type throws NullErr
            from .Err import NullErr
            raise NullErr.make(f"Coerce to non-null: {qname}")

        # Strip nullable suffix for base type check
        base_qname = qname.rstrip('?')

        # Check against common types (primitives)
        if base_qname in ("sys::Obj", "sys::Obj?"):
            return obj
        if base_qname == "sys::Int":
            if isinstance(obj, int) and not isinstance(obj, bool):
                return obj
        elif base_qname == "sys::Float":
            if isinstance(obj, float):
                return obj
        elif base_qname == "sys::Bool":
            if isinstance(obj, bool):
                return obj
        elif base_qname == "sys::Str":
            if isinstance(obj, str):
                return obj
        elif base_qname == "sys::Num":
            if isinstance(obj, (int, float)) and not isinstance(obj, bool):
                return obj
        elif base_qname == "sys::List" or base_qname.endswith("[]"):
            if ObjUtil._is_list(obj):
                return obj
        elif base_qname == "sys::Map" or (base_qname.startswith("[") and ":" in base_qname):
            if isinstance(obj, dict):
                return obj
            from .Map import Map
            if isinstance(obj, Map):
                return obj
        else:
            # Fast path: Check if object's class matches target type exactly
            # This avoids expensive Type.find() and Type.is_() calls for exact matches
            if "::" in base_qname:
                pod_name, type_name = base_qname.split("::", 1)
                cls = obj.__class__
                # Check class name match and module prefix match
                if (cls.__name__ == type_name and
                    cls.__module__.startswith('fan.') and
                    cls.__module__.split('.')[1] == pod_name):
                    return obj

            # Fall back to full type check for inheritance cases
            if ObjUtil.is_(obj, type_):
                return obj
            # Also allow if it's actually the type (direct coerce without strict checking)
            return obj

        # If we get here, type check failed - raise CastErr
        from .Err import CastErr
        objType = ObjUtil.typeof(obj)
        objTypeName = objType.signature() if objType else type(obj).__name__
        raise CastErr.make(f"{objTypeName} cannot be cast to {qname}")

    @staticmethod
    def is_immutable(obj):
        """Check if object is immutable"""
        import types
        if obj is None:
            return True
        if isinstance(obj, (bool, int, float, str)):
            return True
        # Check if object has its own isImmutable method
        # This handles Func instances which track their own immutability
        if hasattr(obj, "is_immutable") and callable(getattr(obj, "is_immutable", None)):
            result = obj.is_immutable()
            if result:
                return True
            # If obj.is_immutable() returns False, still check if the TYPE is const
            # This handles const classes where the transpiler may not have generated is_immutable
        # Python functions/lambdas are considered immutable in Fantom context
        # (const closures in Fantom transpile to Python lambdas/functions)
        if isinstance(obj, (types.FunctionType, types.LambdaType, types.MethodType)):
            return True
        if callable(obj) and hasattr(obj, '__call__'):
            # Generic callable without mutable state marker
            return True
        # Check if object's type is a const class (const classes are inherently immutable)
        from .Type import Type
        try:
            objType = Type.of(obj)
            if objType is not None and objType.is_const():
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def to_immutable(obj):
        """Return immutable version of object"""
        from .Err import NotImmutableErr
        import types
        # Primitives and None are already immutable
        if obj is None:
            return obj
        if isinstance(obj, (bool, int, float, str)):
            return obj
        # Check if already immutable FIRST
        if hasattr(obj, 'is_immutable') and callable(obj.is_immutable):
            if obj.is_immutable():
                return obj
        # Check if object has toImmutable method (List, Map, Func, etc.)
        if hasattr(obj, "to_immutable") and callable(getattr(obj, "to_immutable", None)):
            return obj.to_immutable()
        # Handle plain Python lists (from List.map_, Str.split, etc.)
        if isinstance(obj, list):
            from .List import List
            return List.to_immutable(obj)
        # Check if it's a const type - const types are inherently immutable
        from .Type import Type
        try:
            objType = Type.of(obj)
            if objType is not None and objType.is_const():
                # Const types are inherently immutable
                return obj
        except Exception:
            pass
        # Can't make this object immutable
        raise NotImmutableErr.make(f"Cannot make {type(obj).__name__} immutable")

    @staticmethod
    def to_float(obj):
        """Convert to Float - dispatch to appropriate type"""
        if obj is None:
            return 0.0
        if isinstance(obj, float):
            return obj
        if isinstance(obj, int):
            return float(obj)
        if hasattr(obj, "to_float") and callable(getattr(obj, "to_float", None)):
            return obj.to_float()
        return float(obj)

    @staticmethod
    def to_int(obj):
        """Convert to Int - dispatch to appropriate type"""
        import math
        if obj is None:
            return 0
        if isinstance(obj, int) and not isinstance(obj, bool):
            return obj
        if isinstance(obj, float):
            # Handle special values - Fantom returns maxVal/minVal for infinity
            if math.isnan(obj):
                return 0
            if math.isinf(obj):
                if obj > 0:
                    return 9223372036854775807  # Int.maxVal
                else:
                    return -9223372036854775808  # Int.minVal
            return int(obj)
        if isinstance(obj, bool):
            return 1 if obj else 0
        if hasattr(obj, "to_int") and callable(getattr(obj, "to_int", None)):
            return obj.to_int()
        return int(obj)

    @staticmethod
    def to_decimal(obj):
        """Convert to Decimal - dispatch to appropriate type"""
        if obj is None:
            return 0.0
        if isinstance(obj, float):
            return obj
        if isinstance(obj, int):
            return float(obj)
        if hasattr(obj, "to_decimal") and callable(getattr(obj, "to_decimal", None)):
            return obj.to_decimal()
        return float(obj)

    @staticmethod
    def to_locale(obj, pattern=None, locale=None):
        """Format number according to locale pattern - dispatch to appropriate type"""
        if obj is None:
            return "null"
        if isinstance(obj, float):
            from .Float import Float
            return Float.to_locale(obj, pattern, locale)
        if isinstance(obj, int) and not isinstance(obj, bool):
            from .Int import Int
            return Int.to_locale(obj, pattern, locale)
        if hasattr(obj, "to_locale") and callable(getattr(obj, "to_locale", None)):
            if locale is not None:
                return obj.to_locale(pattern, locale)
            elif pattern is not None:
                return obj.to_locale(pattern)
            else:
                return obj.to_locale()
        return str(obj)

    @staticmethod
    def echo(obj=None):
        """Print to stdout"""
        if obj is None:
            print("")
        else:
            print(ObjUtil.to_str(obj))

    @staticmethod
    def throw_(err):
        """Raise an exception as an expression (used in elvis, ternary, etc.).

        Python's `raise` is a statement, not an expression. This helper
        allows throw to be used in expression context:
            x = v ?: throw ArgErr("boom")
        Transpiles to:
            x = ((lambda _v: _v if _v is not None else ObjUtil.throw_(ArgErr("boom")))(v))
        """
        raise err

    @staticmethod
    def inc_field(obj, fieldName):
        """Increment a field and return new value (for ++field - pre-increment)"""
        val = getattr(obj, fieldName) + 1
        setattr(obj, fieldName, val)
        return val

    @staticmethod
    def inc_field_post(obj, fieldName):
        """Increment a field and return old value (for field++ - post-increment)"""
        old = getattr(obj, fieldName)
        setattr(obj, fieldName, old + 1)
        return old

    @staticmethod
    def dec_field(obj, fieldName):
        """Decrement a field and return new value (for --field - pre-decrement)"""
        val = getattr(obj, fieldName) - 1
        setattr(obj, fieldName, val)
        return val

    @staticmethod
    def dec_field_post(obj, fieldName):
        """Decrement a field and return old value (for field-- - post-decrement)"""
        old = getattr(obj, fieldName)
        setattr(obj, fieldName, old - 1)
        return old

    @staticmethod
    def inc_index(obj, index):
        """Increment a list/array element and return new value (for ++list[i])"""
        val = obj[index] + 1
        obj[index] = val
        return val

    @staticmethod
    def inc_index_post(obj, index):
        """Increment a list/array element and return old value (for list[i]++)"""
        old = obj[index]
        obj[index] = old + 1
        return old

    @staticmethod
    def dec_index(obj, index):
        """Decrement a list/array element and return new value (for --list[i])"""
        val = obj[index] - 1
        obj[index] = val
        return val

    @staticmethod
    def dec_index_post(obj, index):
        """Decrement a list/array element and return old value (for list[i]--)"""
        old = obj[index]
        obj[index] = old - 1
        return old

    @staticmethod
    def div(a, b):
        """Fantom-style integer division (truncated toward zero)
        Python's // uses floor division (toward negative infinity)
        Fantom/Java use truncated division (toward zero)
        Example: -6 / 4 = -1 (truncated), but Python -6 // 4 = -2 (floor)
        """
        # Check if a has a div method (e.g., Duration)
        if hasattr(a, 'div') and callable(a.div):
            return a.div(b)
        if b == 0:
            raise ZeroDivisionError("integer division by zero")
        # Use int() to truncate toward zero instead of //
        return int(a / b)

    @staticmethod
    def mod(a, b):
        """Fantom-style modulo (truncated division, same sign as dividend)
        Python uses floor division modulo (same sign as divisor)
        Fantom/Java use truncated division modulo (same sign as dividend)
        """
        if b == 0:
            return float('nan') if isinstance(a, float) else 0
        # For floats, use math.fmod which gives C/Java style modulo
        if isinstance(a, float) or isinstance(b, float):
            import math
            return math.fmod(float(a), float(b))
        # For ints, truncate towards zero
        return a - int(a / b) * b

    @staticmethod
    def trap(obj, name, args=None):
        """Dynamic method invocation via -> operator

        Args:
            obj: Target object
            name: Method name to invoke
            args: List of arguments (None for no args, list for args)
        """
        # Preserve args as-is (None or list) for Fantom semantics
        # Use (args or []) when we need to spread args for method calls
        call_args = args or []

        # For Int, route to Int.trap
        if isinstance(obj, int) and not isinstance(obj, bool):
            from .Int import Int
            return Int.trap(obj, name, call_args)

        # For Float, route to Float.trap
        if isinstance(obj, float):
            from .Float import Float
            return Float.trap(obj, name, call_args)

        # For Str, route to Str (static methods)
        if isinstance(obj, str):
            from .Str import Str
            method = getattr(Str, name, None)
            if method:
                return method(obj, *call_args)
            raise AttributeError(f"Str.{name}")

        # For list, route to List
        if isinstance(obj, list):
            from .List import List
            method = getattr(List, name, None)
            if method:
                return method(obj, *call_args)
            raise AttributeError(f"List.{name}")

        # For Map, route to Map
        from .Map import Map
        if isinstance(obj, Map):
            method = getattr(obj, name, None)
            if method:
                return method(*call_args) if callable(method) else method
            raise AttributeError(f"Map.{name}")

        # For other types with trap method - pass original args to preserve None/list semantics
        if hasattr(obj, 'trap'):
            return obj.trap(name, args)

        # Try to find method or field directly on object
        attr = getattr(obj, name, None)
        if attr is not None:
            if callable(attr):
                # It's a method - call it
                return attr(*call_args)
            else:
                # It's a field value - if args provided, it's a setter call
                if args:
                    setattr(obj, f"_{name}", args[0])
                    return
                return attr

        # Try Fantom getter/setter pattern (name_ is the accessor method)
        # Generated code uses: def fieldName_(self, _val_=None) for both get and set
        accessor_name = f"{name}_"
        if hasattr(obj, accessor_name):
            accessor = getattr(obj, accessor_name)
            if callable(accessor):
                if args:
                    # Setter call
                    return accessor(args[0])
                else:
                    # Getter call
                    return accessor()

        # Try private field pattern (_fieldName) for direct field access
        priv_name = f"_{name}"
        if hasattr(obj, priv_name):
            if args:
                setattr(obj, priv_name, args[0])
                return
            return getattr(obj, priv_name)

        # Try private field pattern with trailing underscore (_fieldName_)
        priv_name_underscore = f"_{name}_"
        if hasattr(obj, priv_name_underscore):
            if args:
                setattr(obj, priv_name_underscore, args[0])
                return
            return getattr(obj, priv_name_underscore)

        # Try static field/method on the class
        cls = type(obj)
        cls_attr = getattr(cls, name, None)
        if cls_attr is not None:
            if callable(cls_attr):
                # Static method
                return cls_attr(*call_args)
            return cls_attr

        # Use reflection to find slot - this handles fields registered via af_()
        # including static fields that aren't generated as class attributes
        from .Type import Type
        try:
            objType = Type.of(obj)
            if objType is not None:
                slot = objType.slot(name, False)
                if slot is not None:
                    from .Field import Field
                    from .Method import Method
                    if isinstance(slot, Field):
                        if args:
                            # Setting a field via trap
                            slot.set_(obj, args[0])
                            return
                        else:
                            # Getting a field via trap
                            return slot.get(obj) if not slot.is_static() else slot.get()
                    elif isinstance(slot, Method):
                        return slot.call(obj, *call_args) if call_args else slot.call(obj)
        except Exception:
            pass  # Fall through to error

        raise AttributeError(f"trap not supported on {type(obj)}: {name}")

    # Cvar wrapper for closure-captured variables
    class Cvar:
        """Wrapper for closure-captured variables (cvars).

        When a closure modifies a local variable, the transpiler wraps
        the variable in a Cvar so modifications are visible outside
        the closure. Access via ._val attribute.
        """
        __slots__ = ('_val',)

        def __init__(self, val=None):
            self._val = val

    @staticmethod
    def cvar(val=None):
        """Create a cvar wrapper for closure-captured variables.

        Usage in transpiled code:
            x_Wrapper = ObjUtil.cvar(x)  # instead of self.make(x)
        """
        return ObjUtil.Cvar(val)

    @staticmethod
    def setattr_return(obj, field_name, value):
        """Set a field and return the assigned value.

        Implements Fantom assignment-as-expression semantics for field assignments.
        In Fantom (and JavaScript), `x.field = value` is an expression that returns
        the assigned value. Python doesn't support this, so we use this helper
        when the assignment result is needed as an expression value.

        This mirrors the JS transpiler's IIFE pattern:
            ((this$) => { let _temp = rhs; lhs.setter(_temp); return _temp; })(this)

        Args:
            obj: The target object
            field_name: The field name (with _ prefix for direct storage, without for accessor)
            value: The value to assign

        Returns:
            The assigned value (for use as expression result)
        """
        if field_name.startswith('_'):
            # Direct storage access: obj._field = value
            setattr(obj, field_name, value)
        else:
            # Accessor method call: obj.field(value)
            getattr(obj, field_name)(value)
        return value
