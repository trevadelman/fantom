#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

class Obj:
    """Base class for all Fantom objects"""

    _hash_counter = 0

    def __init__(self):
        Obj._hash_counter += 1
        self._hash = Obj._hash_counter

    def equals(self, that):
        return self is that

    def hash(self):
        # Lazily initialize _hash if not set (subclasses may not call super().__init__())
        if not hasattr(self, '_hash'):
            Obj._hash_counter += 1
            self._hash = Obj._hash_counter
        return self._hash

    def compare(self, that):
        """Compare this object to that for ordering.

        Default implementation checks equals() first, then uses string representation.
        Subclasses can override for custom ordering.
        Returns -1 if this < that, 0 if equal, 1 if this > that.
        """
        if self is that:
            return 0
        if that is None:
            return 1
        # If objects are equal by value, compare as 0
        if self.equals(that):
            return 0
        # Fall back to string comparison for consistent ordering
        my_str = self.to_str() if hasattr(self, 'to_str') else str(self)
        that_str = that.to_str() if hasattr(that, 'to_str') else str(that)
        if my_str < that_str:
            return -1
        if my_str > that_str:
            return 1
        return 0

    def __lt__(self, other):
        """Python < operator - delegates to compare()"""
        return self.compare(other) < 0

    def __le__(self, other):
        """Python <= operator - delegates to compare()"""
        return self.compare(other) <= 0

    def __gt__(self, other):
        """Python > operator - delegates to compare()"""
        return self.compare(other) > 0

    def __ge__(self, other):
        """Python >= operator - delegates to compare()"""
        return self.compare(other) >= 0

    def to_str(self):
        return f"{type(self).__name__}@{self._hash}"

    def typeof(self):
        """Return Fantom Type for this object"""
        # Import here to avoid circular dependency
        from .Type import Type
        # Get class name and try to find pod from module
        cls = type(self)
        class_name = cls.__name__
        module = cls.__module__

        # Parse pod from module path (e.g., 'fan.sys.Range' -> 'sys')
        if module.startswith('fan.'):
            parts = module.split('.')
            if len(parts) >= 2:
                py_pod = parts[1]  # e.g., 'sys', 'testSys', 'def_'
                # Convert Python pod name to Fantom pod name (e.g., 'def_' -> 'def')
                pod = Type._py_pod_to_fantom(py_pod)
                return Type.find(f"{pod}::{class_name}")

        # Default to sys pod
        return Type.find(f"sys::{class_name}")

    def is_immutable(self):
        """Check if this object is immutable.

        Delegates to typeof().is_const() - objects of const classes are always immutable.
        This matches the JavaScript reference implementation:
          isImmutable() { return this.typeof().is_const(); }
        """
        t = self.typeof()
        if t is not None and hasattr(t, 'is_const'):
            return t.is_const()
        return False

    def trap(self, name, args=None):
        """Dynamic method invocation (Fantom -> operator)

        This is the base implementation for Fantom's trap method.
        Subclasses can override to intercept dynamic calls.
        """
        # Keep args as-is (None or list) to match Fantom semantics
        # Only spread args for method calls

        # Try to find method or field directly on object
        attr = getattr(self, name, None)
        if attr is not None:
            if callable(attr):
                # Check if this is a getter being used as setter (args provided)
                # In this case, set the backing field instead
                if args:
                    priv_name = f"_{name}"
                    if hasattr(self, priv_name):
                        setattr(self, priv_name, args[0])
                        return args[0]
                    # Fall through to try calling with args
                return attr(*(args or []))
            else:
                # It's a field value - if args provided, it's a setter call
                if args:
                    setattr(self, f"_{name}", args[0])
                    return args[0]
                return attr

        # Try Fantom getter/setter pattern (name_ is the accessor method)
        # Generated code uses: def fieldName_(self, _val_=None) for both get and set
        accessor_name = f"{name}_"
        if hasattr(self, accessor_name):
            accessor = getattr(self, accessor_name)
            if callable(accessor):
                if args:
                    # Setter call
                    return accessor(args[0])
                else:
                    # Getter call
                    return accessor()

        # Try private field pattern (_fieldName)
        priv_name = f"_{name}"
        if hasattr(self, priv_name):
            if args:
                setattr(self, priv_name, args[0])
                return args[0]
            return getattr(self, priv_name)

        # Try private field pattern with trailing underscore (_fieldName_)
        priv_name_underscore = f"_{name}_"
        if hasattr(self, priv_name_underscore):
            if args:
                setattr(self, priv_name_underscore, args[0])
                return args[0]
            return getattr(self, priv_name_underscore)

        # Try static field/method on the class
        cls = type(self)
        cls_attr = getattr(cls, name, None)
        if cls_attr is not None:
            if callable(cls_attr):
                return cls_attr(*(args or []))
            return cls_attr

        # Use reflection to find slot
        from .Type import Type
        try:
            objType = Type.of(self)
            if objType is not None:
                slot = objType.slot(name, False)
                if slot is not None:
                    from .Field import Field
                    from .Method import Method
                    if isinstance(slot, Field):
                        if args:
                            slot.set_(self, args[0])
                            return args[0]
                        else:
                            return slot.get(self) if not slot.is_static() else slot.get()
                    elif isinstance(slot, Method):
                        return slot.call(self, *args) if args else slot.call(self)
        except Exception:
            pass

        from .Err import UnknownSlotErr
        raise UnknownSlotErr(f"{Type.of(self)}.{name}")

    def with_(self, f):
        f(self)
        return self

    # Constructor field-setting support methods
    # These are called by generated code from ConstChecks compiler step
    # for closures (it-blocks) that set const fields. In Python, closures
    # capture 'self' from the outer class, not the Func, so these need
    # to be available on all objects.
    def enter_ctor(self, obj):
        """Called when entering a constructor with an it-block"""
        pass

    def exit_ctor(self):
        """Called when exiting a constructor with an it-block"""
        pass

    def check_in_ctor(self, obj):
        """Called to verify we're in a constructor when setting const fields"""
        pass

    def __str__(self):
        return self.to_str()

    def __eq__(self, other):
        return self.equals(other)

    def __hash__(self):
        return self.hash()

    def __repr__(self):
        return self.to_str()

    @staticmethod
    def echo(obj=None):
        """Print to stdout - Fantom's Obj.echo() static method"""
        from .ObjUtil import ObjUtil
        ObjUtil.echo(obj)
