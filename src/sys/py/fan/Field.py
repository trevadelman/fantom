#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Slot import Slot


class Field(Slot):
    """Field reflection - represents a Fantom field for reflection purposes.

    Fields are created either:
    1. By the transpiler via Type.af_() for registered type metadata
    2. Dynamically via Field.find() for runtime field lookup
    """

    def __init__(self, parent=None, name="", flags=0, type_=None, facets=None, setter_flags=None):
        """Create a Field reflection object.

        Args:
            parent: Parent Type
            name: Field name
            flags: Slot flags (FConst values) - also used for getter
            type_: Field Type
            facets: Dict of facet metadata
            setter_flags: Separate flags for setter visibility (if different from field flags)
        """
        super().__init__(parent, name, flags)
        self._type = type_  # Field type
        self._facets = facets if facets is not None else {}  # Facet metadata
        self._facets_list = None  # Cached list for facets() - for identity comparison
        # If setter_flags not provided, use field flags (same visibility for getter/setter)
        self._setter_flags = setter_flags if setter_flags is not None else flags

    def isField(self):
        return True

    def type(self):
        """Get field type."""
        return self._type

    def type_(self):
        """Alias for type() - Fantom compatible."""
        return self._type

    def getter(self):
        """Get the synthetic getter method for this field.

        Returns a FieldGetter that acts like a Method with appropriate
        signature: returns the field type, takes no params.

        For enum value fields, returns None (they don't have getters).
        """
        # Enum value fields don't have getters - the Enum flag is 0x00000020
        if self._flags & 0x00000020:  # FConst.Enum
            return None
        if not hasattr(self, '_getter'):
            self._getter = FieldGetter(self)
        return self._getter

    def setter(self):
        """Get the synthetic setter method for this field.

        Returns a FieldSetter that acts like a Method with appropriate
        signature: returns Void, takes one param of field type.

        For enum value fields, returns None (they don't have setters).
        """
        # Enum value fields don't have setters - the Enum flag is 0x00000020
        if self._flags & 0x00000020:  # FConst.Enum
            return None
        if not hasattr(self, '_setter'):
            self._setter = FieldSetter(self)
        return self._setter

    def get(self, obj=None):
        """Get field value from object.

        Args:
            obj: Object to get field from (None for static fields)

        Returns:
            Field value
        """
        if self.isStatic():
            # Static field - get from class
            py_cls = self._get_python_class()
            if py_cls is not None:
                # Try private field FIRST to avoid circular init via getter methods
                # This handles cases where static init iterates fields before getters work
                field_name = f"_{self._name}"
                if hasattr(py_cls, field_name):
                    val = getattr(py_cls, field_name)
                    if val is not None:
                        return val
                # Try with trailing underscore for Python reserved words (_fieldName_)
                field_name2 = f"_{self._name}_"
                if hasattr(py_cls, field_name2):
                    val = getattr(py_cls, field_name2)
                    if val is not None:
                        return val
                # Try static getter method (e.g., Kind.obj() for field 'obj')
                if hasattr(py_cls, self._name):
                    attr = getattr(py_cls, self._name)
                    if callable(attr):
                        try:
                            return attr()  # Static getter method
                        except Exception:
                            pass  # Getter failed (possibly circular init), continue
                    else:
                        return attr
            return None

        if obj is None:
            return None

        # Instance field - try getter method with trailing underscore first (transpiler pattern)
        # Transpiled code generates: def map_(self, _val_=None) for field 'map'
        getter_name = f"{self._name}_"
        if hasattr(obj, getter_name):
            attr = getattr(obj, getter_name)
            if callable(attr):
                return attr()  # Getter method

        # Try getter method without trailing underscore (Fantom pattern)
        if hasattr(obj, self._name):
            attr = getattr(obj, self._name)
            if callable(attr):
                return attr()  # Getter method
            return attr

        # Try private field pattern with trailing underscore (_fieldName_)
        # Transpiled code stores fields as: self._map_ for field 'map'
        field_name2 = f"_{self._name}_"
        if hasattr(obj, field_name2):
            return getattr(obj, field_name2)

        # Try private field pattern without trailing underscore (_fieldName)
        field_name = f"_{self._name}"
        if hasattr(obj, field_name):
            return getattr(obj, field_name)

        return None

    def set(self, obj, val, check_const=True):
        """Set field value on object.

        Args:
            obj: Object to set field on (None for static fields)
            val: Value to set
            check_const: If True, raise error for const fields
        """
        # Check const constraint
        if check_const and self.isConst():
            from .Err import ReadonlyErr
            raise ReadonlyErr.make(f"Cannot set const field {self.qname()}")

        if self.isStatic():
            # Static field - set on class
            py_cls = self._get_python_class()
            if py_cls is not None:
                # Try with trailing underscore first (_fieldName_)
                field_name2 = f"_{self._name}_"
                if hasattr(py_cls, field_name2):
                    setattr(py_cls, field_name2, val)
                    return
                field_name = f"_{self._name}"
                setattr(py_cls, field_name, val)
            return

        if obj is None:
            return

        # Try setter accessor method with trailing underscore first (transpiler pattern)
        # Transpiled code generates: def map_(self, _val_=None) for field 'map'
        setter_name = f"{self._name}_"
        if hasattr(obj, setter_name):
            attr = getattr(obj, setter_name)
            if callable(attr):
                # Check if method accepts a value parameter (combined getter/setter)
                import inspect
                try:
                    sig = inspect.signature(attr)
                    # If method takes any parameters (besides self), it's a setter
                    if len(sig.parameters) > 0:
                        attr(val)  # Call setter method with value
                        return
                except (ValueError, TypeError):
                    pass

        # Try setter accessor method without trailing underscore (Fantom pattern)
        if hasattr(obj, self._name):
            attr = getattr(obj, self._name)
            if callable(attr):
                import inspect
                try:
                    sig = inspect.signature(attr)
                    if len(sig.parameters) > 0:
                        attr(val)
                        return
                except (ValueError, TypeError):
                    pass

        # Fallback: Set the private field directly with trailing underscore (_fieldName_)
        field_name2 = f"_{self._name}_"
        if hasattr(obj, field_name2):
            setattr(obj, field_name2, val)
            return

        # Try without trailing underscore (_fieldName pattern)
        field_name = f"_{self._name}"
        setattr(obj, field_name, val)

    def _get_python_class(self):
        """Get the Python class for the parent type."""
        if self._parent is None:
            return None

        qname = self._parent.qname() if hasattr(self._parent, 'qname') else str(self._parent)

        if qname.startswith("sys::"):
            type_name = qname[5:]  # Remove "sys::"
            try:
                module = __import__(f'fan.sys.{type_name}', fromlist=[type_name])
                return getattr(module, type_name, None)
            except ImportError:
                pass

        if "::" in qname:
            parts = qname.split("::")
            if len(parts) == 2:
                pod, name = parts
                try:
                    module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                    return getattr(module, name, None)
                except ImportError:
                    pass

        return None

    def hasFacet(self, facetType):
        """Check if this field has a facet.

        Args:
            facetType: Type of facet to check for

        Returns:
            True if facet is present, False otherwise
        """
        facet_qname = facetType.qname() if hasattr(facetType, 'qname') else str(facetType)
        return facet_qname in self._facets

    def facet(self, facetType, checked=True):
        """Get facet value.

        Args:
            facetType: Type of facet to get
            checked: If True, raise error if not found

        Returns:
            Facet instance or None
        """
        from .Type import FacetInstance
        from .Err import UnknownFacetErr
        facet_qname = facetType.qname() if hasattr(facetType, 'qname') else str(facetType)
        if facet_qname in self._facets:
            facet_data = self._facets[facet_qname]
            # Empty dict = marker facet -> return defVal singleton
            if len(facet_data) == 0:
                try:
                    pod = facet_qname.split('::')[0]
                    name = facet_qname.split('::')[1]
                    module = __import__(f'fan.{pod}.{name}', fromlist=[name])
                    cls = getattr(module, name)
                    return cls.defVal()
                except Exception as e:
                    # Fall back to FacetInstance
                    return FacetInstance(facetType, facet_data)
            return FacetInstance(facetType, facet_data)
        if checked:
            raise UnknownFacetErr.make(f"Unknown facet: {facet_qname}")
        return None

    def facets(self):
        """Return list of all facets.

        Returns:
            Immutable List of Facet instances (cached for identity comparison)
        """
        if self._facets_list is not None:
            return self._facets_list

        from .Type import Type, FacetInstance
        from .List import List as FanList
        result = []
        for facet_qname, facet_data in self._facets.items():
            facet_type = Type.find(facet_qname, True)
            result.append(FacetInstance(facet_type, facet_data))
        # Return immutable Fantom List with Facet element type
        self._facets_list = FanList.fromLiteral(result, "sys::Facet").toImmutable()
        return self._facets_list

    def toStr(self):
        return self.qname()

    @staticmethod
    def find(qname, checked=True):
        """Find field by qualified name like 'sys::Str.size'.

        Args:
            qname: Qualified name like 'pod::Type.field'
            checked: If True, raise error if not found

        Returns:
            Field instance or None
        """
        from .Slot import Slot
        slot = Slot.find(qname, checked)
        if slot is None:
            return None
        if isinstance(slot, Field):
            return slot
        if checked:
            from .Err import CastErr
            raise CastErr.make(f"{qname} is not a field")
        return None

    @staticmethod
    def makeSetFunc(field_vals):
        """Create a function that sets multiple fields on an object.

        Args:
            field_vals: Map of Field to value

        Returns:
            A Func that takes an object and sets all the specified fields
        """
        from .Func import Func
        from .Param import Param
        from .Type import Type

        # Convert to list of (field, value) pairs
        if hasattr(field_vals, 'each'):
            # Fantom Map - use each to iterate
            # NOTE: Fantom Map.each has signature |V, K| (value first, key second)
            pairs = []
            def collect(v, k):
                pairs.append((k, v))  # Append as (field, value)
            field_vals.each(collect)
        elif hasattr(field_vals, 'items'):
            # Python dict-like
            pairs = list(field_vals.items())
        else:
            pairs = list(field_vals)

        def setter(obj):
            for field, value in pairs:
                field.set(obj, value, check_const=False)

        # Wrap in Func object with proper signature: |Obj->Void|
        return Func(setter, Type.find("sys::Void"), [Param("it", Type.find("sys::Obj"))])


class FieldGetter:
    """Synthetic getter method for a field.

    Acts like a Method with:
    - name: field name
    - returns: field type
    - params: empty (just 'this' implicit)
    - flags: same as field
    """

    def __init__(self, field):
        self._field = field

    def name(self):
        return self._field.name()

    def qname(self):
        return self._field.qname()

    def parent(self):
        return self._field.parent()

    def returns(self):
        """Getter returns the field type."""
        return self._field.type()

    def params(self):
        """Getter takes no params (implicit 'this')."""
        return []

    def isMethod(self):
        return True

    def isField(self):
        return False

    # Delegate flag methods to field
    def isPublic(self):
        return self._field.isPublic()

    def isProtected(self):
        return self._field.isProtected()

    def isPrivate(self):
        return self._field.isPrivate()

    def isInternal(self):
        return self._field.isInternal()

    def isStatic(self):
        return self._field.isStatic()

    def isVirtual(self):
        return self._field.isVirtual()

    def call(self, *args):
        """Call the getter - get field value from target."""
        if args:
            return self._field.get(args[0])
        return self._field.get()

    def callList(self, args):
        """Call with args list."""
        if args and len(args) > 0:
            return self._field.get(args[0])
        return self._field.get()


class FieldSetter:
    """Synthetic setter method for a field.

    Acts like a Method with:
    - name: field name
    - returns: Void
    - params: [field type]
    - flags: may differ from getter (e.g., private set)

    Uses _setter_flags from the field for visibility checks, which may differ
    from the field's main flags when field has different getter/setter visibility
    (e.g., 'Int x { private set }' - field is public, setter is private)
    """

    # FConst flag values for visibility checking
    _PUBLIC = 0x00000001
    _PRIVATE = 0x00000002
    _PROTECTED = 0x00000004
    _INTERNAL = 0x00000008
    _STATIC = 0x00000800
    _VIRTUAL = 0x00001000

    def __init__(self, field):
        self._field = field

    def name(self):
        return self._field.name()

    def qname(self):
        return self._field.qname()

    def parent(self):
        return self._field.parent()

    def returns(self):
        """Setter returns Void."""
        from .Type import Type
        return Type.find("sys::Void")

    def params(self):
        """Setter takes one param of field type."""
        from .Param import Param
        return [Param("it", self._field.type(), False)]

    def isMethod(self):
        return True

    def isField(self):
        return False

    # Use setter-specific flags for visibility checks
    def isPublic(self):
        return bool(self._field._setter_flags & self._PUBLIC)

    def isProtected(self):
        return bool(self._field._setter_flags & self._PROTECTED)

    def isPrivate(self):
        return bool(self._field._setter_flags & self._PRIVATE)

    def isInternal(self):
        return bool(self._field._setter_flags & self._INTERNAL)

    def isStatic(self):
        # Static is same for getter/setter, use field's value
        return self._field.isStatic()

    def isVirtual(self):
        # Virtual is same for getter/setter, use field's value
        return self._field.isVirtual()

    def call(self, *args):
        """Call the setter - set field value on target."""
        if len(args) >= 2:
            self._field.set(args[0], args[1])
        elif len(args) == 1:
            self._field.set(None, args[0])

    def callList(self, args):
        """Call with args list."""
        if args and len(args) >= 2:
            self._field.set(args[0], args[1])
        elif args and len(args) == 1:
            self._field.set(None, args[0])
