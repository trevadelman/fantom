#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Func(Obj):
    """Function/closure type"""

    def __init__(self, func=None, returns=None, params=None, immutable=False):
        super().__init__()
        self._func = func
        self._returns = returns
        self._params = params or []
        self._immutable = immutable  # Track if explicitly made immutable

    def returns(self):
        """Get return type - returns Type object"""
        from .Type import Type
        if self._returns is None:
            return Type.find('sys::Void')
        if isinstance(self._returns, str):
            return Type.find(self._returns)
        return self._returns

    def params(self):
        """Get parameter list - returns read-only List of Param"""
        from .List import List
        # Return cached read-only list
        if hasattr(self, '_params_ro') and self._params_ro is not None:
            return self._params_ro
        # Create read-only list from params
        param_list = List.from_literal(self._params if self._params else [], 'sys::Param')
        self._params_ro = List.ro(param_list)
        return self._params_ro

    def arity(self):
        """Get number of parameters"""
        return len(self._params)

    def __call__(self, *args):
        """Make Func callable with regular Python syntax

        In Fantom, extra arguments beyond arity are silently ignored.
        """
        if self._func is None:
            raise NotImplementedError("Func has no implementation")
        # Only pass as many args as the function expects (Fantom ignores extras)
        arity = len(self._params)
        truncated = args[:arity] if arity > 0 else args[:1] if args else ()
        # For truly zero-param closures (lambda _=None:), pass at most 1 arg
        if arity == 0 and len(args) > 0:
            # Lambda has _=None default, but we shouldn't pass anything
            return self._func()
        return self._func(*truncated)

    def call(self, *args):
        """Call the function"""
        return self.__call__(*args)

    def call_list(self, args):
        """Call with args from list

        In Fantom, extra arguments beyond arity are silently ignored.
        """
        if args is None:
            args = []
        if self._func is None:
            raise NotImplementedError("Func has no implementation")
        # Truncate to arity - Fantom ignores extra args
        arity = len(self._params)
        if arity > 0:
            args = list(args)[:arity]
        return self._func(*args)

    def call_on(self, target, args=None):
        """Call on target with args

        In Fantom, target becomes first arg, then args list.
        Extra arguments beyond arity are silently ignored.
        """
        if args is None:
            args = []
        if self._func is None:
            raise NotImplementedError("Func has no implementation")
        # Combine target + args, then truncate to arity
        arity = len(self._params)
        all_args = [target] + list(args)
        if arity > 0:
            all_args = all_args[:arity]
        return self._func(*all_args)

    def bind(self, args):
        """Bind arguments to create a new Func

        In Fantom, bind([]) returns the same function (identity).
        bind() with args creates a new function with those args pre-bound.
        """
        if args is None:
            args = []

        # Convert to list if needed - ListImpl extends Python list
        bound_args = list(args) if args else []

        # If no args to bind, return self (identity)
        if len(bound_args) == 0:
            return self

        original_func = self._func
        remaining_params = self._params[len(bound_args):]

        def bound(*more_args):
            return original_func(*(bound_args + list(more_args)))

        # Track immutability - bound func is immutable only if all bound args are immutable
        from .ObjUtil import ObjUtil
        all_immutable = all(ObjUtil.is_immutable(arg) for arg in bound_args)

        result = Func(bound, self._returns, remaining_params)
        result._bound_immutable = all_immutable and self.is_immutable()
        return result

    def retype(self, t):
        """Return Func with different type signature (for type checking only)
        The returned Func has the new type signature but same underlying function
        """
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
            # t.params() may return Type objects or Param objects
            for i, p in enumerate(inner_type.params()):
                if hasattr(p, 'type'):  # It's a Param
                    new_params.append(p)
                else:  # It's a Type - create Param from it
                    new_params.append(Param(f'_p{i}', p))

        return Func(self._func, new_returns, new_params)

    def is_immutable(self):
        """Return whether this Func is immutable.

        The Fantom compiler's ClosureToImmutable step analyzes each closure:
        - "always": captures only const types -> always immutable
        - "never": captures non-const types (e.g., InStream, mutable this) -> never immutable
        - "maybe": captures types like Obj?, List that can be made immutable at runtime

        For "maybe" case, the closure starts as not immutable but can become
        immutable by calling toImmutable() which creates a copy with immutable captures.
        """
        # Check if compiler provided immutability case
        immut_case = getattr(self, '_immutable_case', None)
        if immut_case == 'always':
            return True
        if immut_case == 'never':
            return False
        if immut_case == 'maybe':
            # Check if this instance has been made immutable
            return getattr(self, '_is_immutable', False)

        # Check if this is a bound function with immutability tracking
        if hasattr(self, '_bound_immutable'):
            return self._bound_immutable

        # Legacy fallback - default to True for backwards compatibility
        return True

    def to_immutable(self):
        """Return immutable version of this Func.

        The behavior depends on the compiler-determined immutability case:
        - "always": return self (already immutable)
        - "never": throw NotImmutableErr
        - "maybe": create a copy with toImmutable() called on captured values

        KNOWN LIMITATION (Python runtime):
        ===================================
        In Java/JVM, the compiler generates closure classes with a custom
        toImmutable() method that calls make() with immutable copies of all
        fields. This creates a true snapshot of captured values.

        In Python, closures are native functions with __closure__ cells that
        we cannot easily rebind. We use an ARITY-BASED HEURISTIC:

        - Arity 0 closures (e.g., |->Obj| { list }):
          Assumed to be "value-returning" - we create a new closure that
          returns the immutable copy of the captured value.

        - Arity 1+ closures (e.g., |msg->Obj?| { f(msg) }):
          Assumed to be "behavior" closures (like Actor receives) - we verify
          all captures are/can-be immutable, then use the original function.
          The original still references the same (now verified immutable) objects.

        Edge cases that may not work correctly:
        1. Arity-0 closures that do more than return a value (have side effects)
        2. Arity-1+ closures that capture mutable data expecting snapshot semantics

        If these patterns cause issues, the proper fix is to have the Python
        transpiler generate closures as classes with proper toImmutable() methods
        (similar to the Java approach). See: fan/src/compiler/fan/steps/ClosureToImmutable.fan
        """
        from .Err import NotImmutableErr

        immut_case = getattr(self, '_immutable_case', None)

        if immut_case == 'always':
            return self

        if immut_case == 'never':
            raise NotImmutableErr.make("Closure captures non-const value")

        if immut_case == 'maybe':
            # Already immutable? Return self
            if getattr(self, '_is_immutable', False):
                return self

            from .ObjUtil import ObjUtil

            # Get the original function
            original_func = self._func
            if original_func is None:
                raise NotImmutableErr.make("Cannot make Func immutable")

            # Get arity for the heuristic decision
            arity = len(self._params)

            # For closures with __closure__ (Python lexical capture)
            if hasattr(original_func, '__closure__') and original_func.__closure__:
                try:
                    # First, make all captured values immutable (or verify they can be)
                    immutable_vals = []
                    for cell in original_func.__closure__:
                        val = cell.cell_contents
                        immutable_vals.append(ObjUtil.to_immutable(val))

                    # ARITY-BASED HEURISTIC:
                    # - Arity 0: Value-returning closure like |->Obj| { list }
                    #   Create new closure that returns immutable snapshot
                    # - Arity 1+: Behavior closure like |msg| { f(msg) }
                    #   Use original function (captures verified immutable)

                    if arity == 0 and len(immutable_vals) == 1:
                        # Value-returning closure: create new function returning immutable value
                        captured = immutable_vals[0]
                        def new_func_arity0():
                            return captured
                        new_func = new_func_arity0
                    else:
                        # Behavior closure or complex captures:
                        # Use original function - captures have been verified immutable.
                        # NOTE: The original still references the same objects, but since
                        # we verified they're immutable, this is safe for concurrent use.
                        new_func = original_func

                    # Create new Func instance
                    result = Func(new_func, self._returns, self._params, immutable=True)
                    result._immutable_case = 'maybe'
                    result._is_immutable = True
                    return result
                except Exception:
                    raise NotImmutableErr.make("Cannot make closure immutable")

            # For closures using default parameters (_outer=self pattern)
            if hasattr(original_func, '__defaults__') and original_func.__defaults__:
                try:
                    immutable_defaults = tuple(
                        ObjUtil.to_immutable(d) for d in original_func.__defaults__
                    )

                    # Create new function with immutable defaults
                    import types
                    new_func = types.FunctionType(
                        original_func.__code__,
                        original_func.__globals__,
                        original_func.__name__,
                        immutable_defaults,
                        original_func.__closure__
                    )

                    result = Func(new_func, self._returns, self._params, immutable=True)
                    result._immutable_case = 'maybe'
                    result._is_immutable = True
                    return result
                except Exception:
                    raise NotImmutableErr.make("Cannot make closure immutable")

            # No captured values - already immutable
            self._is_immutable = True
            return self

        # Legacy fallback - Funcs are immutable by default
        return self

    def typeof(self):
        """Return the FuncType for this Func - enables Type.of() to return proper signature"""
        from .Type import Type
        sig = self.to_str()  # e.g., |sys::Int,sys::Str->sys::Bool|
        return Type.find(sig)

    def to_str(self):
        return self.signature()

    def signature(self):
        """Return the function signature like |sys::Int,sys::Str->sys::Bool|
        Note: Fantom signatures include only types, not parameter names
        """
        # Get just the type signature for each param (not "type name" format)
        param_types = []
        for p in self._params:
            if hasattr(p, 'type') and callable(p.type):
                pt = p.type()
                if pt is not None:
                    if hasattr(pt, 'signature'):
                        param_types.append(pt.signature())
                    else:
                        param_types.append(str(pt))
                else:
                    param_types.append('sys::Obj?')
            elif hasattr(p, '_type') and p._type is not None:
                if hasattr(p._type, 'signature'):
                    param_types.append(p._type.signature())
                else:
                    param_types.append(str(p._type))
            else:
                param_types.append('sys::Obj?')
        params_str = ','.join(param_types)

        # Handle returns - could be Type object or string
        if self._returns is None:
            ret_str = 'sys::Void'
        elif hasattr(self._returns, 'signature'):
            ret_str = self._returns.signature()
        else:
            ret_str = str(self._returns)
        return f"|{params_str}->{ret_str}|"

    @staticmethod
    def make(func):
        """Wrap a Python callable in a Func"""
        return Func(func)

    @staticmethod
    def make_closure(spec, func):
        """Create a Func with type metadata (mirrors JS fan.sys.Func.make$closure)

        Args:
            spec: dict with 'returns' (type signature) and 'params' (list of param info)
            func: the Python callable (lambda or function)
        """
        from .Param import Param  # Late import to avoid circular dependency
        from .Type import Type  # Late import to avoid circular dependency
        from .ObjUtil import ObjUtil  # Late import to avoid circular dependency

        returns = spec.get('returns')
        params_info = spec.get('params', [])

        # Convert param info to Param objects with proper Type instances
        params = []
        for p in params_info:
            if isinstance(p, dict):
                type_sig = p.get('type', 'sys::Obj?')
                param_type = Type.find(type_sig)
                params.append(Param(p.get('name', ''), param_type))
            elif isinstance(p, Param):
                params.append(p)

        result = Func(func, returns, params)

        # Set immutability case from compiler analysis
        # Values: "always", "never", "maybe"
        immut_case = spec.get('immutable')
        if immut_case:
            result._immutable_case = immut_case

        return result
