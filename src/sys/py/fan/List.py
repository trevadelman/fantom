#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#
# Refactored to extend Obj + MutableSequence
#

from collections.abc import MutableSequence
from .Obj import Obj


class List(Obj, MutableSequence):
    """Fantom List - extends Obj, implements Python's MutableSequence ABC.

    This follows tjhe architecture where List is a pure Fantom class that
    extends sys::Obj and wraps an internal Python list rather than inheriting
    from Python's list directly.
    """

    def __init__(self, of_type=None, items=None, capacity=None):
        """Create a new List.

        Args:
            of_type: The Fantom element type (Type object or string signature)
            items: Optional initial items
            capacity: Optional capacity hint
        """
        # Note: Don't call Obj.__init__ as Obj doesn't define __init__
        self._values = list(items) if items else []
        self._elementType = of_type
        self._listType = None
        self._capacity = capacity if capacity is not None else len(self._values)
        self._roView = None
        self._of = None

    #################################################################
    # ABC Required Methods (MutableSequence)
    #################################################################

    def __getitem__(self, index):
        """Get item at index - supports int and slice"""
        if isinstance(index, slice):
            result = List(self._elementType, self._values[index])
            result._listType = self._listType
            return result
        return self._values[index]

    def __setitem__(self, index, value):
        """Set item at index"""
        self._check_readonly()
        self._values[index] = value

    def __delitem__(self, index):
        """Delete item at index"""
        self._check_readonly()
        del self._values[index]

    def __len__(self):
        """Return number of elements"""
        return len(self._values)

    def insert(self, index, value):
        """Insert item at index - ABC required method.
        Returns self for method chaining (Fantom style).
        """
        self._check_readonly()
        self._values.insert(index, value)
        if len(self._values) > self._capacity:
            self._capacity = len(self._values)
        self._roView = None
        return self

    #################################################################
    # Additional Python Protocol Methods
    #################################################################

    def __iter__(self):
        """Support iteration"""
        return iter(self._values)

    def __contains__(self, item):
        """Support 'in' operator"""
        from .ObjUtil import ObjUtil
        for x in self._values:
            if ObjUtil.equals(x, item):
                return True
        return False

    def __hash__(self):
        """Make List hashable for use as map keys (like Fantom immutable lists)"""
        try:
            return hash(tuple(self._values))
        except TypeError:
            return id(self)

    def __repr__(self):
        return f"List({self._values})"

    def __str__(self):
        return self.to_str()

    def __eq__(self, other):
        """Equality comparison"""
        from .ObjUtil import ObjUtil
        if other is self:
            return True
        if not hasattr(other, '__len__') or not hasattr(other, '__getitem__'):
            return False
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if not ObjUtil.equals(self._values[i], other[i]):
                return False
        return True

    def equals(self, other):
        """Fantom equals - delegates to __eq__"""
        return self.__eq__(other)

    #################################################################
    # Read-only Check
    #################################################################

    def _check_readonly(self):
        """Check if list is readonly - override in subclasses"""
        pass  # Base List is always read-write

    #################################################################
    # Static Factory Methods (for transpiler backward compatibility)
    #################################################################

    @staticmethod
    def make(of, values=None, capacity=None):
        """Create a typed list with element type.

        Args:
            of: The Fantom element type (Type object or string signature)
            values: Optional list of initial values
            capacity: Optional capacity hint
        """
        from .Type import Type
        if of is None:
            from .Err import NullErr
            raise NullErr("of not defined")
        if values is None or isinstance(values, (int, Type)):
            values = []
        return List.from_literal(list(values), of)

    @staticmethod
    def from_literal(values, elementType):
        """Create type-aware list from literal values.

        Args:
            values: List of values
            elementType: The Fantom element type (Type object or string signature)
        """
        from .Type import Type

        result = List(None, values)

        # Convert string signature to Type object if needed
        if isinstance(elementType, str):
            elementType = Type.find(elementType)
        elif not hasattr(elementType, 'signature'):
            elementType = Type.of(elementType) if elementType is not None else Type.find("sys::Obj")

        result._elementType = elementType
        try:
            result._listType = Type.find(elementType.signature() + "[]")
        except:
            result._listType = Type.find("sys::Obj[]")
        return result

    @staticmethod
    def from_list(values, elementType=None):
        """Create a List from a Python list"""
        if elementType is None:
            elementType = "sys::Obj"
        return List.from_literal(list(values), elementType)

    #################################################################
    # Type/Reflection Methods
    #################################################################

    def typeof(self):
        """Return Fantom Type for this List"""
        from .Type import Type
        if self._listType is not None:
            return self._listType
        return Type.find("sys::List")

    def of(self):
        """Return element type"""
        if self._of is not None:
            return self._of
        return self._elementType

    #################################################################
    # Size/Capacity Properties
    #################################################################

    @property
    def size(self):
        """Return number of elements"""
        return len(self._values)

    @size.setter
    def size(self, val):
        """Set size - grows or shrinks list"""
        self._check_readonly()
        current = len(self._values)
        if val > current:
            elemType = self._elementType
            if elemType is not None:
                sig = elemType.signature() if hasattr(elemType, 'signature') else str(elemType)
                if not sig.endswith("?"):
                    from .Err import ArgErr
                    raise ArgErr(f"Cannot grow non-nullable list {sig}[] from {current} to {val}")
            if val > self._capacity:
                self._capacity = val
            for _ in range(val - current):
                self._values.append(None)
        elif val < current:
            del self._values[val:]

    @property
    def capacity(self):
        """Return capacity"""
        return self._capacity

    @capacity.setter
    def capacity(self, val):
        """Set capacity"""
        self._check_readonly()
        if val < len(self._values):
            from .Err import ArgErr
            raise ArgErr(f"Cannot set capacity {val} below size {len(self._values)}")
        self._capacity = val

    def is_empty(self):
        """Return true if list is empty"""
        return len(self._values) == 0

    #################################################################
    # Read-only/Immutable Methods
    #################################################################

    def is_ro(self):
        """Return true if this list is read-only"""
        return False

    def is_rw(self):
        """Return true if this list is read-write"""
        return True

    def is_immutable(self):
        """Return true if this list is immutable"""
        return False

    def ro(self):
        """Return read-only view of this list"""
        if self._roView is not None:
            return self._roView
        ro_view = ReadOnlyList(self)
        ro_view._elementType = self._elementType
        ro_view._listType = self._listType
        ro_view._of = self._of
        self._roView = ro_view
        return ro_view

    def rw(self):
        """Return read-write version - this is already read-write"""
        return self

    def to_immutable(self):
        """Return immutable version of this list"""
        from .ObjUtil import ObjUtil
        from .Type import Type
        from .Err import NotImmutableErr
        immutable_items = []
        for i, item in enumerate(self._values):
            if item is None:
                immutable_items.append(None)
            elif ObjUtil.is_immutable(item):
                immutable_items.append(item)
            elif hasattr(item, 'to_immutable') and callable(item.to_immutable):
                immutable_items.append(item.to_immutable())
            else:
                # Item cannot be made immutable - throw NotImmutableErr (matches JS impl)
                raise NotImmutableErr.make(f"Item [{i}] not immutable {Type.of(item)}")
        result = ImmutableList(None, immutable_items)
        result._elementType = self._elementType
        result._listType = self._listType
        result._of = self._of
        return result

    #################################################################
    # Accessor Methods
    #################################################################

    def get(self, index, default=None):
        """Get element at index with optional default"""
        if default is not None:
            if 0 <= index < len(self._values):
                return self._values[index]
            return default
        return self._values[index]

    def get_safe(self, index, default=None):
        """Get element or default if out of bounds"""
        n = len(self._values)
        if index < 0:
            index = n + index
        if 0 <= index < n:
            return self._values[index]
        return default

    def first(self):
        """Get first element or null"""
        return self._values[0] if self._values else None

    def last(self):
        """Get last element or null"""
        return self._values[-1] if self._values else None

    def get_range(self, r_or_target=None, r=None):
        """Get a slice using a Range.

        Can be called as:
        - List.get_range(target, range) - static dispatch from transpiler
        - list.get_range(range) - instance method call

        Delegates to target's getRange method if target is not a List.
        """
        from .Range import Range

        # When transpiler generates List.get_range(target, range):
        # Python binds: self=target, r_or_target=range, r=None

        # When called as instance method list.get_range(range):
        # Python binds: self=list, r_or_target=range, r=None

        # Both cases have r=None and r_or_target=Range

        if isinstance(r_or_target, Range) and r is None:
            # Check if self is a List instance (or subclass that uses _values)
            if isinstance(self, List) and hasattr(self, '_values'):
                return self._get_range(r_or_target)

            # self is not a List with _values (could be Uri, StrBuf, Buf, GbGrid, etc.)
            # Check if type has its own getRange method (not inherited from List)
            own_class_getRange = type(self).__dict__.get('get_range', None)
            if own_class_getRange is not None and own_class_getRange is not List.get_range:
                # Type has its own getRange - call it directly
                # Use object.__getattribute__ to bypass our own getRange
                return own_class_getRange(self, r_or_target)

            # Check parent classes for getRange (but not List)
            for cls in type(self).__mro__:
                if cls is List:
                    continue
                cls_getRange = cls.__dict__.get('get_range', None)
                if cls_getRange is not None:
                    return cls_getRange(self, r_or_target)

            # Fallback: check for _getRange
            if hasattr(self, '_get_range'):
                return self._get_range(r_or_target)

            raise TypeError(f"{type(self).__name__} does not support getRange")

        # Two explicit arguments - shouldn't happen with current transpiler
        if r is not None:
            target = r_or_target
            if isinstance(target, List) and hasattr(target, '_values'):
                return target._get_range(r)
            if hasattr(target, 'get_range'):
                return target.get_range(r)
            raise TypeError(f"{type(target).__name__} does not support getRange")

        raise ValueError("getRange requires a Range argument")

    def _get_range(self, r):
        """Internal getRange implementation for List instances."""
        from .Err import IndexErr
        start = r._start
        end = r._end
        exclusive = r._exclusive
        n = len(self._values)

        if start < 0:
            start = n + start
        if end < 0:
            end = n + end

        end_for_slice = end + 1 if not exclusive else end

        if start < 0 or end_for_slice < start:
            raise IndexErr(f"{r}")
        if not exclusive and end >= n:
            raise IndexErr(f"{r}")
        if exclusive and end > n:
            raise IndexErr(f"{r}")

        result = List(self._elementType, self._values[start:end_for_slice])
        result._listType = self._listType
        return result

    def contains(self, item):
        """Check if list contains item"""
        return item in self

    def contains_same(self, item):
        """Check if list contains item using identity"""
        for x in self._values:
            if x is item:
                return True
        return False

    def contains_all(self, items):
        """Check if list contains all items"""
        for item in items:
            if item not in self:
                return False
        return True

    def contains_any(self, items):
        """Check if list contains any item"""
        for item in items:
            if item in self:
                return True
        return False

    def index(self, item, off=0):
        """Find index of item starting from offset"""
        from .ObjUtil import ObjUtil
        from .Err import IndexErr
        n = len(self._values)
        if n == 0:
            return None
        start = off
        if start < 0:
            start = n + start
        if start >= n or start < 0:
            raise IndexErr(f"{off}")
        for i in range(start, n):
            if ObjUtil.equals(self._values[i], item):
                return i
        return None

    def indexr(self, item, off=None):
        """Find index searching backwards"""
        from .ObjUtil import ObjUtil
        n = len(self._values)
        if off is None:
            off = n - 1
        if off < 0:
            off = n + off
        if off >= n:
            off = n - 1
        if off < 0:
            return None
        for i in range(off, -1, -1):
            if ObjUtil.equals(self._values[i], item):
                return i
        return None

    def index_same(self, item, off=0):
        """Find index using identity comparison"""
        for i in range(off, len(self._values)):
            if self._values[i] is item:
                return i
        return None

    #################################################################
    # Modification Methods
    #################################################################

    def _grow_capacity(self, minCapacity):
        """Grow capacity using standard growth algorithm"""
        # Java ArrayList style growth: max(minCapacity, oldCapacity * 1.5 + 1, 10)
        newCapacity = max(minCapacity, int(self._capacity * 1.5) + 1, 10)
        self._capacity = newCapacity

    def add(self, item):
        """Add item to end of list"""
        self._check_readonly()
        self._values.append(item)
        if len(self._values) > self._capacity:
            self._grow_capacity(len(self._values))
        self._roView = None
        return self

    def add_all(self, items):
        """Add all items from another collection"""
        self._check_readonly()
        self._values.extend(items)
        if len(self._values) > self._capacity:
            self._capacity = len(self._values)
        self._roView = None
        return self

    def add_not_null(self, item):
        """Add item if not null"""
        self._check_readonly()
        if item is not None:
            self._values.append(item)
            if len(self._values) > self._capacity:
                self._capacity = len(self._values)
            self._roView = None
        return self

    def insert_all(self, index, items):
        """Insert all items at index"""
        from .Err import IndexErr
        self._check_readonly()
        items_copy = list(items)
        n = len(self._values)
        orig_index = index
        if index < 0:
            index = n + index
        if index < 0 or index > n:
            raise IndexErr(f"{orig_index}")
        for i, item in enumerate(items_copy):
            self._values.insert(index + i, item)
        self._roView = None
        return self

    def set_(self, index, val):
        """Set item at index"""
        self._check_readonly()
        self._values[index] = val
        self._roView = None
        return self

    def set_not_null(self, index, val):
        """Set item at index only if val is not null"""
        if val is not None:
            self._check_readonly()
            self._values[index] = val
            self._roView = None
        return self

    def remove(self, item):
        """Remove first occurrence of item"""
        self._check_readonly()
        from .ObjUtil import ObjUtil
        for i, x in enumerate(self._values):
            if ObjUtil.equals(x, item):
                self._roView = None
                return self._values.pop(i)
        return None

    def remove_same(self, item):
        """Remove first occurrence using identity"""
        self._check_readonly()
        for i, x in enumerate(self._values):
            if x is item:
                self._roView = None
                return self._values.pop(i)
        return None

    def remove_at(self, index):
        """Remove and return item at index"""
        self._check_readonly()
        self._roView = None
        return self._values.pop(index)

    def remove_range(self, r):
        """Remove items in range"""
        self._check_readonly()
        start = r._start
        end = r._end
        exclusive = r._exclusive
        n = len(self._values)
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end
        if not exclusive:
            end = end + 1
        del self._values[start:end]
        self._roView = None
        return self

    def remove_all(self, items):
        """Remove all occurrences of items"""
        self._check_readonly()
        from .ObjUtil import ObjUtil
        for item in items:
            i = 0
            while i < len(self._values):
                if ObjUtil.equals(self._values[i], item):
                    self._values.pop(i)
                else:
                    i += 1
        self._roView = None
        return self

    def clear(self):
        """Remove all items"""
        self._check_readonly()
        self._values.clear()
        self._roView = None
        return self

    #################################################################
    # Stack Operations
    #################################################################

    def push(self, item):
        """Push item onto stack"""
        return self.add(item)

    def pop(self, index=None):
        """Pop item from stack"""
        self._check_readonly()
        if index is not None:
            self._roView = None
            return self._values.pop(index)
        if len(self._values) == 0:
            return None
        self._roView = None
        return self._values.pop()

    def peek(self):
        """Peek at top of stack"""
        return self._values[-1] if self._values else None

    #################################################################
    # Fill/Dup Methods
    #################################################################

    def fill(self, val, times):
        """Fill list with val, times number of times"""
        self._check_readonly()
        for _ in range(times):
            self._values.append(val)
        if len(self._values) > self._capacity:
            self._capacity = len(self._values)
        self._roView = None
        return self

    def dup(self):
        """Return a duplicate of this list"""
        result = List(self._elementType, list(self._values))
        result._listType = self._listType
        result._of = self._of
        return result

    def trim(self):
        """Trim capacity to size"""
        self._check_readonly()
        self._capacity = len(self._values)
        return self

    #################################################################
    # Iteration Methods
    #################################################################

    @staticmethod
    def _get_param_count(f):
        """Get number of required parameters for a function"""
        from .Func import Func
        if isinstance(f, Func):
            return len(f.params())
        import inspect
        try:
            sig = inspect.signature(f)
            return len([p for p in sig.parameters.values()
                       if p.default is inspect.Parameter.empty])
        except:
            return 1

    def each(self, f):
        """Iterate over each element, optionally with index"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                f(item, i)
        else:
            for item in self._values:
                f(item)

    def eachr(self, f):
        """Iterate in reverse order"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i in range(len(self._values) - 1, -1, -1):
                f(self._values[i], i)
        else:
            for item in reversed(self._values):
                f(item)

    def each_while(self, f):
        """Iterate until f returns non-null"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                result = f(item, i)
                if result is not None:
                    return result
        else:
            for item in self._values:
                result = f(item)
                if result is not None:
                    return result
        return None

    def eachr_while(self, f):
        """Iterate in reverse until f returns non-null"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i in range(len(self._values) - 1, -1, -1):
                result = f(self._values[i], i)
                if result is not None:
                    return result
        else:
            for i in range(len(self._values) - 1, -1, -1):
                result = f(self._values[i])
                if result is not None:
                    return result
        return None

    def each_range(self, r, f):
        """Iterate over a range of indices"""
        start = r._start
        end = r._end
        exclusive = r._exclusive
        n = len(self._values)
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end
        if not exclusive:
            end = end + 1
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i in range(start, end):
                f(self._values[i], i)
        else:
            for i in range(start, end):
                f(self._values[i])

    def each_not_null(self, f):
        """Iterate over non-null elements"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                if item is not None:
                    f(item, i)
        else:
            for item in self._values:
                if item is not None:
                    f(item)

    #################################################################
    # Transformation Methods
    #################################################################

    def map_(self, f):
        """Transform each element, return new list (map_ avoids Python builtin conflict)"""
        result = []
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                result.append(f(item, i))
        else:
            for item in self._values:
                result.append(f(item))
        return List.from_literal(result, self._elementType if self._elementType else "sys::Obj")

    def flat_map(self, f):
        """Map and flatten results"""
        result = []
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                mapped = f(item, i)
                if hasattr(mapped, '__iter__') and not isinstance(mapped, (str, bytes)):
                    result.extend(mapped)
                else:
                    result.append(mapped)
        else:
            for item in self._values:
                mapped = f(item)
                if hasattr(mapped, '__iter__') and not isinstance(mapped, (str, bytes)):
                    result.extend(mapped)
                else:
                    result.append(mapped)
        return List.from_literal(result, "sys::Obj")

    def map_not_null(self, f):
        """Transform elements, excluding null results"""
        result = []
        for item in self._values:
            mapped = f(item)
            if mapped is not None:
                result.append(mapped)
        return List.from_literal(result, "sys::Obj")

    def flatten(self):
        """Flatten nested lists recursively"""
        result = []
        for item in self._values:
            if isinstance(item, List):
                result.extend(item.flatten()._values)
            elif isinstance(item, list):
                result.extend(List(None, item).flatten()._values)
            else:
                result.append(item)
        return List.from_literal(result, "sys::Obj")

    #################################################################
    # Filter/Find Methods
    #################################################################

    def find(self, f):
        """Find first element matching predicate"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                if f(item, i):
                    return item
        else:
            for item in self._values:
                if f(item):
                    return item
        return None

    def find_all(self, f):
        """Find all elements matching predicate"""
        result = []
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                if f(item, i):
                    result.append(item)
        else:
            for item in self._values:
                if f(item):
                    result.append(item)
        return List.from_literal(result, self._elementType if self._elementType else "sys::Obj")

    def find_index(self, f):
        """Find index of first element matching predicate"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                if f(item, i):
                    return i
        else:
            for i, item in enumerate(self._values):
                if f(item):
                    return i
        return None

    def find_type(self, type_):
        """Find all elements of given type"""
        from .ObjUtil import ObjUtil
        result = []
        for item in self._values:
            if ObjUtil.is_(item, type_):
                result.append(item)
        return List.from_literal(result, type_)

    def find_not_null(self):
        """Return list with null values removed"""
        result = [item for item in self._values if item is not None]
        elemType = self._elementType
        if elemType is not None:
            sig = elemType.signature() if hasattr(elemType, 'signature') else str(elemType)
            if sig.endswith("?"):
                sig = sig[:-1]
            return List.from_literal(result, sig)
        return List.from_literal(result, "sys::Obj")

    def exclude(self, f):
        """Exclude elements matching predicate"""
        result = []
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                if not f(item, i):
                    result.append(item)
        else:
            for item in self._values:
                if not f(item):
                    result.append(item)
        return List.from_literal(result, self._elementType if self._elementType else "sys::Obj")

    def any_(self, f):
        """Return true if any element matches predicate"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                if f(item, i):
                    return True
        else:
            for item in self._values:
                if f(item):
                    return True
        return False

    def all_(self, f):
        """Return true if all elements match predicate"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(self._values):
                if not f(item, i):
                    return False
        else:
            for item in self._values:
                if not f(item):
                    return False
        return True

    #################################################################
    # Aggregation Methods
    #################################################################

    def reduce(self, init, f):
        """Reduce list to single value"""
        acc = init
        param_count = List._get_param_count(f)
        if param_count >= 3:
            for i, item in enumerate(self._values):
                acc = f(acc, item, i)
        else:
            for item in self._values:
                acc = f(acc, item)
        return acc

    def min_(self, f=None):
        """Get minimum value"""
        if len(self._values) == 0:
            return None
        if None in self._values:
            return None
        if f is not None:
            import functools
            return min(self._values, key=functools.cmp_to_key(f))
        return min(self._values)

    def max_(self, f=None):
        """Get maximum value"""
        if len(self._values) == 0:
            return None
        non_null = [x for x in self._values if x is not None]
        if len(non_null) == 0:
            return None
        if f is not None:
            import functools
            return max(non_null, key=functools.cmp_to_key(f))
        return max(non_null)

    def join(self, sep="", converter=None):
        """Join elements into string"""
        from .ObjUtil import ObjUtil
        if converter is not None:
            # Call converter with original item, then convert result to string
            return sep.join(ObjUtil.to_str(converter(x)) for x in self._values)
        return sep.join(ObjUtil.to_str(x) for x in self._values)

    #################################################################
    # Sort/Order Methods
    #################################################################

    def sort(self, f=None, *, key=None, reverse=False):
        """Sort list in place"""
        self._check_readonly()
        if key is not None or reverse:
            self._values.sort(key=key, reverse=reverse)
        elif f is not None:
            import functools
            self._values.sort(key=functools.cmp_to_key(f))
        else:
            def sort_key(x):
                if x is None:
                    return (0, "")
                elif isinstance(x, bool):
                    return (1, int(x))
                elif isinstance(x, (int, float)):
                    return (1, x)
                else:
                    return (1, str(x))
            try:
                self._values.sort(key=sort_key)
            except TypeError:
                self._values.sort(key=lambda x: (0, "") if x is None else (1, str(x)))
        self._roView = None
        return self

    def sortr(self, f=None):
        """Sort list in reverse order"""
        self.sort(f)
        self._values.reverse()
        return self

    def reverse(self):
        """Reverse list in place"""
        self._check_readonly()
        self._values.reverse()
        self._roView = None
        return self

    def shuffle(self):
        """Randomly shuffle list"""
        self._check_readonly()
        import random
        random.shuffle(self._values)
        self._roView = None
        return self

    def swap(self, a, b):
        """Swap elements at indices a and b"""
        self._check_readonly()
        self._values[a], self._values[b] = self._values[b], self._values[a]
        self._roView = None
        return self

    def move_to(self, item, index):
        """Move item to target index"""
        self._check_readonly()
        from .ObjUtil import ObjUtil
        old_index = None
        for i, x in enumerate(self._values):
            if ObjUtil.equals(x, item):
                old_index = i
                break
        if old_index is None:
            return self
        n = len(self._values)
        if index < 0:
            index = n + index
        self._values.pop(old_index)
        self._values.insert(index, item)
        self._roView = None
        return self

    #################################################################
    # Set Operations
    #################################################################

    def unique(self):
        """Return list with duplicates removed"""
        from .ObjUtil import ObjUtil
        seen = []
        result = []
        for item in self._values:
            found = False
            for s in seen:
                if ObjUtil.equals(s, item):
                    found = True
                    break
            if not found:
                seen.append(item)
                result.append(item)
        return List.from_literal(result, self._elementType if self._elementType else "sys::Obj")

    def union(self, that):
        """Return union of two lists"""
        result_list = self.unique()
        for item in that:
            if not result_list.contains(item):
                result_list._values.append(item)
        return result_list

    def intersection(self, that):
        """Return intersection of two lists"""
        result = []
        for item in self._values:
            if item in that and item not in result:
                result.append(item)
        return List.from_literal(result, self._elementType if self._elementType else "sys::Obj")

    def group_by(self, f):
        """Group elements by a key function"""
        from .Map import Map
        from .Func import Func
        elemTypeSig = "sys::Obj"
        if self._elementType is not None:
            elemTypeSig = self._elementType.signature() if hasattr(self._elementType, 'signature') else str(self._elementType)
        keyTypeSig = "sys::Obj"
        if isinstance(f, Func):
            ret = f.returns()
            if ret is not None:
                keyTypeSig = ret.signature() if hasattr(ret, 'signature') else str(ret)
        result = Map.from_literal([], [], keyTypeSig, elemTypeSig + "[]")
        param_count = List._get_param_count(f)
        for i, item in enumerate(self._values):
            if param_count >= 2:
                key = f(item, i)
            else:
                key = f(item)
            if result.contains_key(key):
                result.get(key).add(item)
            else:
                result.set_(key, List.from_literal([item], elemTypeSig))
        return result

    def group_by_into(self, map_, f):
        """Group elements into an existing Map"""
        param_count = List._get_param_count(f)
        for i, item in enumerate(self._values):
            if param_count >= 2:
                key = f(item, i)
            else:
                key = f(item)
            if map_.contains_key(key):
                map_.get(key).add(item)
            else:
                map_.set_(key, List.from_literal([item], "sys::Obj"))
        return map_

    #################################################################
    # Binary Search
    #################################################################

    def binary_search(self, key, f=None):
        """Binary search for key"""
        from .ObjUtil import ObjUtil
        lo = 0
        hi = len(self._values) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            midVal = self._values[mid]
            if f is not None:
                cmp = f(midVal, key)
            else:
                cmp = ObjUtil.compare(midVal, key)
            if cmp < 0:
                lo = mid + 1
            elif cmp > 0:
                hi = mid - 1
            else:
                return mid
        return -(lo + 1)

    def binary_find(self, f):
        """Binary search using comparison function"""
        lo = 0
        hi = len(self._values) - 1
        param_count = List._get_param_count(f)
        while lo <= hi:
            mid = (lo + hi) // 2
            if param_count >= 2:
                cmp = f(self._values[mid], mid)
            else:
                cmp = f(self._values[mid])
            if cmp > 0:
                lo = mid + 1
            elif cmp < 0:
                hi = mid - 1
            else:
                return mid
        return -(lo + 1)

    #################################################################
    # Conversion Methods
    #################################################################

    def to_str(self):
        """Convert list to string"""
        from .ObjUtil import ObjUtil
        if len(self._values) == 0:
            return "[,]"
        items = [ObjUtil.to_str(x) for x in self._values]
        return "[" + ", ".join(items) + "]"

    def to_code(self):
        """Convert list to Fantom code literal"""
        from .ObjUtil import ObjUtil
        typeSig = None
        if self._listType is not None:
            typeSig = self._listType.signature() if hasattr(self._listType, 'signature') else None
        if typeSig is None:
            typeSig = "sys::Obj?[]"
        if len(self._values) == 0:
            elemType = typeSig[:-2] if typeSig.endswith("[]") else "sys::Obj?"
            return f"{elemType}[,]"
        items = [ObjUtil.to_code(x) for x in self._values]
        elemType = typeSig[:-2] if typeSig.endswith("[]") else "sys::Obj?"
        return f"{elemType}[" + ", ".join(items) + "]"

    def literal_encode(self, out):
        """Encode for serialization"""
        out.write_list(self)

    def hash_(self):
        """Return hash code"""
        from .ObjUtil import ObjUtil
        h = 33
        for item in self._values:
            h = (h * 31 + ObjUtil.hash_(item)) & 0xFFFFFFFF
        return h

    def random(self):
        """Return random element"""
        import random
        if len(self._values) == 0:
            return None
        return random.choice(self._values)

    def with_(self, f):
        """Apply it-block closure"""
        f(self)
        return self

    def trap(self, name, args=None):
        """Dynamic method invocation"""
        if args is None:
            args = []
        # Convert camelCase to snake_case for Python method lookup
        from .Type import _camel_to_snake
        py_name = _camel_to_snake(name)

        # Handle properties (size, capacity, etc.) - try snake_case first
        for n in (py_name, name):
            attr = getattr(type(self), n, None)
            if isinstance(attr, property):
                if args:
                    # Setter
                    setattr(self, n, args[0])
                    return None
                else:
                    # Getter
                    return getattr(self, n)
        # Handle methods - try snake_case first
        for n in (py_name, name):
            method = getattr(self, n, None)
            if method and callable(method):
                return method(*args)
        raise AttributeError(f"List.{name}")

    # NOTE: Backward compatibility static methods have been REMOVED
    # The transpiler now generates instance method calls directly.
    # Static methods like ro(lst), rw(lst), get(lst, index) were
    # overwriting the instance methods and causing failures.



#################################################################
# ImmutableList - Immutable version of List
#################################################################

class ImmutableList(List):
    """Immutable list - extends List but blocks mutation"""

    def __init__(self, of_type=None, items=None):
        super().__init__(of_type, items)
        self._immutable = True

    def _check_readonly(self):
        """Throw ReadonlyErr on any mutation attempt"""
        from .Err import ReadonlyErr
        raise ReadonlyErr("List is immutable")

    def is_ro(self):
        return True

    def is_rw(self):
        return False

    def is_immutable(self):
        return True

    def to_immutable(self):
        """Already immutable - return self"""
        return self

    def ro(self):
        """Already immutable - return self"""
        return self

    def rw(self):
        """Return mutable copy"""
        result = List(self._elementType, list(self._values))
        result._listType = self._listType
        result._of = self._of
        return result

    def __hash__(self):
        """Immutable lists are hashable"""
        return hash(tuple(self._values))


#################################################################
# ReadOnlyList - Read-only view of a mutable List
#################################################################

class ReadOnlyList(List):
    """Read-only view of a list - blocks mutation but references source"""

    def __init__(self, source):
        """Create read-only view of source list"""
        if isinstance(source, List):
            super().__init__(source._elementType, source._values)
            self._source = source
            self._listType = source._listType
            self._of = source._of
        else:
            super().__init__(None, source)
            self._source = source

    def _check_readonly(self):
        """Throw ReadonlyErr on any mutation attempt"""
        from .Err import ReadonlyErr
        raise ReadonlyErr("List is read-only")

    def is_ro(self):
        return True

    def is_rw(self):
        return False

    def is_immutable(self):
        return False

    def ro(self):
        """Already read-only - return self"""
        return self

    def rw(self):
        """Return the original mutable source"""
        return self._source

    def to_immutable(self):
        """Convert to fully immutable list"""
        from .ObjUtil import ObjUtil
        immutable_items = []
        for item in self._values:
            if item is None:
                immutable_items.append(None)
            elif ObjUtil.is_immutable(item):
                immutable_items.append(item)
            elif hasattr(item, 'to_immutable') and callable(item.to_immutable):
                immutable_items.append(item.to_immutable())
            else:
                immutable_items.append(item)
        result = ImmutableList(self._elementType, immutable_items)
        result._listType = self._listType
        result._of = self._of
        return result


# NOTE: ListImpl alias has been REMOVED
# Any code using ListImpl should be updated to use List directly
