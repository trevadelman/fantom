#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Slot import Slot


class Method(Slot):
    """Method reflection - represents a Fantom method for reflection purposes.

    Methods are created either:
    1. By the transpiler via Type.am_() for registered type metadata
    2. Dynamically via Method.find() for runtime method lookup
    """

    def __init__(self, parent=None, name="", flags=0, returns=None, params=None, facets=None, func=None):
        """Create a Method reflection object.

        Args:
            parent: Parent Type
            name: Method name
            flags: Slot flags (FConst values)
            returns: Return Type
            params: List of Param objects
            facets: Dict of facet metadata
            func: Optional Python callable for direct invocation
        """
        super().__init__(parent, name, flags)
        self._returns = returns  # Return type
        self._params = params if params is not None else []  # Parameter list
        self._facets = facets if facets is not None else {}  # Facet metadata
        self._facets_list = None  # Cached list for facets() - for identity comparison
        self._params_list = None  # Cached list for params() - for identity comparison
        self._func = func  # Optional direct callable
        self._method_func = None  # Cached MethodFunc wrapper for identity
        self._resolved_py_name = None  # Cached Python method name for efficient lookup

    def is_method(self):
        return True

    def returns(self):
        """Get return type - lazily resolves from string signature if needed.

        Type resolution is deferred to avoid circular imports during module
        initialization. The returns type is stored as a string by Type.am_()
        and resolved to a Type object on first access.
        """
        if isinstance(self._returns, str):
            from .Type import Type
            self._returns = Type.find(self._returns, False) or Type.find("sys::Obj")
        return self._returns

    def params(self):
        """Get parameter list as Fantom List of Param objects (read-only, cached for identity)"""
        if self._params_list is not None:
            return self._params_list

        from .List import List as FanList
        from .Param import Param
        from .Type import Type
        # Defensive: ensure all params are Param objects (not strings)
        # This handles cases where dynamic discovery may have added strings
        normalized = []
        for p in self._params:
            if isinstance(p, str):
                # Convert string to Param with Obj? type
                normalized.append(Param(p, Type.find("sys::Obj?"), False))
            elif isinstance(p, Param):
                normalized.append(p)
            else:
                normalized.append(p)
        self._params_list = FanList.from_list(normalized, "sys::Param").to_immutable()
        return self._params_list

    def func(self):
        """Get the Func wrapper for this method.

        Returns a cached MethodFunc to preserve identity semantics.
        Multiple calls to func() on the same Method return the same MethodFunc.
        """
        if self._method_func is None:
            self._method_func = MethodFunc(self)
        return self._method_func

    def has_facet(self, facetType):
        """Check if this method has a facet.

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
        facet_qname = facetType.qname() if hasattr(facetType, 'qname') else str(facetType)
        if facet_qname in self._facets:
            facet_data = self._facets[facet_qname]
            return FacetInstance(facetType, facet_data)
        if checked:
            from .Err import ArgErr
            raise ArgErr.make(f"Facet not found: {facetType}")
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
        self._facets_list = FanList.from_literal(result, "sys::Facet").to_immutable()
        return self._facets_list

    def call(self, *args):
        """Call method with variable args.

        For static methods: call(arg1, arg2, ...)
        For instance methods: call(target, arg1, arg2, ...)
        """
        return self._invoke(None, list(args), from_call=True)

    def call_on(self, target, args=None):
        """Call method on a specific target object.

        Args:
            target: Object to call method on (None for static methods)
            args: List of arguments (method args, NOT including target)
        """
        if args is None:
            args = []
        # Convert Fantom List to Python list if needed
        if hasattr(args, '_values'):
            args = list(args._values)
        return self._invoke(target, list(args), from_call_on=True)

    def call_list(self, args):
        """Call method with args from a list.

        For instance methods, first arg should be the target.
        """
        if args is None:
            args = []
        # Convert Fantom List to Python list if needed
        if hasattr(args, '_values'):
            args = list(args._values)
        return self._invoke(None, list(args), from_call=True)

    def _invoke(self, target, args, from_call=False, from_call_on=False):
        """Internal method to invoke the method.

        Handles finding and calling the actual Python method.
        Validates argument count and trims extra arguments.

        Args:
            target: Target object (for callOn) or None
            args: Arguments list
            from_call: True if called from call()/callList()
            from_call_on: True if called from callOn()
        """
        # Get parameter info for validation and trimming
        # Use self.params() to get normalized Param objects (handles string params)
        from .Param import Param
        params = list(self.params()) if self._params else []
        is_static = self.is_static()
        is_ctor = self.is_ctor()

        # Calculate min required args (params without defaults)
        # Defensive: handle params that may not have has_default method
        min_args = sum(1 for p in params if isinstance(p, Param) and not p.has_default())
        max_args = len(params)

        # For call/callList: instance methods expect target as first arg
        # For callOn: target is separate, args are method args only
        # EXCEPTION: Constructors are invoked statically even though they're not marked Static
        actual_target = target
        method_args = args

        if from_call and not is_static and not is_ctor:
            # Instance method via call/callList - first arg is target
            if not args:
                from .Err import ArgErr
                raise ArgErr.make(f"Instance method {self.qname()} requires target object")
            actual_target = args[0]
            method_args = args[1:]
        elif from_call_on:
            # callOn provides target separately
            if not is_static and actual_target is None:
                from .Err import ArgErr
                raise ArgErr.make(f"Instance method {self.qname()} requires target object")

        # Validate minimum required arguments
        if len(method_args) < min_args:
            from .Err import ArgErr
            raise ArgErr.make(f"Method {self.qname()} requires {min_args} arguments, got {len(method_args)}")

        # Trim extra arguments (Fantom allows passing more args than needed)
        if len(method_args) > max_args:
            method_args = method_args[:max_args]

        # If we have a direct func, use it
        if self._func is not None:
            if actual_target is not None and not is_static:
                return self._func(actual_target, *method_args)
            return self._func(*method_args)

        # Try to find the Python class and method
        parent_type = self._parent
        if parent_type is None:
            from .Err import Err
            raise Err.make(f"Method {self._name} has no parent type")

        # Special handling: when calling Obj methods on primitive types,
        # dispatch to the wrapper class's static method instead
        parent_qname = parent_type.qname() if hasattr(parent_type, 'qname') else str(parent_type)
        if parent_qname == "sys::Obj" and actual_target is not None:
            wrapper_cls = self._get_primitive_wrapper_class(actual_target)
            if wrapper_cls is not None:
                method_attr = getattr(wrapper_cls, self._name, None)
                if method_attr is not None and callable(method_attr):
                    return method_attr(actual_target, *method_args)

        # Get the Python class for this type
        py_cls = self._get_python_class(parent_type)

        # Fast path: use cached Python method name if available
        if self._resolved_py_name is not None:
            if py_cls is not None and hasattr(py_cls, self._resolved_py_name):
                method_attr = getattr(py_cls, self._resolved_py_name)
                if is_static or is_ctor:
                    return method_attr(*method_args)
                else:
                    bound_method = getattr(actual_target, self._resolved_py_name, None)
                    if bound_method is not None and callable(bound_method):
                        return bound_method(*method_args)
                    return method_attr(actual_target, *method_args)
            elif actual_target is not None and hasattr(actual_target, self._resolved_py_name):
                method = getattr(actual_target, self._resolved_py_name)
                if callable(method):
                    return method(*method_args)

        # Slow path: resolve Python method name (first call or cache miss)
        from .Type import _camel_to_snake, _PYTHON_BUILTINS
        snake_name = _camel_to_snake(self._name)

        # Also try escaped name for Python builtins (map -> map_, hash -> hash_)
        escaped_name = self._name + '_' if self._name in _PYTHON_BUILTINS else None
        snake_escaped = snake_name + '_' if snake_name in _PYTHON_BUILTINS else None

        # Build list of names to try (most specific to least)
        names_to_try = [self._name]
        if snake_name != self._name:
            names_to_try.append(snake_name)
        if escaped_name:
            names_to_try.append(escaped_name)
        if snake_escaped and snake_escaped not in names_to_try:
            names_to_try.append(snake_escaped)

        if py_cls is None:
            # Fallback: try to call on target directly
            if actual_target is not None:
                for method_name in names_to_try:
                    if hasattr(actual_target, method_name):
                        method = getattr(actual_target, method_name)
                        if callable(method):
                            self._resolved_py_name = method_name  # Cache for next call
                            return method(*method_args)
            from .Err import Err
            raise Err.make(f"Cannot find implementation for {self.qname()}")

        # Check if method exists on the class
        method_attr = None
        actual_method_name = None
        for method_name in names_to_try:
            if hasattr(py_cls, method_name):
                method_attr = getattr(py_cls, method_name)
                actual_method_name = method_name
                self._resolved_py_name = method_name  # Cache for next call
                break

        if method_attr is None:
            # Try to call on target directly
            if actual_target is not None:
                for method_name in names_to_try:
                    if hasattr(actual_target, method_name):
                        method = getattr(actual_target, method_name)
                        if callable(method):
                            self._resolved_py_name = method_name  # Cache for next call
                            return method(*method_args)
            from .Err import Err
            raise Err.make(f"Method {self._name} not found on {parent_type.qname()}")

        if is_static or is_ctor:
            # Static method or constructor - call directly on class
            return method_attr(*method_args)
        else:
            # Instance method - call on target
            bound_method = getattr(actual_target, self._name, None)
            if bound_method is not None and callable(bound_method):
                return bound_method(*method_args)

            # Fallback: try calling class method with target
            return method_attr(actual_target, *method_args)

    def _get_primitive_wrapper_class(self, obj):
        """Get the wrapper class for a Python primitive type.

        When calling Obj methods on native Python primitives (int, str, float, bool),
        we need to dispatch to the appropriate wrapper class's static methods.

        Returns:
            Wrapper class (Int, Str, Float, Bool) or None if not a primitive
        """
        if isinstance(obj, bool):
            # Check bool before int since bool is a subclass of int
            from .Bool import Bool
            return Bool
        if isinstance(obj, int):
            from .Int import Int
            return Int
        if isinstance(obj, float):
            from .Float import Float
            return Float
        if isinstance(obj, str):
            from .Str import Str
            return Str
        return None

    def _get_python_class(self, type_obj):
        """Get the Python class for a Fantom type."""
        if type_obj is None:
            return None

        qname = type_obj.qname() if hasattr(type_obj, 'qname') else str(type_obj)

        # Map of known types to their Python runtime classes
        if qname.startswith("sys::"):
            type_name = qname[5:]  # Remove "sys::"
            try:
                # Import from fan.sys module
                module = __import__(f'fan.sys.{type_name}', fromlist=[type_name])
                return getattr(module, type_name, None)
            except ImportError:
                pass

        # Try to import from the pod
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

    def to_str(self):
        return self.qname()

    @staticmethod
    def find(qname, checked=True):
        """Find method by qualified name like 'sys::Str.toInt'.

        Args:
            qname: Qualified name like 'pod::Type.method'
            checked: If True, raise error if not found

        Returns:
            Method instance or None
        """
        from .Slot import Slot
        slot = Slot.find(qname, checked)
        if slot is None:
            return None
        if isinstance(slot, Method):
            return slot
        # Also accept parameterized method wrappers (from ListType, MapType, FuncType)
        # These are method-like objects that wrap a generic Method with type substitution
        if hasattr(slot, 'returns') and hasattr(slot, 'params') and hasattr(slot, 'name'):
            return slot
        if checked:
            from .Err import CastErr
            raise CastErr.make(f"{qname} is not a method")
        return None


class MethodFunc:
    """Wraps a Method as a Func for reflection.

    This allows Method.func() to return a Func-like object
    that can be called and has parameter metadata.
    """

    def __init__(self, method):
        self._method = method

    def params(self):
        """Get parameters including 'this' for instance methods (read-only)."""
        from .List import List as FanList
        method_params = self._method.params()

        # For instance methods, prepend 'this' parameter
        if not self._method.is_static():
            from .Param import Param
            this_param = Param("this", self._method.parent(), False)
            all_params = [this_param] + list(method_params)
            return FanList.from_list(all_params, "sys::Param").to_immutable()

        return method_params

    def returns(self):
        """Get return type."""
        return self._method.returns()

    def call(self, *args):
        """Call the underlying method."""
        return self._method.call(*args)

    def __call__(self, *args):
        """Make MethodFunc callable like a regular function."""
        return self._method.call(*args)

    def call_on(self, target, args=None):
        """Call the underlying method on target."""
        return self._method.call_on(target, args)

    def call_list(self, args):
        """Call the underlying method with args list."""
        return self._method.call_list(args)

    def arity(self):
        """Number of parameters."""
        return len(self.params())

    def is_immutable(self):
        """Funcs are always immutable."""
        return True

    def typeof(self):
        """Get the FuncType for this method's signature.

        Returns a FuncType like |Int,Str->Bool| based on the
        method's parameter types and return type.

        Note: Does NOT include 'this' - the func type represents the
        method's declared signature without the implicit receiver.
        """
        from .Type import Type

        # Get parameter types from the method directly (NOT including 'this')
        # The func signature doesn't include the implicit receiver
        param_types = []
        for param in self._method.params():
            param_types.append(param.type())

        # Get return type
        returns = self._method.returns()
        if returns is None:
            returns = Type.find("sys::Void")

        # Build signature and get/create cached FuncType
        sig = self._build_signature(param_types, returns)
        return Type.find(sig)

    def _build_signature(self, param_types, returns):
        """Build function type signature like |sys::Int,sys::Str->sys::Bool|"""
        params_sig = ",".join(p.signature() for p in param_types)
        return f"|{params_sig}->{returns.signature()}|"

    def bind(self, args):
        """Bind arguments to create a new Func with partial application.

        Args:
            args: List of arguments to bind (starting from first param)

        Returns:
            New Func with bound arguments and remaining parameters
        """
        if args is None:
            args = []
        bound_args = list(args)

        # If binding empty list, return self (identity)
        if len(bound_args) == 0:
            return self

        original_method = self._method

        # Create bound function that prepends bound_args
        def bound_func(*more_args):
            all_args = bound_args + list(more_args)
            return original_method.call(*all_args)

        # Get remaining params after binding
        all_params = self.params()
        remaining_params = all_params[len(args):]

        # Create new Func with bound implementation
        from .Func import Func
        result = Func(bound_func, self.returns(), remaining_params)

        # Determine immutability - depends on whether bound args are immutable
        from .ObjUtil import ObjUtil
        all_immutable = True
        for arg in bound_args:
            if not ObjUtil.is_immutable(arg):
                all_immutable = False
                break

        # Set _bound_immutable (checked by Func.is_immutable())
        result._bound_immutable = all_immutable

        return result

    def method(self):
        """Return the underlying Method."""
        return self._method

    def to_immutable(self):
        """Return immutable version - MethodFuncs are already immutable."""
        return self

    def retype(self, t):
        """Return MethodFunc with different type signature.

        The returned MethodFunc retains the same underlying method
        but reports a different type signature.
        """
        from .Func import Func
        from .Param import Param
        from .Type import Type, FuncType, NullableType

        # Unwrap nullable types - |Int->Str|? is a nullable FuncType
        inner_type = t
        if isinstance(t, NullableType):
            inner_type = t.to_non_nullable()

        # Get returns and params from the target type
        new_returns = None
        new_params = []

        if hasattr(inner_type, 'returns'):
            ret = inner_type.returns()
            # Keep as Type object, not string
            new_returns = ret

        # For FuncType, _params is a list of Type objects (parameter types)
        # Access via _params property since Type.params() returns generic params map
        if isinstance(inner_type, FuncType):
            for i, p in enumerate(inner_type._params):
                # Each p is a Type - create Param from it
                new_params.append(Param(f'_p{i}', p))
        elif hasattr(inner_type, 'params') and callable(inner_type.params):
            for i, p in enumerate(inner_type.params()):
                if hasattr(p, 'type'):  # It's a Param
                    new_params.append(p)
                else:  # It's a Type - create Param from it
                    new_params.append(Param(f'_p{i}', p))

        # Create a RetypedMethodFunc wrapper
        return RetypedMethodFunc(self._method, new_returns, new_params)


class RetypedMethodFunc(MethodFunc):
    """A MethodFunc with a different type signature.

    This preserves the method() reference while allowing
    retype() to change the reported signature.
    """

    def __init__(self, method, returns, params):
        super().__init__(method)
        self._retype_returns = returns
        self._retype_params = params

    def params(self):
        """Get retyped parameters."""
        return self._retype_params

    def returns(self):
        """Get retyped return type."""
        return self._retype_returns

    def typeof(self):
        """Get the retyped FuncType."""
        from .Type import Type

        # Collect param type signatures
        param_sigs = []
        for param in self._retype_params:
            # Param has type() method, Type has signature() directly
            if hasattr(param, 'type') and callable(param.type):
                pt = param.type()
                if pt is not None and hasattr(pt, 'signature'):
                    param_sigs.append(pt.signature())
                else:
                    param_sigs.append('sys::Obj?')
            elif hasattr(param, 'signature'):
                param_sigs.append(param.signature())
            else:
                param_sigs.append(str(param))

        # Get return type signature
        returns = self._retype_returns
        if returns is None:
            ret_sig = 'sys::Void'
        elif isinstance(returns, str):
            ret_sig = returns
        elif hasattr(returns, 'signature'):
            ret_sig = returns.signature()
        else:
            ret_sig = str(returns)

        params_sig = ",".join(param_sigs)
        sig = f"|{params_sig}->{ret_sig}|"
        return Type.find(sig)
