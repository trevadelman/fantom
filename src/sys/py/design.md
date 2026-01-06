This is a "living" document covering many aspects of the design and implementation
for the mapping from Fantom to Python.

# Getting Started

The Python implementation of the `sys` pod is in `src/sys/py/fan/`. Unlike JavaScript
which bundles into a single file, Python uses individual `.py` files that match Python's
module import system.

The Python transpiler lives in the `fanc` pod at `src/fanc/fan/py/`. It generates Python
code from Fantom source and outputs to `gen/py/`.

## fanc py (Python Transpiler)

The Python transpiler is invoked via `fanc py <pod>`. It serves the same purpose as
`compilerEs` for JavaScript, but emits Python 3 code.

```bash
# Transpile testSys pod to Python
fanc py testSys

# Transpile haystack pod
fanc py haystack
```

Generated code is output to `<fan_home>/gen/py/fan/<podName>/`.

## Standard Build

To build the Python natives into pod files:

```bash
fan src/sys/py/build.fan compile        # Package natives into sys.pod
fan src/concurrent/py/build.fan compile # Package into concurrent.pod
fan src/util/py/build.fan compile       # Package into util.pod
```

This packages Python natives inside `.pod` files at `/py/fan/<podName>/`, matching the
JavaScript pattern of `/esm/` and `/cjs/` directories.

## Running Tests

To run transpiled Python code:

```bash
# Transpile a pod
fanc py testSys

# Copy natives from src/sys/py/fan/ to gen/py/fan/sys/
# Then run with Python 3
python3 -c "from fan.testSys.BoolTest import BoolTest; BoolTest().testDefVal()"
```

# Porting Native Code

If you have a pod with native Python implementations, follow these steps:

1. Create a `/py/` directory in the root of your pod (peer to any existing `/js/` or `/es/`)
2. For `sys` pod specifically, create `/py/fan/` subdirectory (matches import path)
3. Port native code into this directory following the patterns below
4. Use the existing code in `sys/py/fan/` or `concurrent/py/` as reference

Native files are named to match the Fantom type they implement (e.g., `List.py` for `sys::List`).

# Design

This section details the design decisions and implementation patterns for Python code.

## Python Classes

All Fantom types are implemented as Python classes extending `Obj`.

Fantom:
```fantom
class Foo { }
```

Python:
```python
from fan.sys.Obj import Obj

class Foo(Obj):
    def __init__(self):
        super().__init__()
```

The compiler auto-generates import statements for pod dependencies. Cross-pod types are
imported at the top of the file. Same-pod types use dynamic imports to avoid circular
import issues (see [Circular Imports](#circular-imports) below).

## Fields

All Fantom fields are generated with private storage using the `_fieldName` convention.
The compiler generates a combined getter/setter method using Python's optional parameter pattern.

Fantom:
```fantom
class Foo
{
  Int a := 0
  Int b := 1 { private set }
  private Int c := 2
}
```

Python:
```python
class Foo(Obj):
    def __init__(self):
        super().__init__()
        self._a = 0
        self._b = 1
        self._c = 2

    # Public getter/setter
    def a(self, _val_=None):
        if _val_ is None:
            return self._a
        else:
            self._a = _val_

    # Public getter only
    def b(self):
        return self._b

    # No method for _c (private getter/setter)
```

Usage:
```python
f = Foo()
f.a(100)       # Set
print(f.a())   # Get: 100
```

Note: Unlike JavaScript's `#private` fields, Python uses the `_fieldName` convention by
agreement rather than enforcement.

## Static Fields

Static fields use class-level storage with static getter methods. Lazy initialization
follows the same pattern as JavaScript to handle circular dependencies.

Fantom:
```fantom
class Foo
{
  static const Int max := 100
}
```

Python:
```python
class Foo(Obj):
    _max = None

    @staticmethod
    def max():
        if Foo._max is None:
            Foo._static_init()
        return Foo._max

    @staticmethod
    def _static_init():
        if hasattr(Foo, '_static_init_in_progress') and Foo._static_init_in_progress:
            return
        Foo._static_init_in_progress = True
        Foo._max = 100
        Foo._static_init_in_progress = False
```

## Enums

Enums follow a factory pattern with lazy singleton initialization.

Fantom:
```fantom
enum class Color { red, green, blue }
```

Python:
```python
class Color(Obj):
    _vals = None

    @staticmethod
    def red():
        return Color.vals().get(0)

    @staticmethod
    def green():
        return Color.vals().get(1)

    @staticmethod
    def blue():
        return Color.vals().get(2)

    @staticmethod
    def vals():
        if Color._vals is None:
            Color._vals = List.toImmutable(List.fromList([
                Color._make_enum(0, "red"),
                Color._make_enum(1, "green"),
                Color._make_enum(2, "blue")
            ]))
        return Color._vals

    @staticmethod
    def _make_enum(_ordinal, _name):
        inst = object.__new__(Color)
        inst._ordinal = _ordinal
        inst._name = _name
        return inst

    def ordinal(self):
        return self._ordinal

    def name(self):
        return self._name
```

## Funcs and Closures

Fantom closures are generated as Python lambdas wrapped in `Func.makeClosure()` to provide
Fantom's Func API (`bind()`, `params()`, `returns()`, etc.).

Fantom:
```fantom
list.each |item, i| { echo(item) }
```

Python:
```python
List.each(list, Func.makeClosure({
    "returns": "sys::Void",
    "params": [{"name": "item", "type": "sys::Obj"}, {"name": "i", "type": "sys::Int"}]
}, (lambda item=None, i=None: print(item))))
```

For simple single-expression closures, the lambda is inlined. For multi-statement closures,
a named function is emitted before the usage point.

Unlike JavaScript where closures are invoked directly (`f(args)`), Python closures through
`Func.makeClosure()` are also callable directly - the wrapper implements `__call__`.

## Primitives

Python's type system differs significantly from JavaScript's. Fantom primitives map as follows:

| Fantom | Python | Notes |
|--------|--------|-------|
| `Int` | `int` | Python int is arbitrary precision |
| `Float` | `float` | IEEE 754 double |
| `Bool` | `bool` | `True`/`False` |
| `Str` | `str` | Unicode string |
| `Decimal` | `float` | Uses Python float (not decimal.Decimal) |

Since Python primitives don't have methods, instance method calls on primitives are converted
to static method calls:

Fantom:
```fantom
x.toStr
s.size
```

Python:
```python
Int.toStr(x)
Str.size(s)
```

**Important:** `List` and `Map` are **NOT** primitives. They use normal instance method
dispatch like any other Fantom class. This matches the JavaScript transpiler's design.

The `ObjUtil` class provides dispatch for methods that may be called on any type (`equals`,
`compare`, `hash`, `typeof`, etc.).

## List and Map Architecture

**List** extends `Obj` and implements Python's `MutableSequence` ABC:
- Uses `self._values` for internal storage (not inheriting from Python list)
- All methods are instance methods: `list.each(f)`, `list.map_(f)`, etc.
- `isinstance(fantom_list, list)` returns `False`
- Supports Python protocols: `len()`, `[]`, `in`, iteration

**Map** extends `Obj` and implements Python's `MutableMapping` ABC:
- Uses `self._map` for internal storage (not inheriting from Python dict)
- All methods are instance methods: `map.get(k)`, `map.each(f)`, etc.
- `isinstance(fantom_map, dict)` returns `False`
- Supports Python protocols: `len()`, `[]`, `in`, iteration

Fantom:
```fantom
list.each |item| { echo(item) }
map.get("key")
```

Python:
```python
list.each(lambda item: print(item))
map.get("key")
```

## Circular Imports

Python's import system can cause `ImportError` when modules reference each other. The
transpiler handles this with dynamic imports for same-pod type references:

```python
# Instead of: from fan.testSys.ObjWrapper import ObjWrapper
# Use:
__import__('fan.testSys.ObjWrapper', fromlist=['ObjWrapper']).ObjWrapper
```

Cross-pod imports are placed at the top of the file since pods are built in dependency order.

## Type Metadata (Reflection)

Each transpiled type registers metadata for Fantom's reflection system using `af_()` for
fields and `am_()` for methods:

```python
# Type metadata registration for reflection
from fan.sys.Param import Param
_t = Type.find('testSys::Foo')
_t.af_('name', 1, 'sys::Str', {})
_t.am_('doSomething', 1, 'sys::Void', [Param('arg', Type.find('sys::Int'), False)], {})
```

# Naming

All class names are preserved when going from Fantom to Python.

Slot and parameter names that conflict with Python keywords are "pickled" to end with `_`.
The list includes: `class`, `def`, `return`, `if`, `else`, `for`, `while`, `import`, `from`,
`is`, `in`, `not`, `and`, `or`, `True`, `False`, `None`, `lambda`, `global`, `nonlocal`,
`pass`, `break`, `continue`, `raise`, `try`, `except`, `finally`, `with`, `as`, `assert`,
`yield`, `del`, `elif`, `exec`, `print`.

```
# Fantom
Void class(Str is) { ... }

# Python
def class_(self, is_):
    ...
```

Internal methods and fields used for compiler support use double-underscore prefix patterns
like `_static_init`, `_ctor_init`, etc. These should be considered private implementation
details.

# Python-Specific Considerations

## The GIL

Python's Global Interpreter Lock (GIL) means true parallelism isn't possible with threads.
The `concurrent` pod's Actor model implementation uses Python's `concurrent.futures` but
won't achieve the same parallelism as JVM or JavaScript runtimes.

## No Method Overloading

Python doesn't support method overloading by signature. Fantom constructors with different
signatures are handled via factory methods (`make`, `make1`, etc.) that all delegate to a
single `__init__`.

## Duck Typing vs Static Types

Fantom is statically typed; Python is dynamically typed. The transpiled Python code doesn't
include type hints (though this could be added in the future). Runtime type checks use
`ObjUtil.is_()` and `ObjUtil.as_()`.

## None vs null

Fantom's `null` maps directly to Python's `None`. Nullable types (`Str?`) don't have special
representation - any variable can hold `None`.
