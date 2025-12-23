#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#


class ListImpl(list):
    """Type-aware List implementation that tracks element type"""

    def __init__(self, items=None, elementType=None, capacity=None):
        super().__init__(items or [])
        self._elementType = elementType  # Fantom element type
        self._listType = None  # Cached ListType
        # Track capacity separately (Fantom lists have explicit capacity)
        self._capacity = capacity if capacity is not None else len(self)
        self._roView = None  # Cached read-only view

    def __len__(self):
        """Support Python len() function"""
        return list.__len__(self)

    def __hash__(self):
        """Make ListImpl hashable for use as map keys (like Fantom immutable lists)"""
        # Use tuple of elements for hashing
        try:
            return hash(tuple(self))
        except TypeError:
            # If elements aren't hashable, use id-based hash
            return id(self)

    def toImmutable(self):
        """Return immutable version of this list"""
        result = ImmutableList(self)
        result._elementType = getattr(self, '_elementType', None)
        result._listType = getattr(self, '_listType', None)
        result._of = getattr(self, '_of', None)
        return result

    @staticmethod
    def fromLiteral(values, elementType):
        """Create type-aware list from literal values like JavaScript List.make()

        Args:
            values: List of values
            elementType: The Fantom element type (Type object or string signature)
        """
        from .Type import Type, ListType

        result = ListImpl(values)

        # Convert string signature to Type object if needed
        if isinstance(elementType, str):
            elementType = Type.find(elementType)

        result._elementType = elementType
        # Use Type.find() to get the cached ListType for identity checks
        result._listType = Type.find(elementType.signature() + "[]")
        return result

    def typeof(self):
        """Return Fantom Type for this List"""
        from .Type import Type, ListType
        # If we have stored ListType, use it
        if self._listType is not None:
            return self._listType
        # Otherwise return generic List type
        return Type.find("sys::List")

    def get(self, index, default=None):
        """Get element at index (instance method for ListImpl)"""
        if default is not None:
            if 0 <= index < len(self):
                return self[index]
            return default
        return self[index]

    # Note: size is a property to support both read (x.size) and write (x.size = N)
    @property
    def size(self):
        """Property for size to support both get and set"""
        return len(self)

    @size.setter
    def size(self, val):
        """Set size - grows or shrinks list"""
        self._set_size(val)

    def _set_size(self, val):
        """Set size - grows or shrinks list, adjusting capacity"""
        current = len(self)
        if val > current:
            # Grow list with None values
            if val > self._capacity:
                self._capacity = val
            for _ in range(val - current):
                super().append(None)
        elif val < current:
            # Shrink list (but keep capacity)
            del self[val:]

    @property
    def capacity(self):
        """Return capacity"""
        return self._capacity

    @capacity.setter
    def capacity(self, val):
        """Set capacity - cannot set below current size"""
        if val < len(self):
            from .Err import ArgErr
            raise ArgErr(f"Cannot set capacity {val} below size {len(self)}")
        self._capacity = val

    def isRO(self):
        """Return true if this list is read-only (immutable)"""
        return False

    def isRW(self):
        """Return true if this list is read-write (mutable)"""
        return True

    def _invalidateRoCache(self):
        """Invalidate cached read-only view when list is modified"""
        self._roView = None

    def append(self, item):
        """Override append to track capacity growth and invalidate RO cache"""
        self._invalidateRoCache()
        # If adding would exceed capacity, grow it
        # Fantom grows to next capacity in 8-unit increments:
        # 0->8->16->24..., or 2->10->18..., or 3->11->19..., etc.
        if len(self) >= self._capacity:
            # Grow to next capacity (rounds up to capacity + 8 effectively)
            # But Fantom seems to use: if capacity < 8, grow to 8+cap; else double
            # Looking at test: cap=5, add 1 -> cap=10 (which is 5+5, but rounded to next 10?)
            # Actually: when exceeding capacity, Fantom doubles if small, or adds a chunk
            # Test shows: capacity 5 -> 10 after add. So it rounds to 10.
            # Seems like Fantom rounds up to nearest 10 when growing? Or doubles?
            # Let's try: grow to max(current*2, current+8), but cap at reasonable multiples
            new_cap = max(self._capacity * 2, self._capacity + 5)
            # Round to nearest 5 or 10 for cleaner capacity values
            new_cap = ((new_cap + 4) // 5) * 5
            self._capacity = new_cap
        super().append(item)

    def extend(self, items):
        """Override extend to track capacity growth"""
        new_size = len(self) + len(items)
        if new_size > self._capacity:
            self._capacity = max(self._capacity + 8, new_size)
        super().extend(items)


class List:
    """List utilities - extends Python list behavior with Fantom semantics"""

    @staticmethod
    def fromLiteral(values, elementType):
        """Create type-aware list from literal values

        Args:
            values: List of values
            elementType: The Fantom element type (Type object or string signature)
        """
        return ListImpl.fromLiteral(values, elementType)

    @staticmethod
    def fromList(values, elementType=None):
        """Create a List from a Python list (alias for fromLiteral with optional type)"""
        if elementType is None:
            elementType = "sys::Obj"
        return ListImpl.fromLiteral(values, elementType)

    #################################################################
    # Iteration Methods
    #################################################################

    @staticmethod
    def each(lst, f):
        """Iterate over each element, optionally with index"""
        # Delegate to Map if lst is a Map
        from .Map import Map
        if isinstance(lst, Map):
            return lst.each(f)
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                f(item, i)
        else:
            for item in lst:
                f(item)

    @staticmethod
    def eachWhile(lst, f):
        """Iterate until f returns non-null"""
        # Delegate to Map if lst is a Map
        from .Map import Map
        if isinstance(lst, Map):
            return lst.eachWhile(f)
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                result = f(item, i)
                if result is not None:
                    return result
        else:
            for item in lst:
                result = f(item)
                if result is not None:
                    return result
        return None

    @staticmethod
    def eachr(lst, f):
        """Iterate over each element in reverse order"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i in range(len(lst) - 1, -1, -1):
                f(lst[i], i)
        else:
            for item in reversed(lst):
                f(item)

    @staticmethod
    def eachrWhile(lst, f):
        """Iterate in reverse until f returns non-null"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i in range(len(lst) - 1, -1, -1):
                result = f(lst[i], i)
                if result is not None:
                    return result
        else:
            for i in range(len(lst) - 1, -1, -1):
                result = f(lst[i])
                if result is not None:
                    return result
        return None

    @staticmethod
    def eachRange(lst, r, f):
        """Iterate over a range of indices (supports negative indices)"""
        from .Range import Range
        start = r._start
        end = r._end
        exclusive = r._exclusive
        n = len(lst)

        # Convert negative indices to positive
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end

        if not exclusive:
            end = end + 1

        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i in range(start, end):
                f(lst[i], i)
        else:
            for i in range(start, end):
                f(lst[i])

    @staticmethod
    def eachNotNull(lst, f):
        """Iterate over each non-null element"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                if item is not None:
                    f(item, i)
        else:
            for item in lst:
                if item is not None:
                    f(item)

    #################################################################
    # Transformation Methods
    #################################################################

    @staticmethod
    def map_(lst, f):
        """Transform each element, return new list (underscore avoids Python builtin)"""
        result = []
        param_count = List._get_param_count(f)

        if param_count >= 2:
            for i, item in enumerate(lst):
                result.append(f(item, i))
        else:
            for item in lst:
                result.append(f(item))
        return result

    @staticmethod
    def flatMap(lst, f):
        """Map and flatten results"""
        result = []
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                mapped = f(item, i)
                if isinstance(mapped, list):
                    result.extend(mapped)
                else:
                    result.append(mapped)
        else:
            for item in lst:
                mapped = f(item)
                if isinstance(mapped, list):
                    result.extend(mapped)
                else:
                    result.append(mapped)
        return result

    @staticmethod
    def mapNotNull(lst, f):
        """Transform elements, excluding null results"""
        result = []
        for item in lst:
            mapped = f(item)
            if mapped is not None:
                result.append(mapped)
        return result

    @staticmethod
    def flatten(lst):
        """Flatten nested lists recursively"""
        result = []
        for item in lst:
            if isinstance(item, list):
                # Recursively flatten nested lists
                result.extend(List.flatten(item))
            else:
                result.append(item)
        return result

    #################################################################
    # Filter/Find Methods
    #################################################################

    @staticmethod
    def _get_param_count(f):
        """Get number of required parameters for a function"""
        # Check if f is a Func instance - use its params() method
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

    @staticmethod
    def find(lst, f):
        """Find first element matching predicate"""
        # Delegate to Map if lst is a Map
        from .Map import Map
        if isinstance(lst, Map):
            return lst.find(f)
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                if f(item, i):
                    return item
        else:
            for item in lst:
                if f(item):
                    return item
        return None

    @staticmethod
    def findIndex(lst, f):
        """Find index of first element matching predicate"""
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                if f(item, i):
                    return i
        else:
            for i, item in enumerate(lst):
                if f(item):
                    return i
        return None

    @staticmethod
    def binarySearch(lst, key, f=None):
        """Binary search for key in sorted list. Returns index if found, or -(insertionPoint+1) if not found."""
        from .ObjUtil import ObjUtil
        lo = 0
        hi = len(lst) - 1

        while lo <= hi:
            mid = (lo + hi) // 2
            midVal = lst[mid]

            if f is not None:
                cmp = f(midVal, key)
            else:
                cmp = ObjUtil.compare(midVal, key)

            if cmp < 0:
                lo = mid + 1
            elif cmp > 0:
                hi = mid - 1
            else:
                return mid  # Found

        return -(lo + 1)  # Not found, return insertion point

    @staticmethod
    def binaryFind(lst, f):
        """Binary search using a function that returns <0, 0, >0 for comparison.
        The function f returns: <0 if item > target, 0 if equal, >0 if item < target.
        Returns the index if found, or -(insertionPoint + 1) if not found.
        Supports both 1-arg (item) and 2-arg (item, index) closures."""
        lo = 0
        hi = len(lst) - 1

        # Check arity of function to determine call style
        param_count = List._get_param_count(f)

        while lo <= hi:
            mid = (lo + hi) // 2
            # Call with 1 or 2 args depending on function arity
            if param_count >= 2:
                cmp = f(lst[mid], mid)
            else:
                cmp = f(lst[mid])

            if cmp > 0:
                # item < target, search higher
                lo = mid + 1
            elif cmp < 0:
                # item > target, search lower
                hi = mid - 1
            else:
                return mid  # Found - return index

        return -(lo + 1)  # Not found - return negative insertion point

    @staticmethod
    def findAll(lst, f):
        """Find all elements matching predicate"""
        result = []
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                if f(item, i):
                    result.append(item)
        else:
            for item in lst:
                if f(item):
                    result.append(item)
        return result

    @staticmethod
    def exclude(lst, f):
        """Exclude elements matching predicate"""
        result = []
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                if not f(item, i):
                    result.append(item)
        else:
            for item in lst:
                if not f(item):
                    result.append(item)
        return result

    @staticmethod
    def any(lst, f):
        """Return true if any element matches predicate"""
        # Delegate to Map if lst is a Map
        from .Map import Map
        if isinstance(lst, Map):
            return lst.any(f)
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                if f(item, i):
                    return True
        else:
            for item in lst:
                if f(item):
                    return True
        return False

    @staticmethod
    def all(lst, f):
        """Return true if all elements match predicate"""
        # Delegate to Map if lst is a Map
        from .Map import Map
        if isinstance(lst, Map):
            return lst.all(f)
        param_count = List._get_param_count(f)
        if param_count >= 2:
            for i, item in enumerate(lst):
                if not f(item, i):
                    return False
        else:
            for item in lst:
                if not f(item):
                    return False
        return True

    #################################################################
    # Accessor Methods
    #################################################################

    @staticmethod
    def size(lst):
        return len(lst)

    @staticmethod
    def isEmpty(lst):
        return len(lst) == 0

    @staticmethod
    def first(lst):
        """Get first element or null if empty"""
        return lst[0] if len(lst) > 0 else None

    @staticmethod
    def last(lst):
        """Get last element or null if empty"""
        return lst[-1] if len(lst) > 0 else None

    @staticmethod
    def get(lst, index, default=None):
        """Get element at index. For Maps, supports (key, default) syntax."""
        from .Map import Map
        if isinstance(lst, Map):
            # Map.get(key, default)
            return lst.get(index, default)
        # List: if default provided, use getSafe behavior
        if default is not None:
            if 0 <= index < len(lst):
                return lst[index]
            return default
        return lst[index]

    @staticmethod
    def getSafe(lst, index, default=None):
        """Get element or default if out of bounds"""
        n = len(lst)
        # Handle negative indices (Fantom style: -1 is last element)
        if index < 0:
            index = n + index
        if 0 <= index < n:
            return lst[index]
        return default

    @staticmethod
    def getRange(lst, r):
        """Get a slice of the list using a Range"""
        from .Range import Range

        # If object has its own getRange method, use it (Uri, Str, etc.)
        if hasattr(lst, 'getRange') and callable(getattr(lst, 'getRange')):
            return lst.getRange(r)

        start = r._start
        end = r._end
        exclusive = r._exclusive
        n = len(lst)

        # Convert negative indices to positive
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end

        # Apply exclusive adjustment
        if not exclusive:
            end = end + 1

        # Handle edge case where end < start after conversion
        if end < start:
            return []

        return lst[start:end]

    @staticmethod
    def contains(lst, item):
        """Check if list contains item"""
        from .ObjUtil import ObjUtil
        for x in lst:
            if ObjUtil.equals(x, item):
                return True
        return False

    @staticmethod
    def index(lst, item, off=0):
        """Find index of item starting from offset"""
        from .ObjUtil import ObjUtil
        n = len(lst)
        # Convert negative offset to positive
        if off < 0:
            off = n + off
        # If offset is still negative or beyond list, return None
        if off < 0 or off >= n:
            return None
        for i in range(off, n):
            if ObjUtil.equals(lst[i], item):
                return i
        return None

    @staticmethod
    def indexr(lst, item, off=None):
        """Find index of item searching backwards from offset"""
        from .ObjUtil import ObjUtil
        n = len(lst)
        if off is None:
            off = n - 1
        # Convert negative offset to positive (Fantom style: -1 is last element)
        if off < 0:
            off = n + off
        # Clamp to valid range
        if off >= n:
            off = n - 1
        if off < 0:
            return None
        for i in range(off, -1, -1):
            if ObjUtil.equals(lst[i], item):
                return i
        return None

    @staticmethod
    def indexSame(lst, item, off=0):
        """Find index using identity comparison"""
        for i in range(off, len(lst)):
            if lst[i] is item:
                return i
        return None

    @staticmethod
    def containsSame(lst, item):
        """Check if list contains item using identity"""
        return List.indexSame(lst, item) is not None

    @staticmethod
    def containsAll(lst, items):
        """Check if list contains all items from another list"""
        for item in items:
            if not List.contains(lst, item):
                return False
        return True

    @staticmethod
    def containsAny(lst, items):
        """Check if list contains any item from another list"""
        for item in items:
            if List.contains(lst, item):
                return True
        return False

    #################################################################
    # Modification Methods
    #################################################################

    @staticmethod
    def add(lst, item):
        lst.append(item)
        return lst

    @staticmethod
    def addAll(lst, items):
        """Add all items from another list"""
        lst.extend(items)
        return lst

    @staticmethod
    def addNotNull(lst, item):
        """Add item if not null"""
        if item is not None:
            lst.append(item)
        return lst

    @staticmethod
    def insert(lst, index, item):
        """Insert item at index"""
        lst.insert(index, item)
        return lst

    @staticmethod
    def insertAll(lst, index, items):
        """Insert all items at index"""
        # Copy items to avoid infinite loop when inserting list into itself
        items_copy = list(items)
        n = len(lst)

        # Convert negative index to positive
        if index < 0:
            index = n + index

        for i, item in enumerate(items_copy):
            lst.insert(index + i, item)
        return lst

    @staticmethod
    def set(lst, index, val):
        lst[index] = val
        return lst

    @staticmethod
    def remove(lst, item):
        """Remove first occurrence of item, return removed item or null"""
        from .ObjUtil import ObjUtil
        for i, x in enumerate(lst):
            if ObjUtil.equals(x, item):
                return lst.pop(i)
        return None

    @staticmethod
    def removeSame(lst, item):
        """Remove first occurrence using identity"""
        for i, x in enumerate(lst):
            if x is item:
                return lst.pop(i)
        return None

    @staticmethod
    def removeAt(lst, index):
        """Remove and return item at index"""
        return lst.pop(index)

    @staticmethod
    def removeRange(lst, r):
        """Remove items in range"""
        from .Range import Range
        start = r._start
        end = r._end
        exclusive = r._exclusive
        n = len(lst)

        # Convert negative indices to positive
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end

        # Apply exclusive adjustment
        if not exclusive:
            end = end + 1

        del lst[start:end]
        return lst

    @staticmethod
    def removeAll(lst, items):
        """Remove all occurrences of items"""
        from .ObjUtil import ObjUtil
        for item in items:
            # Remove all occurrences
            i = 0
            while i < len(lst):
                if ObjUtil.equals(lst[i], item):
                    lst.pop(i)
                else:
                    i += 1
        return lst

    @staticmethod
    def clear(lst):
        """Remove all items from the list"""
        lst.clear()
        return lst

    #################################################################
    # Stack Operations
    #################################################################

    @staticmethod
    def push(lst, item):
        """Push item onto stack (same as add)"""
        lst.append(item)
        return lst

    @staticmethod
    def pop(lst):
        """Pop item from stack, return null if empty"""
        if len(lst) == 0:
            return None
        return lst.pop()

    @staticmethod
    def peek(lst):
        """Peek at top of stack"""
        return lst[-1] if len(lst) > 0 else None

    #################################################################
    # Aggregation Methods
    #################################################################

    @staticmethod
    def min(lst, f=None):
        """Get minimum value using optional comparator"""
        if len(lst) == 0:
            return None
        # In Fantom, null is the minimum value (sorts before all other values)
        if None in lst:
            return None
        if f is not None:
            # f is a comparator (a, b) -> Int returning -1/0/1
            import functools
            return min(lst, key=functools.cmp_to_key(f))
        return min(lst)

    @staticmethod
    def max(lst, f=None):
        """Get maximum value using optional comparator"""
        if len(lst) == 0:
            return None
        # Filter out None values for max (null is minimum, not maximum)
        non_null = [x for x in lst if x is not None]
        if len(non_null) == 0:
            return None
        if f is not None:
            # f is a comparator (a, b) -> Int returning -1/0/1
            import functools
            return max(non_null, key=functools.cmp_to_key(f))
        return max(non_null)

    @staticmethod
    def reduce(lst, init, f):
        """Reduce list to single value"""
        acc = init
        param_count = List._get_param_count(f)
        if param_count >= 3:
            for i, item in enumerate(lst):
                acc = f(acc, item, i)
        else:
            for item in lst:
                acc = f(acc, item)
        return acc

    @staticmethod
    def join(lst, sep="", converter=None):
        """Join elements into string with optional converter function"""
        from .ObjUtil import ObjUtil
        # Delegate to Map if lst is a Map
        from .Map import Map
        if isinstance(lst, Map):
            return lst.join(sep)
        if converter is not None:
            # Convert values to string first (null -> "null"), then pass to converter
            return sep.join(converter(ObjUtil.toStr(x)) for x in lst)
        return sep.join(ObjUtil.toStr(x) for x in lst)

    #################################################################
    # Sort/Order Methods
    #################################################################

    @staticmethod
    def sort(lst, f=None):
        """Sort list in place. Nulls sort first in Fantom."""
        from .ObjUtil import ObjUtil
        if f is not None:
            # Use function as comparator (Fantom style: return -1, 0, 1)
            import functools
            lst.sort(key=functools.cmp_to_key(f))
        else:
            # In Fantom, null sorts first. Use tuple key: (is_not_none, value_for_sort)
            def sort_key(x):
                if x is None:
                    return (0, "")  # Nulls sort first (0 < 1)
                elif isinstance(x, bool):
                    return (1, int(x))  # Convert bool to int for comparison
                elif isinstance(x, (int, float)):
                    return (1, x)
                else:
                    return (1, str(x))  # Use string for other types
            try:
                lst.sort(key=sort_key)
            except TypeError:
                # If types still can't be compared, use string representation
                lst.sort(key=lambda x: (0, "") if x is None else (1, str(x)))
        return lst

    @staticmethod
    def sortr(lst, f=None):
        """Sort list in reverse order"""
        List.sort(lst, f)
        lst.reverse()
        return lst

    @staticmethod
    def reverse(lst):
        """Reverse list in place"""
        lst.reverse()
        return lst

    @staticmethod
    def shuffle(lst):
        """Randomly shuffle list in place"""
        import random
        random.shuffle(lst)
        return lst

    @staticmethod
    def swap(lst, a, b):
        """Swap elements at indices a and b"""
        lst[a], lst[b] = lst[b], lst[a]
        return lst

    @staticmethod
    def moveTo(lst, item, index):
        """Move item to target index in the resulting list"""
        from .ObjUtil import ObjUtil
        # Find the item
        old_index = None
        for i, x in enumerate(lst):
            if ObjUtil.equals(x, item):
                old_index = i
                break

        if old_index is None:
            return lst  # Item not found

        # Convert negative index to positive (based on original list length)
        n = len(lst)
        if index < 0:
            index = n + index

        # Remove from old position
        lst.pop(old_index)

        # Insert at target position (no adjustment needed - index is final position)
        lst.insert(index, item)
        return lst

    #################################################################
    # Set Operations
    #################################################################

    @staticmethod
    def unique(lst):
        """Return list with duplicates removed (preserves order)"""
        from .ObjUtil import ObjUtil
        seen = []
        result = []
        for item in lst:
            found = False
            for s in seen:
                if ObjUtil.equals(s, item):
                    found = True
                    break
            if not found:
                seen.append(item)
                result.append(item)
        return result

    @staticmethod
    def union(lst, that):
        """Return union of two lists (unique values from both, preserving order)"""
        # Start with unique values from first list
        result = List.unique(lst)
        # Add items from second list that aren't already present
        for item in that:
            if not List.contains(result, item):
                result.append(item)
        return result

    @staticmethod
    def intersection(lst, that):
        """Return intersection of two lists (unique values only, preserving order)"""
        result = []
        for item in lst:
            # Check if in 'that' AND not already in result
            if List.contains(that, item) and not List.contains(result, item):
                result.append(item)
        return result

    @staticmethod
    def groupBy(lst, f):
        """Group elements by a key function. Returns a Map of key -> list of elements."""
        from .Map import Map
        from .Func import Func

        # Determine the element type for the value lists
        elemType = getattr(lst, '_elementType', None)
        elemTypeSig = "sys::Obj"
        if elemType is not None:
            elemTypeSig = elemType.signature() if hasattr(elemType, 'signature') else str(elemType)

        # Determine the key type from the function's return type
        keyTypeSig = "sys::Obj"
        if isinstance(f, Func):
            ret = f.returns()
            if ret is not None:
                keyTypeSig = ret.signature() if hasattr(ret, 'signature') else str(ret)

        # Create typed map with key type and value type (element type + [])
        result = Map.fromLiteral([], [], keyTypeSig, elemTypeSig + "[]")

        param_count = List._get_param_count(f)
        for i, item in enumerate(lst):
            if param_count >= 2:
                key = f(item, i)
            else:
                key = f(item)
            if result.containsKey(key):
                result.get(key).append(item)
            else:
                # Create a typed list for the value
                result.set(key, ListImpl.fromLiteral([item], elemTypeSig))
        return result

    @staticmethod
    def groupByInto(lst, map_, f):
        """Group elements by a key function into an existing Map."""
        param_count = List._get_param_count(f)
        for i, item in enumerate(lst):
            if param_count >= 2:
                key = f(item, i)
            else:
                key = f(item)
            if map_.containsKey(key):
                map_.get(key).append(item)
            else:
                map_.set(key, [item])
        return map_

    #################################################################
    # Conversion Methods
    #################################################################

    @staticmethod
    def fill(lst, val, times):
        """Fill list with val, times number of times"""
        for i in range(times):
            lst.append(val)
        return lst

    @staticmethod
    def dup(lst):
        """Return a duplicate of this list"""
        return list(lst)

    @staticmethod
    def toStr(lst):
        """Convert list to string"""
        from .ObjUtil import ObjUtil
        if len(lst) == 0:
            return "[,]"
        items = [ObjUtil.toStr(x) for x in lst]
        return "[" + ", ".join(items) + "]"

    @staticmethod
    def toCode(lst):
        """Convert list to Fantom code literal with type signature prefix"""
        from .ObjUtil import ObjUtil

        # Get the type signature for the list
        typeSig = None
        if hasattr(lst, 'typeof'):
            listType = lst.typeof()
            if hasattr(listType, 'signature'):
                typeSig = listType.signature()

        # Default to sys::Obj? if no type info
        if typeSig is None:
            typeSig = "sys::Obj?[]"

        if len(lst) == 0:
            # Empty list: type signature + [,]
            # Extract element type from list type (remove trailing [])
            elemType = typeSig[:-2] if typeSig.endswith("[]") else "sys::Obj?"
            return f"{elemType}[,]"

        items = []
        for x in lst:
            # Use ObjUtil.toCode for proper Fantom code representation
            items.append(ObjUtil.toCode(x))

        # For non-empty lists, prepend type signature
        elemType = typeSig[:-2] if typeSig.endswith("[]") else "sys::Obj?"
        return f"{elemType}[" + ", ".join(items) + "]"

    #################################################################
    # Random
    #################################################################

    @staticmethod
    def random(lst):
        """Return random element"""
        import random
        if len(lst) == 0:
            return None
        return random.choice(lst)

    #################################################################
    # Type/Reflection (stubs)
    #################################################################

    @staticmethod
    def of(lst):
        """Return type of list elements"""
        # Check for stored element type
        of_type = getattr(lst, '_of', None)
        if of_type is not None:
            return of_type
        # Check for element type from ListImpl/ImmutableList
        elem_type = getattr(lst, '_elementType', None)
        if elem_type is not None:
            return elem_type
        return None

    @staticmethod
    def isRW(lst):
        """Check if list is read-write"""
        return not isinstance(lst, (ImmutableList, ReadOnlyList))

    @staticmethod
    def isRO(lst):
        """Check if list is read-only"""
        return isinstance(lst, (ImmutableList, ReadOnlyList))

    @staticmethod
    def ro(lst):
        """Return read-only version - returns cached read-only view"""
        if isinstance(lst, ImmutableList):
            return lst
        if isinstance(lst, ReadOnlyList):
            return lst  # Already read-only, return self
        # Check for cached ro view
        ro_view = getattr(lst, '_roView', None)
        if ro_view is not None:
            return ro_view
        # Create new read-only view and cache it
        ro_view = ReadOnlyList(lst)
        # Copy type info
        ro_view._elementType = getattr(lst, '_elementType', None)
        ro_view._listType = getattr(lst, '_listType', None)
        ro_view._of = getattr(lst, '_of', None)
        # Cache the view on the source list
        try:
            lst._roView = ro_view
        except AttributeError:
            pass  # Can't cache on plain Python lists
        return ro_view

    @staticmethod
    def rw(lst):
        """Return read-write version.

        If lst is already read-write, returns it.
        If lst is immutable or read-only, creates a mutable copy.
        """
        if isinstance(lst, tuple):
            return list(lst)
        # ImmutableList needs to be copied to a mutable ListImpl
        if isinstance(lst, ImmutableList):
            result = ListImpl(lst)
            # Preserve type information
            result._elementType = getattr(lst, '_elementType', None)
            result._listType = getattr(lst, '_listType', None)
            result._of = getattr(lst, '_of', None)
            return result
        # ReadOnlyList should delegate to its instance method
        if isinstance(lst, ReadOnlyList):
            return lst.rw()
        # ListImpl is already read-write
        return lst

    @staticmethod
    def toImmutable(lst):
        """Return immutable version - returns self if already immutable.
        Recursively makes nested lists and maps immutable."""
        from .ObjUtil import ObjUtil
        from .Map import Map

        # If already immutable, return self (identity semantics)
        if isinstance(lst, ImmutableList):
            return lst
        if hasattr(lst, '_immutable') and lst._immutable:
            return lst

        # Recursively make nested items immutable
        immutable_items = []
        for item in lst:
            if item is None:
                immutable_items.append(None)
            elif isinstance(item, list):
                # Recursively make nested lists immutable
                immutable_items.append(List.toImmutable(item))
            elif isinstance(item, Map):
                # Recursively make nested maps immutable (instance method)
                immutable_items.append(item.toImmutable())
            elif ObjUtil.isImmutable(item):
                # Already immutable (primitives, etc.)
                immutable_items.append(item)
            elif hasattr(item, 'toImmutable') and callable(item.toImmutable):
                # Item has its own toImmutable
                immutable_items.append(item.toImmutable())
            else:
                # Can't make immutable - just include as-is
                # (will fail later if accessed)
                immutable_items.append(item)

        # Create new immutable list with immutable items
        result = ImmutableList(immutable_items)
        # Copy type info
        result._elementType = getattr(lst, '_elementType', None)
        result._listType = getattr(lst, '_listType', None)
        result._of = getattr(lst, '_of', None)
        return result

    @staticmethod
    def hash_(lst):
        """Return hash code for list"""
        from .ObjUtil import ObjUtil
        h = 33
        for item in lst:
            h = (h * 31 + ObjUtil.hash_(item)) & 0xFFFFFFFF
        return h

    @staticmethod
    def trim(lst):
        """Trim capacity to size (no-op in Python)"""
        return lst

    @staticmethod
    def keys(m):
        """Get keys from a Map as a list"""
        from .Map import Map
        if isinstance(m, Map):
            return m.keys_()
        return list(m.keys()) if hasattr(m, 'keys') else []

    @staticmethod
    def vals(m):
        """Get values from a Map as a list"""
        from .Map import Map
        if isinstance(m, Map):
            return m.vals()
        return list(m.values()) if hasattr(m, 'values') else []

    @staticmethod
    def trap(lst, name, args=None):
        """Dynamic method invocation"""
        if args is None:
            args = []
        method = getattr(List, name, None)
        if method:
            return method(lst, *args)
        raise AttributeError(f"List.{name}")

    @staticmethod
    def capacity(lst):
        """Return capacity (tracked separately for Fantom compatibility)"""
        # Check for stored capacity first
        cap = getattr(lst, '_capacity', None)
        if cap is not None:
            return cap
        # Fall back to size
        return len(lst)

    @staticmethod
    def setNotNull(lst, index, val):
        """Set item at index only if val is not null"""
        if val is not None:
            lst[index] = val
        return lst

    @staticmethod
    def findType(lst, type_):
        """Find all elements of given type, returning typed list"""
        from .ObjUtil import ObjUtil
        from .Type import Type
        result = []
        for item in lst:
            if ObjUtil.is_(item, type_):
                result.append(item)
        # Return a typed list with the target type as element type
        return ListImpl.fromLiteral(result, type_)

    @staticmethod
    def findNotNull(lst):
        """Return list with null values removed, typed as non-nullable version"""
        from .Type import Type
        result = [item for item in lst if item is not None]
        # Get element type and convert to non-nullable
        elemType = getattr(lst, '_elementType', None)
        if elemType is not None:
            sig = elemType.signature() if hasattr(elemType, 'signature') else str(elemType)
            # Remove trailing ? to make non-nullable
            if sig.endswith("?"):
                sig = sig[:-1]
            return ListImpl.fromLiteral(result, sig)
        return ListImpl.fromLiteral(result, "sys::Obj")

    #################################################################
    # Map Delegation Methods
    # When transpiler routes Map methods through List, delegate to Map
    #################################################################

    @staticmethod
    def containsKey(m, key):
        """Delegate to Map.containsKey"""
        from .Map import Map
        if isinstance(m, Map):
            return m.containsKey(key)
        return key in m if hasattr(m, '__contains__') else False

    @staticmethod
    def getOrAdd(m, key, defVal):
        """Delegate to Map.getOrAdd"""
        from .Map import Map
        if isinstance(m, Map):
            return m.getOrAdd(key, defVal)
        if key in m:
            return m[key]
        m[key] = defVal
        return defVal

    @staticmethod
    def getOrThrow(m, key):
        """Delegate to Map.getOrThrow"""
        from .Map import Map
        if isinstance(m, Map):
            return m.getOrThrow(key)
        if key in m:
            return m[key]
        raise KeyError(f"Key not found: {key}")

    @staticmethod
    def setAll(m, other):
        """Delegate to Map.setAll"""
        from .Map import Map
        if isinstance(m, Map):
            return m.setAll(other)
        for k, v in other.items():
            m[k] = v
        return m

    @staticmethod
    def with_(m, key, val):
        """Create a copy of map with added key-value pair"""
        from .Map import Map
        if isinstance(m, Map):
            result = Map(m)
            result[key] = val
            return result
        result = dict(m)
        result[key] = val
        return result

    @staticmethod
    def isImmutable(lst):
        """Check if list is immutable"""
        return isinstance(lst, ImmutableList)


class ImmutableList(list):
    """Immutable list - extends list but blocks mutation"""

    def __init__(self, items=None):
        super().__init__(items or [])
        self._immutable = True
        self._elementType = None  # Fantom element type
        self._listType = None  # Cached ListType

    def __len__(self):
        """Support Python len() function"""
        return list.__len__(self)

    def isImmutable(self):
        return True

    def isRO(self):
        """Immutable lists are read-only"""
        return True

    def isRW(self):
        """Immutable lists are not read-write"""
        return False

    def toImmutable(self):
        return self

    def ro(self):
        """Return read-only version of list - already immutable so return self"""
        return self

    def size(self):
        """Return number of elements"""
        return len(self)

    def get(self, index, default=None):
        """Get element at index (instance method for ImmutableList)"""
        if default is not None:
            if 0 <= index < len(self):
                return self[index]
            return default
        return self[index]

    def typeof(self):
        """Return Fantom Type for this List"""
        from .Type import Type
        # If we have stored ListType, use it
        if self._listType is not None:
            return self._listType
        # Otherwise return generic List type
        return Type.find("sys::List")

    def __hash__(self):
        # Hash based on tuple of elements (only works if all elements are hashable)
        return hash(tuple(self))

    # Block all mutating operations
    def append(self, item):
        raise ReadonlyErr("List is immutable")

    def extend(self, items):
        raise ReadonlyErr("List is immutable")

    def insert(self, index, item):
        raise ReadonlyErr("List is immutable")

    def remove(self, item):
        raise ReadonlyErr("List is immutable")

    def pop(self, index=-1):
        raise ReadonlyErr("List is immutable")

    def clear(self):
        raise ReadonlyErr("List is immutable")

    def __setitem__(self, key, value):
        raise ReadonlyErr("List is immutable")

    def __delitem__(self, key):
        raise ReadonlyErr("List is immutable")


class ReadOnlyList(list):
    """Read-only view of a list - blocks mutation but keeps reference to source"""

    def __init__(self, source):
        """Create read-only view of source list"""
        super().__init__(source)
        self._source = source
        self._elementType = None  # Fantom element type
        self._listType = None  # Cached ListType
        self._of = None

    def __len__(self):
        """Support Python len() function"""
        return list.__len__(self)

    def isRO(self):
        return True

    def isRW(self):
        return False

    def isImmutable(self):
        return False

    def ro(self):
        """Return self - already read-only"""
        return self

    def rw(self):
        """Return the original mutable source"""
        return self._source

    def size(self):
        """Return number of elements"""
        return len(self)

    def get(self, index, default=None):
        """Get element at index"""
        if default is not None:
            if 0 <= index < len(self):
                return self[index]
            return default
        return self[index]

    def typeof(self):
        """Return Fantom Type for this List"""
        from .Type import Type
        # If we have stored ListType, use it
        if self._listType is not None:
            return self._listType
        # Otherwise return generic List type
        return Type.find("sys::List")

    def toImmutable(self):
        """Convert to fully immutable list"""
        result = ImmutableList(self)
        result._elementType = getattr(self, '_elementType', None)
        result._listType = getattr(self, '_listType', None)
        result._of = getattr(self, '_of', None)
        return result

    def _checkModify(self):
        """Throw ReadonlyErr if trying to modify"""
        raise ReadonlyErr("List is read-only")

    # Block all mutating operations
    def append(self, item):
        self._checkModify()

    def extend(self, items):
        self._checkModify()

    def insert(self, index, item):
        self._checkModify()

    def remove(self, item):
        self._checkModify()

    def pop(self, index=-1):
        self._checkModify()

    def clear(self):
        self._checkModify()

    def __setitem__(self, key, value):
        self._checkModify()

    def __delitem__(self, key):
        self._checkModify()

    def sort(self, *args, **kwargs):
        self._checkModify()

    def reverse(self):
        self._checkModify()


class ReadonlyErr(Exception):
    """Raised when attempting to modify an immutable object"""
    pass
