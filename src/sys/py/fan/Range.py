#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Range(Obj):
    """Range type - represents an integer range"""

    def __init__(self, start, end, exclusive=False):
        super().__init__()
        self._start = start
        self._end = end
        self._exclusive = exclusive

    @staticmethod
    def make(start, end, exclusive=False):
        return Range(start, end, exclusive)

    @staticmethod
    def makeInclusive(start, end):
        return Range(start, end, False)

    @staticmethod
    def makeExclusive(start, end):
        return Range(start, end, True)

    def start(self):
        return self._start

    def end(self):
        return self._end

    def inclusive(self):
        return not self._exclusive

    def exclusive(self):
        return self._exclusive

    def isEmpty(self):
        # For upward ranges (start <= end)
        if self._start <= self._end:
            if self._exclusive:
                return self._start >= self._end
            return False  # inclusive range always has at least one element
        # For downward ranges (start > end)
        else:
            if self._exclusive:
                return self._start <= self._end
            return False  # inclusive range always has at least one element

    def min(self):
        if self.isEmpty():
            return None
        return min(self._start, self._lastVal())

    def max(self):
        if self.isEmpty():
            return None
        return max(self._start, self._lastVal())

    def first(self):
        if self.isEmpty():
            return None
        return self._start

    def last(self):
        if self.isEmpty():
            return None
        return self._lastVal()

    def _lastVal(self):
        """Internal method to get last value without null check"""
        if self._exclusive:
            if self._start <= self._end:
                return self._end - 1
            else:
                return self._end + 1
        return self._end

    def size(self):
        if self._exclusive:
            return abs(self._end - self._start)
        return abs(self._end - self._start) + 1

    def contains(self, val):
        if self._start <= self._end:
            if self._exclusive:
                return self._start <= val < self._end
            return self._start <= val <= self._end
        else:
            if self._exclusive:
                return self._end < val <= self._start
            return self._end <= val <= self._start

    def each(self, f):
        if self._start <= self._end:
            end = self._end if self._exclusive else self._end + 1
            for i in range(self._start, end):
                f(i)
        else:
            end = self._end if self._exclusive else self._end - 1
            for i in range(self._start, end, -1):
                f(i)

    def eachWhile(self, f):
        if self._start <= self._end:
            end = self._end if self._exclusive else self._end + 1
            for i in range(self._start, end):
                result = f(i)
                if result is not None:
                    return result
        else:
            end = self._end if self._exclusive else self._end - 1
            for i in range(self._start, end, -1):
                result = f(i)
                if result is not None:
                    return result
        return None

    def map(self, f):
        """Map each element using function"""
        result = []
        self.each(lambda i: result.append(f(i)))
        return result

    def map_(self, f):
        """Alias for map to match List.map_ naming convention"""
        return self.map(f)

    def offset(self, n):
        """Return new range shifted by n"""
        return Range(self._start + n, self._end + n, self._exclusive)

    @staticmethod
    def fromStr(s, checked=True):
        """Parse range from string like '2..5' or '2..<5'"""
        if s is None:
            if checked:
                from .Err import ParseErr
                raise ParseErr(f"Invalid Range: {s}")
            return None

        # Check for exclusive range
        exclusive_idx = s.find('..<')
        if exclusive_idx >= 0:
            try:
                start = int(s[:exclusive_idx])
                end = int(s[exclusive_idx + 3:])
                return Range(start, end, True)
            except ValueError:
                if checked:
                    from .Err import ParseErr
                    raise ParseErr(f"Invalid Range: {s}")
                return None

        # Check for inclusive range
        inclusive_idx = s.find('..')
        if inclusive_idx >= 0:
            try:
                start = int(s[:inclusive_idx])
                end = int(s[inclusive_idx + 2:])
                return Range(start, end, False)
            except ValueError:
                if checked:
                    from .Err import ParseErr
                    raise ParseErr(f"Invalid Range: {s}")
                return None

        # Invalid format
        if checked:
            from .Err import ParseErr
            raise ParseErr(f"Invalid Range: {s}")
        return None

    def toList(self):
        from .List import List
        result = []
        self.each(lambda i: result.append(i))
        return List.fromLiteral(result, "sys::Int")

    def random(self):
        """Return a random integer within this range."""
        import random
        if self.isEmpty():
            return None
        # Calculate first and last values
        first = self._start
        last = self._lastVal()
        # Ensure first <= last for randint
        if first <= last:
            return random.randint(first, last)
        else:
            return random.randint(last, first)

    def toStr(self):
        if self._exclusive:
            return f"{self._start}..<{self._end}"
        return f"{self._start}..{self._end}"

    def hash(self):
        return hash((self._start, self._end, self._exclusive))

    def equals(self, other):
        if not isinstance(other, Range):
            return False
        return (self._start == other._start and
                self._end == other._end and
                self._exclusive == other._exclusive)

    def __iter__(self):
        """Allow Python iteration"""
        return iter(self.toList())

    def __len__(self):
        """Allow Python len()"""
        return self.size()

    def __contains__(self, val):
        """Allow Python 'in' operator"""
        return self.contains(val)

    def typeof(self):
        """Return Fantom Type for Range"""
        from .Type import Type
        return Type.find("sys::Range")

    def start_(self, size=None):
        """Resolve start index for given size (handles negative indexing).

        Args:
            size: The size to resolve against, or None to return raw start

        Returns:
            Resolved start index (0-based)
        """
        if size is None:
            return self._start

        x = self._start
        if x < 0:
            x = size + x
        if x > size:
            from .Err import IndexErr
            raise IndexErr.make(str(self))
        return x

    def end_(self, size=None):
        """Resolve end index for given size (handles negative indexing, exclusive adjustment).

        Args:
            size: The size to resolve against, or None to return raw end

        Returns:
            Resolved end index (0-based, inclusive)
        """
        if size is None:
            return self._end

        x = self._end
        if x < 0:
            x = size + x
        if self._exclusive:
            x -= 1
        if x >= size:
            from .Err import IndexErr
            raise IndexErr.make(str(self))
        return x
