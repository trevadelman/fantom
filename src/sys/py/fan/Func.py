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

        Throws ArgErr if more args provided than the function accepts.
        """
        from .Err import ArgErr

        if args is None:
            args = []

        # Convert to list if needed - ListImpl extends Python list
        bound_args = list(args) if args else []

        # If no args to bind, return self (identity)
        if len(bound_args) == 0:
            return self

        # Validate arg count - cannot bind more args than params
        if len(bound_args) > len(self._params):
            raise ArgErr.make(f"Func.bind more args than params: {len(bound_args)} > {len(self._params)}")

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
        """Return immutable version of this Func with proper snapshot semantics.

        The behavior depends on the compiler-determined immutability case:
        - "always": return self (already immutable)
        - "never": throw NotImmutableErr
        - "maybe": create a copy with toImmutable() called on captured values

        Implementation uses types.CellType (Python 3.8+) to create new closure
        cells with immutable values, providing true snapshot semantics like Java.
        """
        from .Err import NotImmutableErr
        import types

        immut_case = getattr(self, '_immutable_case', None)

        if immut_case == 'always':
            return self

        if immut_case == 'never':
            raise NotImmutableErr.make("Closure captures non-const value")

        # Already immutable? Return self
        if getattr(self, '_is_immutable', False):
            return self

        from .ObjUtil import ObjUtil
        from .Type import Type

        # Get the original function
        original_func = self._func
        if original_func is None:
            raise NotImmutableErr.make("Cannot make Func immutable")

        # APPROACH 1: Cell rebinding using types.CellType (Python 3.8+)
        # This creates true snapshot semantics by making new closure cells
        if (hasattr(original_func, '__closure__') and
            original_func.__closure__ and
            hasattr(types, 'CellType')):

            # Get variable names for better error messages
            freevars = original_func.__code__.co_freevars

            # Make all captured values immutable and create new cells
            immutable_cells = []
            for i, cell in enumerate(original_func.__closure__):
                varname = freevars[i] if i < len(freevars) else f"capture[{i}]"
                try:
                    val = cell.cell_contents
                    immutable_val = ObjUtil.to_immutable(val)
                    # Create new cell with immutable value
                    new_cell = types.CellType(immutable_val)
                    immutable_cells.append(new_cell)
                except NotImmutableErr as e:
                    # Re-raise with context about which capture failed
                    raise NotImmutableErr.make(
                        f"Closure capture '{varname}' not immutable: {Type.of(val)}"
                    )
                except Exception as e:
                    raise NotImmutableErr.make(
                        f"Cannot make closure capture '{varname}' immutable: {e}"
                    )

            # Create new function with new closure cells
            new_func = types.FunctionType(
                original_func.__code__,
                original_func.__globals__,
                original_func.__name__,
                original_func.__defaults__,
                tuple(immutable_cells)  # New closure with immutable values!
            )

            result = Func(new_func, self._returns, self._params, immutable=True)
            result._immutable_case = 'maybe'
            result._is_immutable = True
            return result

        # APPROACH 2: Default parameter rebinding (_outer=self pattern)
        # The transpiler captures 'this' via default parameters
        if hasattr(original_func, '__defaults__') and original_func.__defaults__:
            # Get parameter names for better error messages
            code = original_func.__code__
            varnames = code.co_varnames[:code.co_argcount]
            num_defaults = len(original_func.__defaults__)
            default_names = varnames[-num_defaults:] if num_defaults <= len(varnames) else []

            immutable_defaults = []
            for i, d in enumerate(original_func.__defaults__):
                varname = default_names[i] if i < len(default_names) else f"default[{i}]"
                try:
                    immutable_defaults.append(ObjUtil.to_immutable(d))
                except NotImmutableErr as e:
                    raise NotImmutableErr.make(
                        f"Closure default '{varname}' not immutable: {Type.of(d)}"
                    )
                except Exception as e:
                    raise NotImmutableErr.make(
                        f"Cannot make closure default '{varname}' immutable: {e}"
                    )

            # Create new function with immutable defaults
            new_func = types.FunctionType(
                original_func.__code__,
                original_func.__globals__,
                original_func.__name__,
                tuple(immutable_defaults),
                original_func.__closure__
            )

            result = Func(new_func, self._returns, self._params, immutable=True)
            result._immutable_case = 'maybe'
            result._is_immutable = True
            return result

        # APPROACH 3: No captures - closure is already immutable
        # Just mark it and return self
        self._is_immutable = True
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
