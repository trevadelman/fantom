# Python Developer's Guide

A guide for Python developers using transpiled Fantom libraries (Haystack, Xeto, etc.).

> **Note:** This guide is for Python developers *consuming* Fantom APIs.
> For information on how the transpiler generates Python code, see `design.md`.

## Quick Start

```python
import sys
sys.path.insert(0, 'fan/gen/py')

from fan.sys.List import List
from fan.sys.Map import Map

# Create a Fantom list
nums = List.fromLiteral([1, 2, 3], "sys::Int")

# Use instance methods (natural OO style)
doubled = nums.map_(lambda it: it * 2)
# Result: [2, 4, 6]

# Python protocols work
len(nums)           # 3
nums[0]             # 1
for x in nums:      # iteration
    print(x)
```

## Using Lambdas and Functions

Fantom methods that accept closures work with any Python callable:

### Lambda
```python
List.map_(nums, lambda it: it * 2)
List.findAll(nums, lambda it: it % 2 == 0)
List.find(nums, lambda it: it > 3)
```

### Named Function
```python
def multiply_by_2(x):
    return x * 2

List.map_(nums, multiply_by_2)
```

### Multi-line Logic
```python
def complex_filter(item):
    if item < 0:
        return False
    if item > 100:
        return False
    return item % 2 == 0

List.findAll(nums, complex_filter)
```

## Type Interoperability

### List

Fantom's `List` extends `Obj` and implements Python's `MutableSequence` protocol.
It wraps an internal Python list but is **not** a subclass of Python's `list`.

```python
nums = List.fromLiteral([1, 2, 3], "sys::Int")

# Instance methods (preferred - natural OO style)
nums.map_(lambda it: it * 2)           # [2, 4, 6]
nums.findAll(lambda it: it > 1)        # [2, 3]
nums.reduce(0, lambda acc, it: acc + it)  # 6

# Python protocols work
len(nums)           # 3
nums[0]             # 1
nums[-1]            # 3
3 in nums           # True
for x in nums:      # iteration works
    print(x)

# Note: List is NOT a Python list
isinstance(nums, list)  # False
isinstance(nums, List)  # True
```

### Map

Fantom's `Map` extends `Obj` and implements Python's `MutableMapping` protocol.
It wraps an internal Python dict but is **not** a subclass of Python's `dict`.

```python
from fan.sys.Map import Map

m = Map.fromLiteral(["a", "b"], [1, 2], "sys::Str", "sys::Int")

# Instance methods
m.each(lambda v, k: print(f"{k}={v}"))
m.get("a")          # 1
m.containsKey("a")  # True

# Python protocols work
len(m)              # 2
m["a"]              # 1
"a" in m            # True

# Note: Map is NOT a Python dict
isinstance(m, dict)  # False
isinstance(m, Map)   # True
```

### Primitives

Fantom primitives map to Python types:

| Fantom | Python | Notes |
|--------|--------|-------|
| `Int` | `int` | Arbitrary precision |
| `Float` | `float` | IEEE 754 |
| `Bool` | `bool` | `True`/`False` |
| `Str` | `str` | Unicode |
| `null` | `None` | Nullable values |

Fantom methods on primitives are called as static methods:

```python
from fan.sys.Int import Int
from fan.sys.Str import Str

# Int methods
Int.times(3, lambda i: print(i))  # 0, 1, 2
Int.toHex(255)                     # "ff"

# Str methods
Str.size("hello")                  # 5
Str.upper("hello")                 # "HELLO"
```

## Instance Methods (Recommended)

Lists created with `List.fromLiteral()` support instance methods for a more natural OO style:

```python
from fan.sys.List import List

nums = List.fromLiteral([1, 2, 3, 4, 5], "sys::Int")

# Transform
nums.map(lambda it: it * 2)              # [2, 4, 6, 8, 10]
nums.flatMap(lambda it: [it, it * 2])    # flatten nested results
nums.mapNotNull(lambda it: it if it > 2 else None)

# Filter/Find
nums.find(lambda it: it > 3)             # 4
nums.findAll(lambda it: it % 2 == 0)     # [2, 4]
nums.findIndex(lambda it: it > 3)        # 3
nums.exclude(lambda it: it < 3)          # [3, 4, 5]

# Predicates
nums.any(lambda it: it > 4)              # True
nums.all(lambda it: it > 0)              # True

# Aggregate
nums.reduce(0, lambda acc, it: acc + it) # 15
nums.min()                                # 1
nums.max()                                # 5
nums.join(", ")                           # "1, 2, 3, 4, 5"

# Sort
nums.sort(lambda a, b: b - a)            # descending
nums.sortr()                              # reverse order
nums.shuffle()                            # random order
nums.reverse()                            # reverse in place

# Iteration
nums.each(lambda it: print(it))
nums.each(lambda it, i: print(f"{i}: {it}"))

# Accessors
nums.first()                              # 1
nums.last()                               # 5
nums.isEmpty()                            # False
nums.contains(3)                          # True
nums.index(3)                             # 2

# Modification
nums.add(6)                               # append
nums.insert(0, 0)                         # insert at index
nums.remove(3)                            # remove first occurrence
nums.removeAt(0)                          # remove at index

# Stack operations
nums.push(6)                              # same as add
nums.pop()                                # remove and return last
nums.peek()                               # return last without removing
```

## Common API Patterns

### List Operations (Static Methods)

Static methods are also available for all list operations:

```python
from fan.sys.List import List

nums = List.fromLiteral([1, 2, 3, 4, 5], "sys::Int")

# Transform
List.map_(nums, lambda it: it * 2)           # [2, 4, 6, 8, 10]

# Filter
List.findAll(nums, lambda it: it % 2 == 0)   # [2, 4]
List.find(nums, lambda it: it > 3)           # 4

# Aggregate
List.reduce(nums, 0, lambda acc, it: acc + it)  # 15
List.any(nums, lambda it: it > 4)            # True
List.all(nums, lambda it: it > 0)            # True

# Sort
List.sort(nums, lambda a, b: b - a)          # descending

# Iterate
List.each(nums, lambda it: print(it))
List.each(nums, lambda it, i: print(f"{i}: {it}"))  # with index
```

### Map Operations

```python
from fan.sys.Map import Map

m = Map.fromLiteral(["a", "b", "c"], [1, 2, 3], "sys::Str", "sys::Int")

# Iterate
m.each(lambda v, k: print(f"{k}={v}"))

# Transform
m.map_(lambda v, k: v * 2)

# Filter
m.findAll(lambda v, k: v > 1)
```

### Int Operations

```python
from fan.sys.Int import Int

# Repeat N times
Int.times(5, lambda i: print(i))

# Range iteration
Int.times(10, lambda i: do_something(i))
```

## Two-Argument Closures

Many Fantom methods support closures with both value and index:

```python
# Value only
List.each(nums, lambda it: print(it))

# Value and index
List.each(nums, lambda it, i: print(f"{i}: {it}"))

# Map: value and key
m.each(lambda v, k: print(f"{k}={v}"))
```

## Error Handling

Fantom errors map to Python exceptions:

```python
from fan.sys.Err import Err, ArgErr, NullErr

try:
    # Fantom code that might throw
    result = some_fantom_api()
except ArgErr as e:
    print(f"Invalid argument: {e}")
except NullErr as e:
    print(f"Null value: {e}")
except Err as e:
    print(f"Fantom error: {e}")
```

## Importing Types

Cross-pod imports:

```python
# Core sys types
from fan.sys.List import List
from fan.sys.Map import Map
from fan.sys.Type import Type

# Haystack types (after transpiling)
from fan.haystack.Dict import Dict
from fan.haystack.Grid import Grid

# Xeto types (after transpiling)
from fan.xeto.Spec import Spec
```

## Further Reading

- `design.md` - How the transpiler generates Python code
- `development_guide.md` - Contributing to the transpiler
- Fantom documentation at https://fantom.org/doc/
