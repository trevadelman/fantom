#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Duration(Obj):
    """Duration type - represents a span of time in nanoseconds"""

    # Value type semantics - two durations with same ticks are === equal
    _same_uses_equals = True

    # Cached singleton instances for common values
    _defVal = None
    _cache = {}  # Cache for common durations

    def __init__(self, ticks=0):
        super().__init__()
        self._ticks = ticks  # nanoseconds

    @staticmethod
    def def_val():
        if Duration._defVal is None:
            Duration._defVal = Duration(0)
        return Duration._defVal

    @staticmethod
    def min_val():
        """Minimum duration value"""
        return Duration(-9223372036854775808)

    @staticmethod
    def max_val():
        """Maximum duration value"""
        return Duration(9223372036854775807)

    @staticmethod
    def make(ticks):
        """Make from nanoseconds - caches common values"""
        # Return cached singleton for 0
        if ticks == 0:
            return Duration.def_val()
        # Cache small whole-unit durations for identity semantics
        if ticks in Duration._cache:
            return Duration._cache[ticks]
        # Create new and potentially cache it
        d = Duration(ticks)
        # Cache common unit values (1ms, 1sec, 1min, etc up to reasonable size)
        if Duration._should_cache(ticks):
            Duration._cache[ticks] = d
        return d

    @staticmethod
    def _should_cache(ticks):
        """Determine if this duration should be cached for identity semantics"""
        # Cache durations that are whole units up to 1 day
        if ticks < 0:
            return False
        if ticks <= 86_400_000_000_000:  # Up to 1 day
            # Cache if it's a whole unit
            if ticks % 1_000_000 == 0:  # At least 1ms precision
                return True
        return False

    @staticmethod
    def now():
        """Return current time as duration since epoch"""
        import time
        return Duration(int(time.time_ns()))

    @staticmethod
    def now_ticks():
        """Return current time as nanoseconds since epoch"""
        import time
        return time.time_ns()

    @staticmethod
    def boot():
        """Return boot time (stub - returns a fixed time before now)"""
        if not hasattr(Duration, '_boot'):
            import time
            Duration._boot = Duration(int(time.time_ns()) - 1_000_000_000)  # 1 sec before first call
        return Duration._boot

    @staticmethod
    def uptime():
        """Return uptime since boot"""
        return Duration.now().minus(Duration.boot())

    @staticmethod
    def from_str(s, checked=True):
        """Parse duration string like '5sec', '3min', '100ms', '0.5hr'"""
        try:
            s = s.strip()
            if s.endswith("ns"):
                return Duration(int(float(s[:-2])))
            elif s.endswith("ms"):
                return Duration(int(float(s[:-2]) * 1_000_000))
            elif s.endswith("sec"):
                return Duration(int(float(s[:-3]) * 1_000_000_000))
            elif s.endswith("min"):
                return Duration(int(float(s[:-3]) * 60_000_000_000))
            elif s.endswith("hr"):
                return Duration(int(float(s[:-2]) * 3_600_000_000_000))
            elif s.endswith("day"):
                return Duration(int(float(s[:-3]) * 86_400_000_000_000))
            else:
                raise ValueError()
        except:
            if not checked:
                return None
            from .Err import ParseErr
            raise ParseErr.make_str("Duration", s)

    def ticks(self):
        """Get nanoseconds"""
        return self._ticks

    def to_nanos(self):
        return self._ticks

    def to_millis(self):
        return self._ticks // 1_000_000

    def to_sec(self):
        return self._ticks // 1_000_000_000

    def to_min(self):
        return self._ticks // 60_000_000_000

    def to_hour(self):
        return self._ticks // 3_600_000_000_000

    def to_day(self):
        return self._ticks // 86_400_000_000_000

    # Arithmetic
    def plus(self, that):
        return Duration(self._ticks + that._ticks)

    def minus(self, that):
        return Duration(self._ticks - that._ticks)

    def mult(self, scalar):
        """Multiply by Int or Float"""
        if isinstance(scalar, float):
            return Duration(int(self._ticks * scalar))
        return Duration(self._ticks * scalar)

    def div(self, scalar):
        """Divide by Int or Float"""
        if isinstance(scalar, float):
            return Duration(int(self._ticks / scalar))
        return Duration(self._ticks // scalar)

    def negate(self):
        return Duration(-self._ticks)

    def abs_(self):
        """Return absolute value"""
        if self._ticks >= 0:
            return self
        return Duration(-self._ticks)

    def min_(self, that):
        """Return lesser of this and that"""
        if self._ticks <= that._ticks:
            return self
        return that

    def max_(self, that):
        """Return greater of this and that"""
        if self._ticks >= that._ticks:
            return self
        return that

    def clamp(self, minVal, maxVal):
        """Clamp to range [min, max]"""
        if self._ticks < minVal._ticks:
            return minVal
        if self._ticks > maxVal._ticks:
            return maxVal
        return self

    def floor(self, accuracy):
        """Floor to given accuracy duration"""
        if accuracy._ticks == 0:
            return self
        ticks = (self._ticks // accuracy._ticks) * accuracy._ticks
        # Return self if result is same value (for identity semantics)
        if ticks == self._ticks:
            return self
        return Duration.make(ticks)

    # Comparison
    def compare(self, that):
        if that is None:
            return 1
        if self._ticks < that._ticks:
            return -1
        if self._ticks > that._ticks:
            return 1
        return 0

    def equals(self, that):
        if that is None:
            return False
        if not isinstance(that, Duration):
            return False
        return self._ticks == that._ticks

    def hash(self):
        return self._ticks

    def __hash__(self):
        return self._ticks

    def to_str(self):
        """Convert to string representation"""
        ticks = abs(self._ticks)
        neg = "-" if self._ticks < 0 else ""

        if ticks == 0:
            return "0ns"
        # Check for whole units (prefer largest unit that divides evenly)
        if ticks % 86_400_000_000_000 == 0:
            return f"{neg}{ticks // 86_400_000_000_000}day"
        if ticks % 3_600_000_000_000 == 0:
            return f"{neg}{ticks // 3_600_000_000_000}hr"
        if ticks % 60_000_000_000 == 0:
            return f"{neg}{ticks // 60_000_000_000}min"
        if ticks % 1_000_000_000 == 0:
            return f"{neg}{ticks // 1_000_000_000}sec"
        if ticks % 1_000_000 == 0:
            return f"{neg}{ticks // 1_000_000}ms"
        if ticks < 1_000_000:
            return f"{neg}{ticks}ns"
        # Fractional values
        if ticks < 1_000_000_000:
            ms = ticks / 1_000_000
            return f"{neg}{ms}ms"
        if ticks < 60_000_000_000:
            sec = ticks / 1_000_000_000
            return f"{neg}{sec}sec"
        if ticks < 3_600_000_000_000:
            min_ = ticks / 60_000_000_000
            return f"{neg}{min_}min"
        if ticks < 86_400_000_000_000:
            hr = ticks / 3_600_000_000_000
            return f"{neg}{hr}hr"
        day = ticks / 86_400_000_000_000
        return f"{neg}{day}day"

    def __repr__(self):
        return self.to_str()

    def to_code(self):
        """Return Fantom code representation"""
        ticks = abs(self._ticks)
        neg = "-" if self._ticks < 0 else ""

        if ticks == 0:
            return "0ns"
        elif ticks % 86_400_000_000_000 == 0:
            return f"{neg}{ticks // 86_400_000_000_000}day"
        elif ticks % 3_600_000_000_000 == 0:
            return f"{neg}{ticks // 3_600_000_000_000}hr"
        elif ticks % 60_000_000_000 == 0:
            return f"{neg}{ticks // 60_000_000_000}min"
        elif ticks % 1_000_000_000 == 0:
            return f"{neg}{ticks // 1_000_000_000}sec"
        elif ticks % 1_000_000 == 0:
            return f"{neg}{ticks // 1_000_000}ms"
        else:
            return f"{neg}{ticks}ns"

    def to_locale(self):
        """Return locale string representation"""
        ticks = abs(self._ticks)
        neg = "-" if self._ticks < 0 else ""

        if ticks == 0:
            return "0ns"
        elif ticks < 1000:
            return f"{neg}{ticks}ns"
        elif ticks < 1_000_000:
            # Show as fractional ms (0.003ms, 0.078ms, 0.8ms)
            # Truncate to 3 decimal places (don't round)
            us = ticks // 1000  # Truncate to microseconds
            ms = us / 1000
            formatted = f"{ms:.3f}".rstrip('0').rstrip('.')
            return f"{neg}{formatted}ms"
        elif ticks < 2_000_000_000:
            # Show as ms (truncate to 3 decimal places)
            if ticks % 1_000_000 == 0:
                ms = ticks // 1_000_000
                # Special case: exactly 1ms shows as "1.0ms"
                if ms == 1:
                    return f"{neg}1.0ms"
                # Other whole ms - show without decimals
                return f"{neg}{ms}ms"
            # Fractional ms - truncate to microseconds
            us = ticks // 1000
            ms = us / 1000
            formatted = f"{ms:.3f}".rstrip('0').rstrip('.')
            return f"{neg}{formatted}ms"
        else:
            # Build compound string
            parts = []
            remaining = ticks

            days = remaining // 86_400_000_000_000
            if days > 0:
                parts.append(f"{days}day" if days == 1 else f"{days}days")
                remaining %= 86_400_000_000_000

            hours = remaining // 3_600_000_000_000
            if hours > 0:
                parts.append(f"{hours}hr")
                remaining %= 3_600_000_000_000

            mins = remaining // 60_000_000_000
            if mins > 0:
                parts.append(f"{mins}min")
                remaining %= 60_000_000_000

            secs = remaining // 1_000_000_000
            if secs > 0:
                parts.append(f"{secs}sec")

            return neg + " ".join(parts)

    def to_iso(self):
        """Return ISO 8601 duration string"""
        ticks = self._ticks
        neg = "-" if ticks < 0 else ""
        ticks = abs(ticks)

        if ticks == 0:
            return "PT0S"

        parts = []
        has_date = False
        has_time = False

        # Days
        days = ticks // 86_400_000_000_000
        if days > 0:
            parts.append(f"P{days}D")
            ticks %= 86_400_000_000_000
            has_date = True

        # Time components
        hours = ticks // 3_600_000_000_000
        ticks %= 3_600_000_000_000
        mins = ticks // 60_000_000_000
        ticks %= 60_000_000_000
        secs = ticks / 1_000_000_000

        if hours > 0 or mins > 0 or secs > 0:
            has_time = True
            if not has_date:
                parts.append("PT")
            else:
                parts.append("T")

            if hours > 0:
                parts.append(f"{hours}H")
            if mins > 0:
                parts.append(f"{mins}M")
            if secs > 0:
                # Format seconds with fractional part
                if secs == int(secs):
                    parts.append(f"{int(secs)}S")
                else:
                    # Format with proper decimal places
                    s = f"{secs:.9f}".rstrip('0').rstrip('.')
                    parts.append(f"{s}S")
        elif has_date:
            pass  # Just the date part
        else:
            return "PT0S"

        return neg + "".join(parts)

    @staticmethod
    def from_iso(s, checked=True):
        """Parse ISO 8601 duration string"""
        try:
            orig = s
            neg = False
            if s.startswith("-"):
                neg = True
                s = s[1:]

            if not s.startswith("P"):
                raise ValueError("Missing P prefix")
            s = s[1:]

            ticks = 0
            in_time = False

            while s:
                if s[0] == "T":
                    in_time = True
                    s = s[1:]
                    continue

                # Parse number
                i = 0
                while i < len(s) and (s[i].isdigit() or s[i] == '.'):
                    i += 1
                if i == 0:
                    raise ValueError("Expected number")

                num_str = s[:i]
                num = float(num_str) if '.' in num_str else int(num_str)
                unit = s[i] if i < len(s) else ''
                s = s[i+1:]

                if in_time:
                    if unit == 'H':
                        ticks += int(num * 3_600_000_000_000)
                    elif unit == 'M':
                        ticks += int(num * 60_000_000_000)
                    elif unit == 'S':
                        ticks += int(num * 1_000_000_000)
                    else:
                        raise ValueError(f"Unknown time unit: {unit}")
                else:
                    if unit == 'D':
                        ticks += int(num * 86_400_000_000_000)
                    else:
                        raise ValueError(f"Unknown date unit: {unit}")

            if neg:
                ticks = -ticks
            return Duration(ticks)
        except Exception as e:
            if not checked:
                return None
            from .Err import ParseErr
            raise ParseErr.make_str("Duration", orig)

    def is_immutable(self):
        return True

    # Python operator overloads for convenience
    def __add__(self, other):
        return self.plus(other)

    def __sub__(self, other):
        return self.minus(other)

    def __mul__(self, other):
        return self.mult(other)

    def __rmul__(self, other):
        return self.mult(other)

    def __truediv__(self, other):
        return self.div(other)

    def __neg__(self):
        return self.negate()

    def __eq__(self, other):
        return self.equals(other)

    def __lt__(self, other):
        return self.compare(other) < 0

    def __le__(self, other):
        return self.compare(other) <= 0

    def __gt__(self, other):
        return self.compare(other) > 0

    def __ge__(self, other):
        return self.compare(other) >= 0

    def literal_encode(self, out):
        """Encode for serialization.

        Duration literals are written directly as their string representation.
        For example: 5sec, 3min, 100ms
        """
        out.w(self.to_str())

    def typeof(self):
        """Return Fantom Type for Duration"""
        from .Type import Type
        return Type.find("sys::Duration")

    #################################################################
    # Python Interop (to_py / from_py)
    #################################################################

    def to_py(self):
        """Convert to native Python datetime.timedelta.

        Returns:
            A datetime.timedelta object.

        Note: Python timedelta only has microsecond precision, so
              nanoseconds are truncated to microseconds.

        Example:
            >>> Duration.from_str("5sec").to_py()
            datetime.timedelta(seconds=5)
        """
        from datetime import timedelta
        # Convert nanoseconds to microseconds (Python's finest resolution)
        microseconds = self._ticks // 1000
        return timedelta(microseconds=microseconds)

    @staticmethod
    def from_py(td):
        """Create Duration from native Python datetime.timedelta.

        Args:
            td: Python datetime.timedelta object

        Returns:
            Fantom Duration

        Example:
            >>> from datetime import timedelta
            >>> Duration.from_py(timedelta(seconds=30))
            Duration("30sec")
        """
        # Convert timedelta to nanoseconds
        # timedelta.total_seconds() gives seconds as float
        total_ns = int(td.total_seconds() * 1_000_000_000)
        return Duration.make(total_ns)
