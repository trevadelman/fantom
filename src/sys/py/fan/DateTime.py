#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from datetime import datetime as py_datetime, timezone as py_timezone
from .Obj import Obj
from .Month import Month


class DateTime(Obj):
    """DateTime represents an absolute instant in time with nanosecond precision."""

    # Fantom epoch is 2000-01-01 00:00:00 UTC
    # Python epoch is 1970-01-01 00:00:00 UTC
    # Difference in nanoseconds
    _EPOCH_DIFF_NS = 946684800 * 1000000000  # seconds from 1970 to 2000 * ns/sec

    # Nanoseconds per unit - use these constants for precision
    _NS_PER_SEC = 1000000000
    _NS_PER_MIN = 60 * _NS_PER_SEC
    _NS_PER_HOUR = 60 * _NS_PER_MIN
    _NS_PER_DAY = 24 * _NS_PER_HOUR

    # Days before each month (0-indexed) for non-leap and leap years
    _DAYS_BEFORE_MONTH = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    _DAYS_BEFORE_MONTH_LEAP = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

    _defVal = None
    _cached = None      # Cached DateTime.now() value
    _cachedUtc = None   # Cached DateTime.now_utc() value

    @staticmethod
    def _is_leap_year(year):
        """Check if year is a leap year"""
        if (year & 3) != 0:
            return False
        return (year % 100 != 0) or (year % 400 == 0)

    @staticmethod
    def _days_since_epoch(year, month_ord, day):
        """Calculate days since Fantom epoch (2000-01-01) using integer arithmetic only.
        month_ord is 0-indexed (0=Jan, 11=Dec)"""
        # Count days from 2000-01-01 to given date
        # For years >= 2000, count forward; for years < 2000, count backward

        total_days = 0

        if year >= 2000:
            # Count days from 2000 to the start of the target year
            for y in range(2000, year):
                total_days += 366 if DateTime._is_leap_year(y) else 365
        else:
            # Count days backward from 2000 to the target year
            for y in range(year, 2000):
                total_days -= 366 if DateTime._is_leap_year(y) else 365

        # Add days for months in the target year
        if DateTime._is_leap_year(year):
            total_days += DateTime._DAYS_BEFORE_MONTH_LEAP[month_ord]
        else:
            total_days += DateTime._DAYS_BEFORE_MONTH[month_ord]

        # Add days in the current month (1-indexed day, so subtract 1)
        total_days += day - 1

        return total_days

    @staticmethod
    def _compute_ticks(year, month_ord, day, hour, min_, sec, ns, tz_offset_secs=0):
        """Compute ticks (nanoseconds since Fantom epoch) using integer arithmetic only.
        This avoids floating point precision issues.
        tz_offset_secs is the timezone offset in seconds (positive = east of UTC)"""

        # Get days since epoch for UTC
        days = DateTime._days_since_epoch(year, month_ord, day)

        # Convert to nanoseconds and add time components
        ticks = (days * DateTime._NS_PER_DAY +
                 hour * DateTime._NS_PER_HOUR +
                 min_ * DateTime._NS_PER_MIN +
                 sec * DateTime._NS_PER_SEC +
                 ns)

        # Adjust for timezone offset to get UTC ticks
        ticks -= tz_offset_secs * DateTime._NS_PER_SEC

        return ticks

    def __init__(self, year=2000, month=None, day=1, hour=0, min_=0, sec=0, ns=0, tz=None):
        super().__init__()
        from .TimeZone import TimeZone

        # Handle string constructor: DateTime("2009-06-04T07:52:00-04:00 New_York")
        if isinstance(year, str):
            parsed = DateTime.from_str(year)
            self._year = parsed._year
            self._month = parsed._month
            self._day = parsed._day
            self._hour = parsed._hour
            self._min = parsed._min
            self._sec = parsed._sec
            self._ns = parsed._ns
            self._tz = parsed._tz
            self._ticks = parsed._ticks
            return

        if month is None:
            month = Month.jan()
        # Handle integer month (1-12) or Month object
        if isinstance(month, int):
            month = Month._get(month - 1)
        if tz is None:
            tz = TimeZone.cur()

        self._year = year
        self._month = month
        self._day = day
        self._hour = hour
        self._min = min_
        self._sec = sec
        self._ns = ns
        self._tz = tz

        # Calculate ticks (nanoseconds since Fantom epoch 2000-01-01)
        # Use integer-only arithmetic to preserve nanosecond precision
        month_ord = month.ordinal() if hasattr(month, 'ordinal') else month - 1

        # Get timezone offset in seconds for this datetime
        # Use rule-based DST detection to handle ambiguous times correctly
        tz_offset_secs = 0
        try:
            # Try rule-based DST detection first (matches Fantom/JS behavior exactly)
            rule = tz._get_rule(year) if hasattr(tz, '_get_rule') else None
            if rule is not None:
                # Use rule offset (standard time offset)
                tz_offset_secs = rule.offset
                # Calculate DST offset using rule
                from .TimeZone import _dst_offset
                time_in_secs = hour * 3600 + min_ * 60 + sec
                dst_offset = _dst_offset(rule, year, month_ord, day, time_in_secs)
                if dst_offset != 0:
                    tz_offset_secs += dst_offset
            else:
                # Fall back to Python datetime-based detection for timezones without rules
                offset_dur = tz.offset(year)
                tz_offset_secs = offset_dur.to_sec() if hasattr(offset_dur, 'to_sec') else offset_dur
                month_num = month_ord + 1
                if hasattr(tz, '_tz') and tz._tz is not None:
                    dt = py_datetime(year, month_num, day, hour, min_, sec, tzinfo=tz._tz)
                    dst = dt.dst()
                    if dst is not None and dst.total_seconds() != 0:
                        tz_offset_secs += int(dst.total_seconds())
        except Exception:
            pass

        self._ticks = DateTime._compute_ticks(year, month_ord, day, hour, min_, sec, ns, tz_offset_secs)

    @staticmethod
    def def_val():
        """Default value: 2000-01-01T00:00:00Z UTC"""
        if DateTime._defVal is None:
            from .TimeZone import TimeZone
            DateTime._defVal = DateTime(2000, Month.jan(), 1, 0, 0, 0, 0, TimeZone.utc())
        return DateTime._defVal

    # Sentinel for "use default tolerance" vs "null means skip tolerance check"
    _USE_DEFAULT_TOLERANCE = object()

    @staticmethod
    def now(tolerance=_USE_DEFAULT_TOLERANCE):
        """Get current date and time with caching.
        If tolerance is None, skip tolerance check but still cache.
        If tolerance is default (not passed), use 250ms tolerance.
        Otherwise, return cached value if within given tolerance.
        """
        from .TimeZone import TimeZone
        from .Duration import Duration

        # Get current ticks
        now_ticks = DateTime._now_ticks_raw()

        # Determine effective tolerance
        if tolerance is DateTime._USE_DEFAULT_TOLERANCE:
            # No argument passed - use default 250ms tolerance
            tolerance = Duration.make(250000000)  # 250ms in ns

        # Initialize cache if needed
        if DateTime._cached is None:
            DateTime._cached = DateTime.make_ticks(0, TimeZone.cur())

        # Check cache if tolerance is not null
        c = DateTime._cached
        if tolerance is not None:
            tol_ticks = tolerance.ticks() if hasattr(tolerance, 'ticks') else tolerance
            if now_ticks - c._ticks <= tol_ticks:
                return c

        # Update cache and return new value
        DateTime._cached = DateTime.make_ticks(now_ticks, TimeZone.cur())
        return DateTime._cached

    # Sentinel for nowUtc default tolerance
    _USE_DEFAULT_TOLERANCE_UTC = object()

    @staticmethod
    def now_utc(tolerance=_USE_DEFAULT_TOLERANCE_UTC):
        """Get current date and time in UTC with caching.
        If tolerance is None, skip tolerance check but still cache.
        If tolerance is default (not passed), use 250ms tolerance.
        Otherwise, return cached value if within given tolerance.
        """
        from .TimeZone import TimeZone
        from .Duration import Duration

        # Get current ticks
        now_ticks = DateTime._now_ticks_raw()

        # Determine effective tolerance
        if tolerance is DateTime._USE_DEFAULT_TOLERANCE_UTC:
            # No argument passed - use default 250ms tolerance
            tolerance = Duration.make(250000000)  # 250ms in ns

        # Initialize cache if needed
        if DateTime._cachedUtc is None:
            DateTime._cachedUtc = DateTime.make_ticks(0, TimeZone.utc())

        # Check cache if tolerance is not null
        c = DateTime._cachedUtc
        if tolerance is not None:
            tol_ticks = tolerance.ticks() if hasattr(tolerance, 'ticks') else tolerance
            if now_ticks - c._ticks <= tol_ticks:
                return c

        # Update cache and return new value
        DateTime._cachedUtc = DateTime.make_ticks(now_ticks, TimeZone.utc())
        return DateTime._cachedUtc

    @staticmethod
    def _now_ticks_raw():
        """Get current time as raw ticks (nanoseconds since Fantom epoch).

        Note: We truncate to millisecond precision to match Fantom/JS behavior.
        JavaScript's Date.getTime() only provides millisecond precision, so
        Fantom semantics are defined at that level. This ensures round-trip
        through binary I/O (which stores milliseconds) produces equal values.
        """
        import time
        # Get current time in nanoseconds since Unix epoch (1970)
        unix_ns = time.time_ns()
        # Truncate to millisecond precision to match JS/Fantom behavior
        # (JS: new Date().getTime() * nsPerMilli)
        unix_ns = (unix_ns // 1000000) * 1000000
        # Convert to Fantom epoch (2000)
        return unix_ns - DateTime._EPOCH_DIFF_NS

    @staticmethod
    def make(year=None, month=None, day=None, hour=0, min_=0, sec=0, ns=0, tz=None):
        """Create a DateTime. If year is None, returns defVal."""
        from .Err import ArgErr
        if year is None:
            return DateTime.def_val()
        if month is None:
            month = Month.jan()
        if day is None:
            day = 1
        # Handle integer month (1-12) - convert to Month object
        if isinstance(month, int):
            month = Month._get(month - 1)

        # Validate ranges (matches Fantom: 1901-2099)
        if year < 1901 or year > 2099:
            raise ArgErr.make(f"Year out of range: {year}")
        num_days = month.num_days(year)
        if day < 1 or day > num_days:
            raise ArgErr.make(f"Day out of range: {day}")
        if hour < 0 or hour > 23:
            raise ArgErr.make(f"Hour out of range: {hour}")
        if min_ < 0 or min_ > 59:
            raise ArgErr.make(f"Minute out of range: {min_}")
        if sec < 0 or sec > 59:
            raise ArgErr.make(f"Second out of range: {sec}")
        if ns < 0 or ns >= 1000000000:
            raise ArgErr.make(f"Nanosecond out of range: {ns}")

        return DateTime(year, month, day, hour, min_, sec, ns, tz)

    @staticmethod
    def _make_with_offset(year, month, day, hour, min_, sec, ns, offset_secs, tz):
        """Create DateTime with a known UTC offset in seconds.

        This is used when parsing datetime strings that include an offset like
        +05:00 or -08:00. The offset tells us exactly how to convert local time
        to UTC, which is crucial for disambiguation during DST transitions.

        Args:
            year, month, day, hour, min_, sec, ns: Local time components (month is 1-indexed)
            offset_secs: UTC offset in seconds (positive = east of UTC)
            tz: TimeZone object
        """
        from .TimeZone import TimeZone
        from .Obj import Obj

        month_ord = month - 1  # Convert to 0-indexed

        # Compute ticks using the provided offset (not the timezone's default offset)
        # This is the key difference from regular constructor
        ticks = DateTime._compute_ticks(year, month_ord, day, hour, min_, sec, ns, offset_secs)

        # Determine if DST is in effect based on offset comparison
        # If the provided offset != standard offset, then we're in DST
        std_offset = 0
        dst = False
        try:
            std_offset_dur = tz.offset(year)
            std_offset = std_offset_dur.to_sec() if hasattr(std_offset_dur, 'to_sec') else std_offset_dur
            dst_offset_dur = tz.dst_offset(year)
            dst_offset = dst_offset_dur.to_sec() if hasattr(dst_offset_dur, 'to_sec') else 0
            # DST is in effect if offset matches standard + dst offset
            dst = (offset_secs == std_offset + dst_offset) and dst_offset != 0
        except Exception:
            pass

        # Create DateTime directly without going through __init__
        result = DateTime.__new__(DateTime)
        Obj._hash_counter += 1
        result._hash = Obj._hash_counter
        result._year = year
        result._month = Month._get(month_ord)
        result._day = day
        result._hour = hour
        result._min = min_
        result._sec = sec
        result._ns = ns
        result._tz = tz
        result._ticks = ticks
        return result

    # Min/max ticks for valid year range 1901-2099
    # 1901-01-01 00:00:00 UTC = -3124137600000000000 ns from 2000-01-01
    # 2099-12-31 23:59:59.999999999 UTC = 3155759999999999999 ns from 2000-01-01
    _MIN_TICKS = -3124137600000000000
    _MAX_TICKS = 3155759999999999999

    @staticmethod
    def make_ticks(ticks, tz=None):
        """Create DateTime from ticks (nanoseconds since Fantom epoch)"""
        from .TimeZone import TimeZone
        from .Err import ArgErr
        if tz is None:
            tz = TimeZone.cur()

        # Validate ticks range (1901-2099)
        if ticks < DateTime._MIN_TICKS or ticks > DateTime._MAX_TICKS:
            raise ArgErr.make(f"Ticks out of range: {ticks}")

        # Convert ticks to Python datetime in UTC
        unix_ns = ticks + DateTime._EPOCH_DIFF_NS
        unix_sec = unix_ns // 1000000000
        ns_remainder = unix_ns % 1000000000

        # Get UTC datetime
        dt_utc = py_datetime.fromtimestamp(unix_sec, py_timezone.utc)

        # Convert to local timezone if not UTC
        if hasattr(tz, '_tz') and tz._tz is not None:
            dt_local = dt_utc.astimezone(tz._tz)
        else:
            dt_local = dt_utc

        # Create DateTime but preserve exact ticks to avoid precision loss
        result = DateTime.__new__(DateTime)
        # Initialize _hash since we bypass __init__
        from .Obj import Obj
        Obj._hash_counter += 1
        result._hash = Obj._hash_counter
        result._year = dt_local.year
        result._month = Month._get(dt_local.month - 1)
        result._day = dt_local.day
        result._hour = dt_local.hour
        result._min = dt_local.minute
        result._sec = dt_local.second
        result._ns = ns_remainder
        result._tz = tz
        result._ticks = ticks  # Store exact ticks, don't recompute
        return result

    @staticmethod
    def from_str(s, checked=True, tz=None):
        """Parse a DateTime from Fantom string format: YYYY-MM-DDTHH:MM:SS[.nnnnnnnnn][+/-HH:MM|Z] TimeZoneName

        Note: Fantom format REQUIRES a timezone name at the end (e.g., "2008-11-14T12:00:00Z UTC").
        ISO format (without timezone name) should use fromIso() instead.
        """
        try:
            from .TimeZone import TimeZone
            s = s.strip()

            # Fantom format REQUIRES a timezone name at end (e.g., "2008-11-14T12:00:00Z UTC")
            # ISO format (no timezone name) is NOT valid for fromStr - use fromIso instead
            parts = s.rsplit(' ', 1)
            if len(parts) != 2:
                raise ValueError("Fantom DateTime format requires timezone name")

            datetime_part = parts[0]
            tz_name = parts[1]
            tz = TimeZone.from_str(tz_name)

            # Parse datetime part
            # Format: YYYY-MM-DDTHH:MM:SS[.nnnnnnnnn][+/-HH:MM|Z]
            if 'T' not in datetime_part:
                raise ValueError("Missing T separator")

            date_part, time_part = datetime_part.split('T')
            year, month, day = date_part.split('-')
            year = int(year)
            month = int(month)
            day = int(day)

            # Handle timezone offset in time part
            offset_secs = None  # Known offset in seconds (positive = east of UTC)
            if time_part.endswith('Z'):
                time_part = time_part[:-1]
                offset_secs = 0
                if tz is None:
                    tz = TimeZone.utc()
            elif '+' in time_part[6:]:
                idx = time_part.rfind('+')
                offset_str = time_part[idx+1:]
                time_part = time_part[:idx]
                # Parse +HH:MM (with colon) or +HHMM (4 digits without colon)
                # Fantom requires proper format - reject +HH without minutes
                if ':' in offset_str:
                    oh, om = offset_str.split(':')
                elif len(offset_str) == 4:
                    oh, om = offset_str[:2], offset_str[2:]
                else:
                    raise ValueError(f"Invalid timezone offset: +{offset_str}")
                offset_secs = int(oh) * 3600 + int(om) * 60
            elif time_part.count('-') > 0 and len(time_part) > 8:
                idx = time_part.rfind('-')
                offset_str = time_part[idx+1:]
                time_part = time_part[:idx]
                # Parse -HH:MM (with colon) or -HHMM (4 digits without colon)
                # Fantom requires proper format - reject -HH without minutes
                if ':' in offset_str:
                    oh, om = offset_str.split(':')
                elif len(offset_str) == 4:
                    oh, om = offset_str[:2], offset_str[2:]
                else:
                    raise ValueError(f"Invalid timezone offset: -{offset_str}")
                offset_secs = -(int(oh) * 3600 + int(om) * 60)

            # Parse time
            if '.' in time_part:
                time_main, frac = time_part.split('.')
            else:
                time_main = time_part
                frac = "0"

            time_parts = time_main.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            sec = int(time_parts[2]) if len(time_parts) > 2 else 0

            # Parse fractional seconds to nanoseconds
            frac = frac.ljust(9, '0')[:9]
            ns = int(frac)

            if tz is None:
                tz = TimeZone.cur()

            # Validate date/time ranges
            month_obj = Month._get(month - 1)
            if month < 1 or month > 12:
                raise ValueError(f"Invalid month: {month}")
            if day < 1 or day > month_obj.num_days(year):
                raise ValueError(f"Invalid day: {day}")
            if hour < 0 or hour > 23:
                raise ValueError(f"Invalid hour: {hour}")
            if minute < 0 or minute > 59:
                raise ValueError(f"Invalid minute: {minute}")
            if sec < 0 or sec > 59:
                raise ValueError(f"Invalid second: {sec}")

            # If we have a known offset, use it to compute ticks correctly
            # This is crucial for DST disambiguation
            if offset_secs is not None:
                return DateTime._make_with_offset(year, month, day, hour, minute, sec, ns, offset_secs, tz)

            return DateTime(year, month_obj, day, hour, minute, sec, ns, tz)
        except Exception as e:
            if checked:
                from .Err import ParseErr
                raise ParseErr.make(f"Invalid DateTime: {s}")
            return None

    def ticks(self):
        """Nanoseconds since Fantom epoch (2000-01-01 00:00:00 UTC)"""
        return self._ticks

    def year(self): return self._year
    def month(self): return self._month
    def day(self): return self._day
    def hour(self): return self._hour
    def min_(self): return self._min
    def sec(self): return self._sec
    def nano_sec(self): return self._ns
    def tz(self): return self._tz

    def dst(self):
        """Return true if this datetime is in daylight saving time.

        During DST fall-back transitions (when clocks go back), the same wall-clock
        time occurs twice. We use the stored ticks to disambiguate which instance
        we're in - if the ticks correspond to DST offset, we're in DST; if they
        correspond to standard offset, we're in standard time.
        """
        try:
            rule = self._tz._get_rule(self._year) if hasattr(self._tz, '_get_rule') else None
            if rule is not None and rule.dstOffset != 0:
                # Calculate what ticks would be for this wall-clock time in DST vs standard
                month_ord = self._month.ordinal() if hasattr(self._month, 'ordinal') else self._month - 1

                # Ticks assuming standard time offset
                ticks_std = DateTime._compute_ticks(
                    self._year, month_ord, self._day, self._hour, self._min, self._sec, self._ns,
                    rule.offset)

                # Ticks assuming DST offset
                ticks_dst = DateTime._compute_ticks(
                    self._year, month_ord, self._day, self._hour, self._min, self._sec, self._ns,
                    rule.offset + rule.dstOffset)

                # Check which one matches our actual ticks
                # This handles DST fall-back ambiguity correctly
                if self._ticks == ticks_dst:
                    return True
                if self._ticks == ticks_std:
                    return False

                # If neither exact match (shouldn't happen), fall back to rule-based calculation
                from .TimeZone import _dst_offset
                time_in_secs = self._hour * 3600 + self._min * 60 + self._sec
                dst_offset = _dst_offset(rule, self._year, month_ord, self._day, time_in_secs)
                return dst_offset != 0

            # Fall back to Python datetime for timezones without rules
            unix_ns = self._ticks + DateTime._EPOCH_DIFF_NS
            unix_sec = unix_ns // 1000000000
            dt_utc = py_datetime.fromtimestamp(unix_sec, py_timezone.utc)
            if hasattr(self._tz, '_tz') and self._tz._tz is not None:
                dt_local = dt_utc.astimezone(self._tz._tz)
                dst = dt_local.dst()
                return dst is not None and dst.total_seconds() != 0
            return False
        except Exception:
            return False

    def tz_abbr(self):
        """Return the timezone abbreviation for this datetime"""
        if self.dst():
            return self._tz.dst_abbr(self._year)
        return self._tz.std_abbr(self._year)

    def weekday(self):
        """Get the day of the week"""
        from .Weekday import Weekday
        month_num = self._month.ordinal() + 1 if hasattr(self._month, 'ordinal') else self._month
        dt = py_datetime(self._year, month_num, self._day)
        # Python: Monday=0, Fantom: Sunday=0
        py_weekday = dt.weekday()
        fantom_weekday = (py_weekday + 1) % 7
        return Weekday._get(fantom_weekday)

    def date(self):
        """Get just the date portion"""
        return Date(self._year, self._month, self._day)

    def time(self):
        """Get just the time portion"""
        return Time(self._hour, self._min, self._sec, self._ns)

    def to_str(self):
        """Format as Fantom string: YYYY-MM-DD'T'hh:mm:ss.FFFFFFFFFz zzzz
        For Rel timezone, timezone info is omitted."""
        from .TimeZone import TimeZone
        if self._tz == TimeZone.rel():
            return self.to_locale("YYYY-MM-DD'T'hh:mm:ss.FFFFFFFFF")
        return self.to_locale("YYYY-MM-DD'T'hh:mm:ss.FFFFFFFFFz zzzz")

    def __str__(self):
        return self.to_str()

    def equals(self, other):
        """Fantom equality - called by ObjUtil.equals"""
        if not isinstance(other, DateTime):
            return False
        return self._ticks == other._ticks

    def compare(self, that):
        """Fantom compare - returns -1, 0, or 1"""
        if not isinstance(that, DateTime):
            return 1 if that is None else -1
        if self._ticks < that._ticks:
            return -1
        if self._ticks > that._ticks:
            return 1
        return 0

    def __eq__(self, other):
        if not isinstance(other, DateTime):
            return False
        return self._ticks == other._ticks

    def __hash__(self):
        return hash(self._ticks)

    def __lt__(self, other):
        return self._ticks < other._ticks

    def __le__(self, other):
        return self._ticks <= other._ticks

    def __gt__(self, other):
        return self._ticks > other._ticks

    def __ge__(self, other):
        return self._ticks >= other._ticks

    # Arithmetic operators
    def plus(self, duration):
        """Add a duration to this DateTime"""
        d = duration.ticks()
        if d == 0:
            return self
        return DateTime.make_ticks(self._ticks + d, self._tz)

    def minus(self, duration):
        """Subtract a duration from this DateTime"""
        d = duration.ticks()
        if d == 0:
            return self
        return DateTime.make_ticks(self._ticks - d, self._tz)

    def minus_date_time(self, time):
        """Return the delta between this and the given time as a Duration"""
        from .Duration import Duration
        return Duration.make(self._ticks - time._ticks)

    def __add__(self, other):
        """Python + operator: DateTime + Duration -> DateTime"""
        return self.plus(other)

    def __sub__(self, other):
        """Python - operator: DateTime - Duration -> DateTime, or DateTime - DateTime -> Duration"""
        if isinstance(other, DateTime):
            return self.minus_date_time(other)
        else:
            return self.minus(other)

    def hash_(self):
        """Fantom hash - return ticks as hash"""
        return self._ticks

    def midnight(self):
        """Get midnight for this date in same timezone"""
        if self._hour == 0 and self._min == 0 and self._sec == 0 and self._ns == 0:
            return self
        return DateTime(self._year, self._month, self._day, 0, 0, 0, 0, self._tz)

    def is_midnight(self):
        """Return true if time is midnight"""
        return self._hour == 0 and self._min == 0 and self._sec == 0 and self._ns == 0

    def floor(self, accuracy):
        """Floor to given accuracy duration"""
        ticks = accuracy.ticks()
        if ticks == 0:
            return self
        floored_ticks = (self._ticks // ticks) * ticks
        if floored_ticks == self._ticks:
            return self
        return DateTime.make_ticks(floored_ticks, self._tz)

    def to_time_zone(self, tz):
        """Convert to different timezone"""
        if self._tz == tz:
            return self
        from .TimeZone import TimeZone
        # Special handling for Rel timezone - preserve wall-clock time
        if tz == TimeZone.rel() or self._tz == TimeZone.rel():
            return DateTime(self._year, self._month, self._day,
                          self._hour, self._min, self._sec, self._ns, tz)
        # Normal timezone conversion - preserve UTC instant
        return DateTime.make_ticks(self._ticks, tz)

    def to_utc(self):
        """Convert to UTC timezone"""
        from .TimeZone import TimeZone
        return self.to_time_zone(TimeZone.utc())

    def to_rel(self):
        """Convert to Rel timezone (relative timezone)"""
        from .TimeZone import TimeZone
        return self.to_time_zone(TimeZone.rel())

    def day_of_year(self):
        """Get day of year (1-366)"""
        return self.date().day_of_year()

    def week_of_year(self, startOfWeek=None):
        """Get week of year"""
        return self.date().week_of_year(startOfWeek)

    def hours_in_day(self):
        """Get hours in day (usually 24, but 23 or 25 for DST transitions)"""
        from datetime import timedelta
        try:
            # Get the timezone's Python zoneinfo object
            if not hasattr(self._tz, '_tz') or self._tz._tz is None:
                return 24

            tz = self._tz._tz
            month_num = self._month.ordinal() + 1

            # Start of this day
            start = py_datetime(self._year, month_num, self._day, 0, 0, 0, tzinfo=tz)
            # Start of next day
            next_day = start + timedelta(days=1)

            # Convert both to UTC to get actual time difference
            start_utc = start.astimezone(py_timezone.utc)
            next_utc = next_day.astimezone(py_timezone.utc)

            diff_seconds = (next_utc - start_utc).total_seconds()
            hours = int(diff_seconds / 3600)

            return hours
        except Exception:
            return 24

    @staticmethod
    def boot():
        """Get boot time (when process started).

        Note: _boot is initialized at class definition time (see end of file)
        to ensure it captures the actual module load time, not the first call time.
        This matches JS behavior where staticInit.js sets DateTime.__boot = DateTime.now()
        """
        return DateTime._boot

    @staticmethod
    def now_ticks():
        """Get current ticks"""
        return DateTime.now()._ticks

    # Lock for nowUnique thread safety
    _nowUniqueLock = None

    @staticmethod
    def now_unique():
        """Get unique ticks that is always increasing (thread-safe)"""
        import threading
        if DateTime._nowUniqueLock is None:
            DateTime._nowUniqueLock = threading.Lock()
        if not hasattr(DateTime, '_lastUnique'):
            DateTime._lastUnique = 0

        with DateTime._nowUniqueLock:
            ticks = DateTime._now_ticks_raw()
            if ticks <= DateTime._lastUnique:
                ticks = DateTime._lastUnique + 1
            DateTime._lastUnique = ticks
            return ticks

    @staticmethod
    def is_leap_year(year):
        """Check if year is a leap year"""
        if (year & 3) != 0:
            return False
        return (year % 100 != 0) or (year % 400 == 0)

    @staticmethod
    def weekday_in_month(year, month, weekday, pos):
        """Get the day of month for nth weekday"""
        if pos == 0:
            from .Err import ArgErr
            raise ArgErr.make("Position cannot be 0")

        # Get the first day of the month
        first = Date(year, month, 1)
        first_weekday = first.weekday().ordinal()
        target_weekday = weekday.ordinal()

        # Calculate days to first occurrence of target weekday
        days_to_first = (target_weekday - first_weekday) % 7
        first_occurrence = 1 + days_to_first

        num_days = month.num_days(year)

        if pos > 0:
            day = first_occurrence + (pos - 1) * 7
            if day > num_days:
                from .Err import ArgErr
                raise ArgErr.make(f"Invalid weekday position: {pos}")
        else:
            # Count from end of month
            last_occurrence = first_occurrence
            while last_occurrence + 7 <= num_days:
                last_occurrence += 7
            day = last_occurrence + (pos + 1) * 7
            if day < 1:
                from .Err import ArgErr
                raise ArgErr.make(f"Invalid weekday position: {pos}")

        return day

    @staticmethod
    def _invalid_num_pattern(c, count):
        """Check if pattern count is invalid and raise ArgErr"""
        from .Err import ArgErr
        raise ArgErr.make(f"Invalid pattern: {c * count}")

    def to_locale(self, pattern=None, locale=None):
        """Format DateTime using locale pattern"""
        from .Locale import Locale
        if locale is None:
            locale = Locale.cur()
        if pattern is None:
            # Use locale-specific default pattern
            # US locale uses 12-hour time with AM/PM
            if locale.country() == "US":
                pattern = "D-MMM-YYYY WWW k:mm:ssAA zzz"
            else:
                # Non-US locales use 24-hour time
                pattern = "D-MMM-YYYY WWW hh:mm:ss zzz"

        # Weekday names (TODO: make locale-aware)
        weekday_full = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        weekday_abbr = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

        result = []
        i = 0
        while i < len(pattern):
            c = pattern[i]
            # Count consecutive same chars
            count = 1
            while i + count < len(pattern) and pattern[i + count] == c:
                count += 1

            if c == 'Y':  # Year - valid: YY, YYYY
                if count == 1 or count == 3 or count > 4:
                    DateTime._invalid_num_pattern(c, count)
                if count >= 4:
                    result.append(f"{self._year:04d}")
                elif count == 2:
                    result.append(f"{self._year % 100:02d}")
            elif c == 'M':  # Month - valid: M, MM, MMM, MMMM
                if count > 4:
                    DateTime._invalid_num_pattern(c, count)
                if count >= 4:
                    # Use locale-aware month name via Month native
                    from .Month import Month as MonthNative
                    m = MonthNative.vals().get(self._month.ordinal())
                    result.append(m._Month__full(locale))
                elif count == 3:
                    # Use locale-aware month abbreviation via Month native
                    from .Month import Month as MonthNative
                    m = MonthNative.vals().get(self._month.ordinal())
                    result.append(m._Month__abbr(locale))
                elif count == 2:
                    result.append(f"{self._month.ordinal() + 1:02d}")
                else:
                    result.append(str(self._month.ordinal() + 1))
            elif c == 'D':  # Day of month - valid: D, DD, DDD
                if count > 3:
                    DateTime._invalid_num_pattern(c, count)
                if count >= 3:
                    result.append(Date._ordinal(self._day))
                elif count == 2:
                    result.append(f"{self._day:02d}")
                else:
                    result.append(str(self._day))
            elif c == 'W':  # Weekday - valid: WWW, WWWW
                if count < 3 or count > 4:
                    DateTime._invalid_num_pattern(c, count)
                wd = self.weekday().ordinal()
                if count >= 4:
                    result.append(weekday_full[wd])
                else:
                    result.append(weekday_abbr[wd])
            elif c == 'h':  # Hour (24-hour, 0-23) - valid: h, hh
                if count > 2:
                    DateTime._invalid_num_pattern(c, count)
                if count >= 2:
                    result.append(f"{self._hour:02d}")
                else:
                    result.append(str(self._hour))
            elif c == 'k':  # Hour (12-hour, 1-12) - valid: k, kk
                if count > 2:
                    DateTime._invalid_num_pattern(c, count)
                h = self._hour % 12
                if h == 0:
                    h = 12
                if count >= 2:
                    result.append(f"{h:02d}")
                else:
                    result.append(str(h))
            elif c == 'm':  # Minute - valid: m, mm
                if count > 2:
                    DateTime._invalid_num_pattern(c, count)
                if count >= 2:
                    result.append(f"{self._min:02d}")
                else:
                    result.append(str(self._min))
            elif c == 's':  # Second - valid: s, ss
                if count > 2:
                    DateTime._invalid_num_pattern(c, count)
                if count >= 2:
                    result.append(f"{self._sec:02d}")
                else:
                    result.append(str(self._sec))
            elif c == 'S':  # Optional seconds (omit if 0)
                if self._sec != 0 or self._ns != 0:
                    result.append(f"{self._sec:02d}" if count >= 2 else str(self._sec))
            elif c == 'f' or c == 'F':  # Fractional seconds
                # f = required digits, F = optional (trimmed) digits
                # Count consecutive f and F chars from current position
                req = 0  # required digits
                opt = 0  # optional digits
                if c == 'F':
                    opt = count
                else:
                    req = count
                    # Look ahead for F's
                    while i + count < len(pattern) and pattern[i + count] == 'F':
                        opt += 1
                        count += 1
                # Output fractional digits
                frac = self._ns
                tenth = 100000000  # 10^8
                frac_str = ""
                for x in range(9):
                    if req > 0:
                        req -= 1
                    else:
                        if frac == 0 or opt <= 0:
                            break
                        opt -= 1
                    frac_str += str(frac // tenth)
                    frac %= tenth
                    tenth //= 10
                result.append(frac_str)
            elif c == 'a':  # Lowercase am/pm - valid: a, aa
                if count > 2:
                    DateTime._invalid_num_pattern(c, count)
                if count == 1:
                    result.append("a" if self._hour < 12 else "p")
                else:
                    result.append("am" if self._hour < 12 else "pm")
            elif c == 'A':  # Uppercase AM/PM - valid: A, AA
                if count > 2:
                    DateTime._invalid_num_pattern(c, count)
                if count == 1:
                    result.append("A" if self._hour < 12 else "P")
                else:
                    result.append("AM" if self._hour < 12 else "PM")
            elif c == 'z':  # Timezone
                if count == 1:
                    # z = UTC offset like +01:00 or Z
                    # Use rule-based offset when available (matches Fantom/JS exactly)
                    offset_secs = 0
                    rule = self._tz._get_rule(self._year) if hasattr(self._tz, '_get_rule') else None
                    if rule is not None:
                        offset_secs = rule.offset
                        if self.dst():
                            offset_secs += rule.dstOffset
                    else:
                        # Fall back to Python-based offset
                        offset_dur = self._tz.offset(self._year)
                        offset_secs = offset_dur.to_sec() if hasattr(offset_dur, 'to_sec') else offset_dur
                        if self.dst():
                            dst_off = self._tz.dst_offset(self._year)
                            if dst_off:
                                dst_secs = dst_off.to_sec() if hasattr(dst_off, 'to_sec') else dst_off
                                offset_secs = offset_secs + dst_secs
                    if offset_secs == 0:
                        result.append("Z")
                    else:
                        sign = '+' if offset_secs >= 0 else '-'
                        offset_secs = abs(offset_secs)
                        hrs = offset_secs // 3600
                        mins = (offset_secs % 3600) // 60
                        result.append(f"{sign}{hrs:02d}:{mins:02d}")
                elif count == 3:
                    # zzz = abbreviation (e.g., EST, EDT) - use actual DST state
                    result.append(self.tz_abbr())
                else:
                    # zzzz = full name
                    result.append(self._tz.name())
            elif c == 'Q':  # Quarter
                quarter = (self._month.ordinal() // 3) + 1
                if count >= 4:
                    result.append(f"{Date._ordinal(quarter)} Quarter")
                elif count >= 3:
                    result.append(Date._ordinal(quarter))
                else:
                    result.append(str(quarter))
            elif c == 'V':  # Week of year
                woy = self.week_of_year()
                if count >= 3:
                    result.append(Date._ordinal(woy))
                elif count == 2:
                    result.append(f"{woy:02d}")
                else:
                    result.append(str(woy))
            elif c == "'":  # Quoted literal - '' means literal quote
                num_literals = 0
                i += 1
                while i < len(pattern) and pattern[i] != "'":
                    result.append(pattern[i])
                    num_literals += 1
                    i += 1
                if num_literals == 0:
                    result.append("'")
                count = 1  # Reset count since we handled quote specially
            else:
                # Handle symbol skip before optional patterns
                skip = False
                if i + 1 < len(pattern):
                    next_c = pattern[i + 1]
                    # Skip symbol before .FFFFFFFFF if ns=0
                    if next_c == 'F' and self._ns == 0:
                        skip = True
                    # Skip symbol before :SS if sec and ns are 0
                    elif next_c == 'S' and self._sec == 0 and self._ns == 0:
                        skip = True
                if not skip:
                    result.append(c)

            i += count

        return "".join(result)

    @staticmethod
    def from_locale(s, pattern, tz=None, checked=True):
        """Parse DateTime from locale pattern string"""
        from .TimeZone import TimeZone
        try:
            if tz is None:
                tz = TimeZone.cur()

            month_full = ["january", "february", "march", "april", "may", "june",
                          "july", "august", "september", "october", "november", "december"]
            month_abbr = ["jan", "feb", "mar", "apr", "may", "jun",
                          "jul", "aug", "sep", "oct", "nov", "dec"]

            year = 0
            mon = 0
            day = 0
            hour = 0
            min_ = 0
            sec = 0
            ns = 0
            tz_offset = None
            tz_name = None

            pos = 0
            i = 0
            pattern_len = len(pattern)
            skipped_last = False

            while i < pattern_len:
                c = pattern[i]
                count = 1
                while i + count < pattern_len and pattern[i + count] == c:
                    count += 1

                if c == 'Y':
                    year = DateTime._parse_int(s, pos, count)
                    pos += len(str(year)) if count == 1 else count
                    if year < 30:
                        year += 2000
                    elif year < 100:
                        year += 1900
                elif c == 'M':
                    if count >= 3:
                        mon, pos = DateTime._parse_month(s, pos, month_abbr, month_full)
                    else:
                        mon = DateTime._parse_int(s, pos, count)
                        pos += len(str(mon)) if count == 1 else count
                elif c == 'D':
                    if count == 3:
                        # Day with suffix (1st, 2nd, etc.)
                        day = DateTime._parse_int(s, pos, 1)
                        pos += len(str(day))
                        # Skip suffix
                        while pos < len(s) and s[pos].isalpha():
                            pos += 1
                    else:
                        day = DateTime._parse_int(s, pos, count)
                        pos += len(str(day)) if count == 1 else count
                elif c == 'W':
                    # Skip weekday
                    while pos < len(s) and s[pos].isalpha():
                        pos += 1
                elif c == 'h' or c == 'k':
                    hour = DateTime._parse_int(s, pos, count)
                    pos += len(str(hour)) if count == 1 else count
                elif c == 'm':
                    min_ = DateTime._parse_int(s, pos, count)
                    pos += len(str(min_)) if count == 1 else count
                elif c == 's':
                    sec = DateTime._parse_int(s, pos, count)
                    pos += len(str(sec)) if count == 1 else count
                elif c == 'S':
                    # Optional seconds
                    if not skipped_last and pos < len(s) and s[pos].isdigit():
                        sec = DateTime._parse_int(s, pos, count)
                        pos += len(str(sec)) if count == 1 else count
                elif c == 'a' or c == 'A':
                    if pos < len(s):
                        am_pm = s[pos].lower()
                        pos += count
                        if am_pm == 'p':
                            if hour < 12:
                                hour += 12
                        else:
                            if hour == 12:
                                hour = 0
                elif c == 'f' or c == 'F':
                    # Fractional seconds
                    if skipped_last:
                        pass  # Skip
                    else:
                        ns = 0
                        tenth = 100000000
                        while pos < len(s) and s[pos].isdigit():
                            ns += (ord(s[pos]) - 48) * tenth
                            tenth //= 10
                            pos += 1
                elif c == 'z':
                    # Timezone
                    if count == 1:
                        # Parse offset like +05:00, -05:00, Z
                        tz_offset, pos = DateTime._parse_tz_offset(s, pos)
                    else:
                        # Parse timezone name
                        tz_name, pos = DateTime._parse_tz_name(s, pos)
                elif c == "'":
                    # Quoted literal
                    if count == 2:
                        # Escaped quote
                        if pos < len(s) and s[pos] == "'":
                            pos += 1
                        i += 1
                        continue
                    else:
                        i += 1
                        while i < pattern_len and pattern[i] != "'":
                            if pos < len(s) and s[pos] == pattern[i]:
                                pos += 1
                            i += 1
                        count = 1
                else:
                    # Literal character - handle optional skipping for S and F
                    if i + 1 < pattern_len:
                        next_c = pattern[i + 1]
                        if next_c in ('F', 'S'):
                            if pos >= len(s) or s[pos] != c:
                                skipped_last = True
                                i += count
                                continue
                    skipped_last = False
                    if pos < len(s) and s[pos] == c:
                        pos += 1

                i += count

            # Resolve timezone
            result_tz = tz
            if tz_name is not None:
                def_rule_std = tz.std_abbr(year) if hasattr(tz, 'std_abbr') else None
                def_rule_dst = tz.dst_abbr(year) if hasattr(tz, 'dst_abbr') else None
                if tz_name == tz.name() or tz_name == def_rule_std or tz_name == def_rule_dst:
                    result_tz = tz
                else:
                    try:
                        result_tz = TimeZone.from_str(tz_name)
                    except:
                        result_tz = tz
            elif tz_offset is not None:
                # Figure out what the expected offset is for defTz at this specific date/time
                # This matches the JavaScript implementation which calculates actual offset
                def_offset = tz.offset(year)
                def_offset_secs = def_offset.to_sec() if hasattr(def_offset, 'to_sec') else def_offset

                # Calculate actual offset by checking if DST is in effect for this date
                actual_offset = def_offset_secs
                try:
                    # Use Python's datetime to determine if DST would be in effect
                    if hasattr(tz, '_tz') and tz._tz is not None:
                        dt = py_datetime(year, mon, day, hour, min_, sec, tzinfo=tz._tz)
                        dst = dt.dst()
                        if dst is not None and dst.total_seconds() != 0:
                            actual_offset += int(dst.total_seconds())
                except Exception:
                    pass

                # If specified offset matches expected offset for defTz, use defTz
                # Otherwise use a vanilla GMT+/- timezone
                if tz_offset == actual_offset:
                    result_tz = tz
                else:
                    result_tz = TimeZone._from_gmt_offset(tz_offset)

            # If we have a known offset, use it for exact ticks calculation
            # This is crucial for half-hour offsets like -03:30
            if tz_offset is not None:
                return DateTime._make_with_offset(year, mon, day, hour, min_, sec, ns, tz_offset, result_tz)
            return DateTime(year, Month._get(mon - 1), day, hour, min_, sec, ns, result_tz)
        except Exception as e:
            if checked:
                from .Err import ParseErr
                raise ParseErr.make(f"DateTime: {s}")
            return None

    @staticmethod
    def _parse_int(s, pos, n):
        """Parse n digits from string at position.

        For n=1, allows parsing 1 or 2 digits (flexible).
        For n>1, requires exactly n digits (strict).
        """
        num = 0
        count = 0
        while pos + count < len(s) and s[pos + count].isdigit():
            num = num * 10 + (ord(s[pos + count]) - 48)
            count += 1
            if count >= n and n > 1:
                break
        # For n=1, allow parsing one or two digits
        if n == 1 and count > 0 and pos + count < len(s) and s[pos + count].isdigit():
            num = num * 10 + (ord(s[pos + count]) - 48)
            count += 1
        # Raise error if no digits found
        if count == 0:
            raise ValueError(f"Expected digits at position {pos}")
        # For n>1, require exactly n digits
        if n > 1 and count < n:
            raise ValueError(f"Expected {n} digits at position {pos}, got {count}")
        return num

    @staticmethod
    def _parse_month(s, pos, abbr_list, full_list, locale=None):
        """Parse month name from string, return (month_num, new_pos).
        Uses locale-aware month names via Locale.__monthByName when available."""
        word = ""
        while pos < len(s) and s[pos].isalpha():
            word += s[pos]
            pos += 1
        word_lower = word.lower()

        # Try locale-aware month lookup first
        if locale is not None:
            m = locale._Locale__month_by_name(word_lower)
            if m is not None:
                return m.ordinal() + 1, pos

        # Fall back to English month names
        for i, name in enumerate(abbr_list):
            if word_lower == name or word_lower == full_list[i]:
                return i + 1, pos
        raise ValueError(f"Invalid month: {word}")

    @staticmethod
    def _parse_tz_offset(s, pos):
        """Parse timezone offset like +05:00, -05:00, Z, +0500"""
        if pos >= len(s):
            return None, pos
        c = s[pos]
        if c == 'Z':
            return 0, pos + 1
        elif c == '+' or c == '-':
            neg = (c == '-')
            pos += 1
            hr = 0
            hr_digits = 0
            while pos < len(s) and s[pos].isdigit() and hr_digits < 2:
                hr = hr * 10 + (ord(s[pos]) - 48)
                pos += 1
                hr_digits += 1
            min_ = 0
            if pos < len(s) and s[pos] == ':':
                pos += 1
            min_digits = 0
            while pos < len(s) and s[pos].isdigit() and min_digits < 2:
                min_ = min_ * 10 + (ord(s[pos]) - 48)
                pos += 1
                min_digits += 1
            offset = hr * 3600 + min_ * 60
            if neg:
                offset = -offset
            return offset, pos
        return None, pos

    @staticmethod
    def _parse_tz_name(s, pos):
        """Parse timezone name from string"""
        name = ""
        while pos < len(s) and (s[pos].isalnum() or s[pos] in '+_-'):
            name += s[pos]
            pos += 1
        return name, pos

    def to_code(self):
        """Return Fantom code representation"""
        if self.equals(DateTime.def_val()):
            return "DateTime.defVal"
        return f'DateTime("{self.to_str()}")'

    @staticmethod
    def from_iso(s, checked=True):
        """Parse ISO 8601 format: YYYY-MM-DDTHH:MM:SS.FFFZ or YYYY-MM-DDTHH:MM:SS.FFF+HH:MM
        ISO format does NOT include a timezone name at the end (that's Fantom format)."""
        from .TimeZone import TimeZone
        try:
            orig = s
            s = s.strip()

            # ISO format should not have a space (timezone name comes after space in Fantom format)
            if ' ' in s:
                raise ValueError("ISO format cannot have timezone name")

            # Parse the datetime components
            # Format: YYYY-MM-DDThh:mm:ss[.FFFFFFFFF][Z|+hh:mm|-hh:mm]
            if 'T' not in s:
                raise ValueError("Missing T separator")

            date_part, time_part = s.split('T', 1)

            # Parse date
            date_parts = date_part.split('-')
            if len(date_parts) != 3:
                raise ValueError("Invalid date format")
            year = int(date_parts[0])
            month = int(date_parts[1])
            day = int(date_parts[2])

            # Parse timezone offset from end of time part
            offset_secs = 0
            if time_part.endswith('Z'):
                time_part = time_part[:-1]
                offset_secs = 0
            else:
                # Look for + or - offset
                for i in range(len(time_part) - 1, 5, -1):
                    if time_part[i] in '+-':
                        offset_str = time_part[i:]
                        time_part = time_part[:i]
                        # Parse offset
                        sign = 1 if offset_str[0] == '+' else -1
                        offset_str = offset_str[1:]
                        if ':' in offset_str:
                            hrs, mins = offset_str.split(':')
                        elif len(offset_str) == 4:
                            hrs = offset_str[:2]
                            mins = offset_str[2:]
                        elif len(offset_str) <= 2:
                            hrs = offset_str
                            mins = "0"
                        else:
                            raise ValueError(f"Invalid offset: {offset_str}")
                        offset_secs = sign * (int(hrs) * 3600 + int(mins) * 60)
                        break

            # Parse time
            if '.' in time_part:
                time_main, frac = time_part.split('.')
            else:
                time_main = time_part
                frac = "0"

            time_parts = time_main.split(':')
            if len(time_parts) < 2:
                raise ValueError("Invalid time format")
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            sec = int(time_parts[2]) if len(time_parts) > 2 else 0

            # Parse fractional seconds to nanoseconds
            frac = frac.ljust(9, '0')[:9]
            ns = int(frac)

            # Create timezone from GMT offset
            tz = TimeZone._from_gmt_offset(offset_secs)

            return DateTime(year, Month._get(month - 1), day, hour, minute, sec, ns, tz)
        except Exception as e:
            if checked:
                from .Err import ParseErr
                raise ParseErr.make(f"Invalid ISO DateTime: {orig}")
            return None

    def to_iso(self):
        """Format as ISO 8601 string"""
        month_num = self._month.ordinal() + 1
        base = f"{self._year}-{month_num:02d}-{self._day:02d}T{self._hour:02d}:{self._min:02d}:{self._sec:02d}"
        if self._ns != 0:
            # Add fractional seconds, trimming trailing zeros
            frac = f"{self._ns:09d}".rstrip('0')
            base = f"{base}.{frac}"
        # Add timezone offset
        offset_dur = self._tz.offset(self._year)
        offset_secs = offset_dur.to_sec() if hasattr(offset_dur, 'to_sec') else offset_dur
        if offset_secs == 0:
            base = f"{base}Z"
        else:
            sign = '+' if offset_secs >= 0 else '-'
            offset_secs = abs(offset_secs)
            hrs = offset_secs // 3600
            mins = (offset_secs % 3600) // 60
            base = f"{base}{sign}{hrs:02d}:{mins:02d}"
        return base

    @staticmethod
    def from_java(millis, tz=None, negIsNull=True):
        """Create DateTime from Java milliseconds since Unix epoch (1970-01-01)"""
        from .TimeZone import TimeZone
        if tz is None:
            tz = TimeZone.cur()

        # Check for null/invalid values
        if millis <= 0:
            if negIsNull or millis == 0:
                return None
            # Otherwise, handle negative millis (dates before 1970)

        # Convert Java millis to Fantom ticks (nanoseconds since 2000-01-01)
        # Java epoch: 1970-01-01, Fantom epoch: 2000-01-01
        # Difference: 30 years (10957 days)
        java_epoch_diff_ms = 946684800000  # milliseconds from 1970 to 2000
        fantom_ticks = (millis - java_epoch_diff_ms) * 1000000  # convert to nanoseconds

        return DateTime.make_ticks(fantom_ticks, tz)

    def to_java(self):
        """Convert to Java milliseconds since Unix epoch (1970-01-01)"""
        # Convert Fantom ticks (ns since 2000) to Java millis (ms since 1970)
        java_epoch_diff_ms = 946684800000  # milliseconds from 1970 to 2000
        return (self._ticks // 1000000) + java_epoch_diff_ms

    @staticmethod
    def from_posix(secs, tz=None):
        """Create DateTime from Unix/POSIX seconds since 1970-01-01 00:00:00 UTC.

        Args:
            secs: Seconds since Unix epoch (1970-01-01)
            tz: Optional timezone (defaults to current timezone)

        Returns:
            DateTime in the specified timezone
        """
        from .TimeZone import TimeZone
        if tz is None:
            tz = TimeZone.cur()

        # Convert Unix seconds to Fantom ticks (nanoseconds since 2000-01-01)
        # Unix epoch: 1970-01-01, Fantom epoch: 2000-01-01
        # Difference: 946684800 seconds
        unix_epoch_diff_secs = 946684800
        fantom_ticks = (secs - unix_epoch_diff_secs) * 1000000000  # convert to nanoseconds

        return DateTime.make_ticks(fantom_ticks, tz)

    @staticmethod
    def from_http_str(s, checked=True):
        """Parse HTTP date format (RFC 1123, RFC 850, or asctime)"""
        from .TimeZone import TimeZone
        try:
            s = s.strip()
            # Try RFC 1123: "Sun, 06 Nov 1994 08:49:37 GMT"
            # Try RFC 850: "Sunday, 06-Nov-94 08:49:37 GMT"
            # Try asctime: "Sun Nov  6 08:49:37 1994"

            weekday_abbr = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            weekday_full = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            month_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

            # RFC 850 format: "Sunday, 06-Nov-94 08:49:37 GMT" (check first - has dashes in date)
            if ', ' in s and '-' in s.split(', ')[1].split()[0]:
                parts = s.split(', ')
                rest = parts[1]  # "06-Nov-94 08:49:37 GMT"
                date_time = rest.split(' ')
                date_parts = date_time[0].split('-')
                day = int(date_parts[0])
                month = month_abbr.index(date_parts[1]) + 1
                year = int(date_parts[2])
                if year < 100:
                    year = 1900 + year if year >= 70 else 2000 + year
                time_parts = date_time[1].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                sec = int(time_parts[2])
                return DateTime(year, Month._get(month - 1), day, hour, minute, sec, 0, TimeZone.utc())

            # RFC 1123 format: "Sun, 06 Nov 1994 08:49:37 GMT"
            if ', ' in s and s.endswith('GMT'):
                parts = s.split()
                # parts: ['Sun,', '06', 'Nov', '1994', '08:49:37', 'GMT']
                day = int(parts[1])
                month = month_abbr.index(parts[2]) + 1
                year = int(parts[3])
                time_parts = parts[4].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                sec = int(time_parts[2])
                return DateTime(year, Month._get(month - 1), day, hour, minute, sec, 0, TimeZone.utc())

            # asctime format: "Sun Nov  6 08:49:37 1994"
            parts = s.split()
            # parts: ['Sun', 'Nov', '6', '08:49:37', '1994']
            if len(parts) >= 5:
                month = month_abbr.index(parts[1]) + 1
                day = int(parts[2])
                time_parts = parts[3].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                sec = int(time_parts[2])
                year = int(parts[4])
                return DateTime(year, Month._get(month - 1), day, hour, minute, sec, 0, TimeZone.utc())

            raise ValueError("Unknown HTTP date format")
        except Exception as e:
            if checked:
                from .Err import ParseErr
                raise ParseErr.make(f"Invalid HTTP DateTime: {s}")
            return None

    def to_http_str(self):
        """Format as HTTP date string (RFC 1123)"""
        weekday_abbr = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        month_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        # Convert to UTC first
        utc = self.to_utc()
        wd = utc.weekday().ordinal()
        return f"{weekday_abbr[wd]}, {utc._day:02d} {month_abbr[utc._month.ordinal()]} {utc._year} {utc._hour:02d}:{utc._min:02d}:{utc._sec:02d} GMT"

    def typeof(self):
        """Return the Fantom type of this object."""
        from fan.sys.Type import Type
        return Type.find("sys::DateTime")

    def literal_encode(self, encoder):
        """Encode for serialization.

        Simple types serialize as: Type("toStr")
        Example: sys::DateTime("2023-06-15T10:30:00-05:00 New_York")
        """
        encoder.w_type(self.typeof())
        encoder.w('(')
        encoder.w_str_literal(self.to_str(), '"')
        encoder.w(')')

    #################################################################
    # Python Interop (to_py / from_py)
    #################################################################

    def to_py(self):
        """Convert to native Python datetime.datetime.

        Returns:
            A timezone-aware datetime.datetime object.

        Example:
            >>> fantom_dt.to_py()
            datetime.datetime(2025, 1, 21, 17, 20, 0, tzinfo=...)
        """
        from datetime import datetime as py_dt, timezone as py_tz, timedelta

        # Get offset for this datetime
        offset_secs = 0
        rule = self._tz._get_rule(self._year) if hasattr(self._tz, '_get_rule') else None
        if rule is not None:
            offset_secs = rule.offset
            if self.dst():
                offset_secs += rule.dstOffset
        else:
            offset_dur = self._tz.offset(self._year)
            offset_secs = offset_dur.to_sec() if hasattr(offset_dur, 'to_sec') else offset_dur
            if self.dst():
                dst_off = self._tz.dst_offset(self._year)
                if dst_off:
                    dst_secs = dst_off.to_sec() if hasattr(dst_off, 'to_sec') else dst_off
                    offset_secs += dst_secs

        # Create timezone from offset
        tz_info = py_tz(timedelta(seconds=offset_secs))

        # Get month number (1-12)
        month_num = self._month.ordinal() + 1

        # Create datetime with microseconds (Python datetime precision limit)
        microseconds = self._ns // 1000
        return py_dt(self._year, month_num, self._day,
                    self._hour, self._min, self._sec, microseconds,
                    tzinfo=tz_info)

    @staticmethod
    def from_py(dt, tz=None):
        """Create DateTime from native Python datetime.datetime.

        Args:
            dt: Python datetime.datetime object
            tz: Optional Fantom TimeZone. If None, uses the datetime's tzinfo
                or falls back to current timezone.

        Returns:
            Fantom DateTime

        Example:
            >>> from datetime import datetime
            >>> DateTime.from_py(datetime.now())
            DateTime("2025-01-21T17:20:00-08:00 Los_Angeles")
        """
        from .TimeZone import TimeZone

        if tz is None:
            if dt.tzinfo is not None:
                # Try to get timezone name from Python tzinfo
                tz_name = getattr(dt.tzinfo, 'key', None) or getattr(dt.tzinfo, 'zone', None)
                if tz_name:
                    try:
                        tz = TimeZone.from_str(tz_name)
                    except:
                        pass
            if tz is None:
                tz = TimeZone.cur()

        # Get offset in seconds from Python datetime
        offset_secs = 0
        if dt.tzinfo is not None:
            utc_offset = dt.utcoffset()
            if utc_offset is not None:
                offset_secs = int(utc_offset.total_seconds())

        # Convert microseconds to nanoseconds
        ns = dt.microsecond * 1000

        return DateTime._make_with_offset(
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second, ns,
            offset_secs, tz
        )


class Date(Obj):
    """Date represents a day in time without time-of-day or timezone."""

    def __init__(self, year_or_str, month=None, day=None):
        super().__init__()
        # Handle string constructor: Date("2025-03-02")
        if isinstance(year_or_str, str):
            parsed = Date.from_str(year_or_str)
            self._year = parsed._year
            self._month = parsed._month
            self._day = parsed._day
        else:
            self._year = year_or_str
            self._month = month
            self._day = day

    @staticmethod
    def today(tz=None):
        from .TimeZone import TimeZone
        if tz is None:
            tz = TimeZone.cur()
        # Get current time and convert to requested timezone
        now = DateTime.now(None)  # null = fresh datetime
        if now.tz() != tz:
            now = now.to_time_zone(tz)
        return Date(now.year(), now.month(), now.day())

    def year(self): return self._year
    def month(self): return self._month
    def day(self): return self._day

    def to_str(self):
        month_num = self._month.ordinal() + 1 if hasattr(self._month, 'ordinal') else self._month
        return f"{self._year}-{month_num:02d}-{self._day:02d}"

    def __str__(self):
        return self.to_str()

    # Identity/comparison methods
    def equals(self, that):
        """Fantom equality"""
        if not isinstance(that, Date):
            return False
        return (self._year == that._year and
                self._month.ordinal() == that._month.ordinal() and
                self._day == that._day)

    def compare(self, that):
        """Fantom compare - returns -1, 0, or 1"""
        if self._year != that._year:
            return -1 if self._year < that._year else 1
        if self._month.ordinal() != that._month.ordinal():
            return -1 if self._month.ordinal() < that._month.ordinal() else 1
        if self._day != that._day:
            return -1 if self._day < that._day else 1
        return 0

    def hash_(self):
        """Fantom hash"""
        return (self._year << 16) ^ (self._month.ordinal() << 8) ^ self._day

    def __eq__(self, other):
        if not isinstance(other, Date):
            return False
        return self.equals(other)

    def __hash__(self):
        return self.hash_()

    def __lt__(self, other):
        return self.compare(other) < 0

    def __le__(self, other):
        return self.compare(other) <= 0

    def __gt__(self, other):
        return self.compare(other) > 0

    def __ge__(self, other):
        return self.compare(other) >= 0

    # Helper for date arithmetic
    @staticmethod
    def _num_days_in_month(year, month_ordinal):
        """Get number of days in a month (0-based month ordinal)"""
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if month_ordinal == 1 and Date._is_leap_year(year):
            return 29
        return days_in_month[month_ordinal]

    @staticmethod
    def _is_leap_year(year):
        """Check if year is a leap year"""
        if (year & 3) != 0:
            return False
        return (year % 100 != 0) or (year % 400 == 0)

    def _day_of_year(self):
        """Get day of year (1-366)"""
        days_before_month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
        days_before_month_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
        month_ord = self._month.ordinal()
        if Date._is_leap_year(self._year):
            return days_before_month_leap[month_ord] + self._day
        return days_before_month[month_ord] + self._day

    # Arithmetic operators
    def plus(self, duration):
        """Add duration (must be whole days) to get future date"""
        from .Duration import Duration
        ticks = duration.ticks()

        # Check even number of days
        ns_per_day = 86400 * 1000000000
        if ticks % ns_per_day != 0:
            from .Err import ArgErr
            raise ArgErr.make("Duration must be even num of days")

        num_days = ticks // ns_per_day
        if num_days == 0:
            return self

        year = self._year
        month = self._month.ordinal()
        day = self._day

        while num_days != 0:
            if num_days > 0:
                day += 1
                if day > Date._num_days_in_month(year, month):
                    day = 1
                    month += 1
                    if month >= 12:
                        month = 0
                        year += 1
                num_days -= 1
            else:
                day -= 1
                if day <= 0:
                    month -= 1
                    if month < 0:
                        month = 11
                        year -= 1
                    day = Date._num_days_in_month(year, month)
                num_days += 1

        return Date(year, Month._get(month), day)

    def minus(self, duration):
        """Subtract duration (must be whole days) to get past date"""
        from .Duration import Duration
        return self.plus(Duration.make(-duration.ticks()))

    def minus_date(self, that):
        """Return the delta between this and the given date as Duration"""
        from .Duration import Duration
        ns_per_day = 86400 * 1000000000

        # Short circuit if equal
        if self.equals(that):
            return Duration.def_val()

        # Compute so that a < b
        a = self
        b = that
        if a.compare(b) > 0:
            b = self
            a = that

        # Compute difference in days
        if a._year == b._year:
            days = b._day_of_year() - a._day_of_year()
        else:
            days = (366 if Date._is_leap_year(a._year) else 365) - a._day_of_year()
            days += b._day_of_year()
            for i in range(a._year + 1, b._year):
                days += 366 if Date._is_leap_year(i) else 365

        # Negate if necessary if a was self
        if a == self:
            days = -days

        return Duration.make(days * ns_per_day)

    def __add__(self, other):
        """Python + operator: Date + Duration -> Date"""
        return self.plus(other)

    def __sub__(self, other):
        """Python - operator: Date - Duration -> Date, or Date - Date -> Duration"""
        if isinstance(other, Date):
            return self.minus_date(other)
        else:
            return self.minus(other)

    def is_before(self, that):
        """Return true if this date is before given date"""
        return self.compare(that) < 0

    def is_after(self, that):
        """Return true if this date is after given date"""
        return self.compare(that) > 0

    def is_same_year(self, that):
        """Return true if this date is same year as given date"""
        return self._year == that._year

    def is_same_month(self, that):
        """Return true if this date is same year and month as given date"""
        return self._year == that._year and self._month.ordinal() == that._month.ordinal()

    def weekday(self):
        """Get the day of the week"""
        from .Weekday import Weekday
        month_num = self._month.ordinal() + 1
        dt = py_datetime(self._year, month_num, self._day)
        py_weekday = dt.weekday()
        fantom_weekday = (py_weekday + 1) % 7
        return Weekday._get(fantom_weekday)

    def day_of_year(self):
        """Get day of year (1-366)"""
        return self._day_of_year()

    def first_of_month(self):
        """Get first day of this month"""
        if self._day == 1:
            return self
        return Date(self._year, self._month, 1)

    def last_of_month(self):
        """Get last day of this month"""
        last_day = self._month.num_days(self._year)
        if self._day == last_day:
            return self
        return Date(self._year, self._month, last_day)

    def first_of_year(self):
        """Get Jan 1 of this year"""
        if self._month.ordinal() == 0 and self._day == 1:
            return self
        return Date(self._year, Month.jan(), 1)

    def last_of_year(self):
        """Get Dec 31 of this year"""
        if self._month.ordinal() == 11 and self._day == 31:
            return self
        return Date(self._year, Month.dec(), 31)

    def quarter(self):
        """Get quarter 1-4"""
        return (self._month.ordinal() // 3) + 1

    def first_of_quarter(self):
        """Get first day of this quarter"""
        q = self.quarter()
        first_month = Month._get((q - 1) * 3)
        result = Date(self._year, first_month, 1)
        if self.equals(result):
            return self
        return result

    def last_of_quarter(self):
        """Get last day of this quarter"""
        q = self.quarter()
        last_month = Month._get(q * 3 - 1)
        result = Date(self._year, last_month, last_month.num_days(self._year))
        if self.equals(result):
            return self
        return result

    def is_yesterday(self):
        """Return true if this date is yesterday"""
        return self.equals(Date.yesterday())

    def is_today(self):
        """Return true if this date is today"""
        return self.equals(Date.today())

    def is_tomorrow(self):
        """Return true if this date is tomorrow"""
        return self.equals(Date.tomorrow())

    @staticmethod
    def yesterday(tz=None):
        """Get yesterday's date"""
        from .Duration import Duration
        return Date.today(tz) - Duration.make(86400000000000)

    @staticmethod
    def tomorrow(tz=None):
        """Get tomorrow's date"""
        from .Duration import Duration
        return Date.today(tz) + Duration.make(86400000000000)

    def to_iso(self):
        """Format as ISO 8601 date string"""
        return self.to_str()

    @staticmethod
    def from_iso(s, checked=True):
        """Parse ISO 8601 date string"""
        return Date.from_str(s, checked)

    @staticmethod
    def from_str(s, checked=True):
        """Parse date from YYYY-MM-DD string"""
        try:
            parts = s.split('-')
            if len(parts) != 3:
                raise ValueError("Invalid date format")
            year = int(parts[0])
            month = Month._get(int(parts[1]) - 1)
            day = int(parts[2])
            return Date(year, month, day)
        except Exception:
            if checked:
                from .Err import ParseErr
                raise ParseErr.make(f"Invalid Date: {s}")
            return None

    @staticmethod
    def make(year=None, month=None, day=None):
        """Create a Date. If year is None, returns defVal."""
        if year is None:
            return Date.def_val()
        if month is None:
            month = Month.jan()
        # Handle integer month (1-12) - convert to Month object
        if isinstance(month, int):
            month = Month._get(month - 1)
        if day is None:
            day = 1
        return Date(year, month, day)

    @staticmethod
    def def_val():
        """Default value: 2000-01-01"""
        if not hasattr(Date, '_defVal') or Date._defVal is None:
            Date._defVal = Date(2000, Month.jan(), 1)
        return Date._defVal

    def to_date_time(self, time, tz=None):
        """Convert to DateTime with given time"""
        from .TimeZone import TimeZone
        if tz is None:
            tz = TimeZone.cur()
        return DateTime(self._year, self._month, self._day,
                       time.hour(), time.min_(), time.sec(), time.nano_sec(), tz)

    def midnight(self, tz=None):
        """Get DateTime at midnight for this date"""
        from .TimeZone import TimeZone
        if tz is None:
            tz = TimeZone.cur()
        return DateTime(self._year, self._month, self._day, 0, 0, 0, 0, tz)

    def week_of_year(self, startOfWeek=None):
        """Get week of year (1-53)"""
        from .Weekday import Weekday
        if startOfWeek is None:
            startOfWeek = Weekday.locale_start_of_week()
        # Get ordinals for weekday calculations
        jan1 = Date(self._year, Month.jan(), 1)
        jan1_weekday = jan1.weekday().ordinal()
        start_ord = startOfWeek.ordinal()

        # Day of year (1-based)
        doy = self.day_of_year()

        # Calculate week number based on relationship between Jan 1 and startOfWeek
        if jan1_weekday >= start_ord:
            # Jan 1 is on or after startOfWeek in the week
            # e.g., Jan 1 is Friday (5), startOfWeek is Sunday (0)
            # The partial week containing Jan 1 counts as week 1
            days_offset = jan1_weekday - start_ord
            return (doy + days_offset - 1) // 7 + 1
        else:
            # Jan 1 is before startOfWeek
            # e.g., Jan 1 is Friday (5), startOfWeek is Saturday (6)
            # Week 1 starts on the first occurrence of startOfWeek
            days_to_first_start = start_ord - jan1_weekday
            if doy <= days_to_first_start:
                return 1  # still in partial week at start
            else:
                return (doy - days_to_first_start - 1) // 7 + 1

    def to_code(self):
        """Return Fantom code representation"""
        if self.equals(Date.def_val()):
            return "Date.defVal"
        return f'Date("{self.to_str()}")'

    @staticmethod
    def _ordinal(n):
        """Get ordinal suffix for a number (1st, 2nd, 3rd, etc.)"""
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    def to_locale(self, pattern=None, locale=None):
        """Format Date using locale pattern"""
        from .Locale import Locale
        if locale is None:
            locale = Locale.cur()
        if pattern is None:
            pattern = "D-MMM-YYYY"
        weekday_full = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        weekday_abbr = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        result = []
        i = 0
        while i < len(pattern):
            c = pattern[i]
            count = 1
            while i + count < len(pattern) and pattern[i + count] == c:
                count += 1
            if c == 'Y':
                if count >= 4:
                    result.append(f"{self._year:04d}")
                elif count == 2:
                    result.append(f"{self._year % 100:02d}")
                else:
                    result.append(str(self._year))
            elif c == 'M':
                if count >= 4:
                    # Use locale-aware month name via Month native
                    from .Month import Month as MonthNative
                    m = MonthNative.vals().get(self._month.ordinal())
                    result.append(m._Month__full(locale))
                elif count == 3:
                    # Use locale-aware month abbreviation via Month native
                    from .Month import Month as MonthNative
                    m = MonthNative.vals().get(self._month.ordinal())
                    result.append(m._Month__abbr(locale))
                elif count == 2:
                    result.append(f"{self._month.ordinal() + 1:02d}")
                else:
                    result.append(str(self._month.ordinal() + 1))
            elif c == 'D':
                if count >= 3:
                    result.append(Date._ordinal(self._day))
                elif count == 2:
                    result.append(f"{self._day:02d}")
                else:
                    result.append(str(self._day))
            elif c == 'W':
                wd = self.weekday().ordinal()
                if count >= 4:
                    result.append(weekday_full[wd])
                elif count == 3:
                    result.append(weekday_abbr[wd])
                else:
                    result.append(weekday_abbr[wd][:count])
            elif c == 'V':  # Week of year
                woy = self.week_of_year()
                if count >= 3:
                    result.append(Date._ordinal(woy))
                elif count == 2:
                    result.append(f"{woy:02d}")
                else:
                    result.append(str(woy))
            elif c == 'Q':  # Quarter
                quarter = (self._month.ordinal() // 3) + 1
                if count >= 4:
                    result.append(f"{Date._ordinal(quarter)} Quarter")
                elif count >= 3:
                    result.append(Date._ordinal(quarter))
                else:
                    result.append(str(quarter))
            elif c == "'":
                # Quoted literal - '' means literal quote
                num_literals = 0
                i += 1
                while i < len(pattern) and pattern[i] != "'":
                    result.append(pattern[i])
                    num_literals += 1
                    i += 1
                if num_literals == 0:
                    result.append("'")
                count = 1
            else:
                # Check for symbol skip (don't display symbol before SS.F if sec/ns are 0)
                if i + 1 < len(pattern):
                    next_c = pattern[i + 1]
                    if next_c == 'S':
                        # Skip this symbol if there's no time object (Date doesn't have time)
                        pass  # Date doesn't have sec/ns, so don't skip
                result.append(c)
            i += count
        return "".join(result)

    @staticmethod
    def from_locale(s, pattern, checked=True):
        """Parse Date from locale pattern string"""
        from .Locale import Locale
        try:
            month_full = ["january", "february", "march", "april", "may", "june",
                          "july", "august", "september", "october", "november", "december"]
            month_abbr = ["jan", "feb", "mar", "apr", "may", "jun",
                          "jul", "aug", "sep", "oct", "nov", "dec"]
            locale = Locale.cur()

            year = 0
            mon = 0
            day = 0

            pos = 0
            i = 0
            pattern_len = len(pattern)

            while i < pattern_len:
                c = pattern[i]
                count = 1
                while i + count < pattern_len and pattern[i + count] == c:
                    count += 1

                if c == 'Y':
                    year = DateTime._parse_int(s, pos, count)
                    pos += len(str(year)) if count == 1 else count
                    if year < 30:
                        year += 2000
                    elif year < 100:
                        year += 1900
                elif c == 'M':
                    if count >= 3:
                        mon, pos = DateTime._parse_month(s, pos, month_abbr, month_full, locale)
                    else:
                        mon = DateTime._parse_int(s, pos, count)
                        pos += len(str(mon)) if count == 1 else count
                elif c == 'D':
                    if count == 3:
                        # Day with suffix (1st, 2nd, etc.)
                        day = DateTime._parse_int(s, pos, 1)
                        pos += len(str(day))
                        # Skip suffix
                        while pos < len(s) and s[pos].isalpha():
                            pos += 1
                    else:
                        day = DateTime._parse_int(s, pos, count)
                        pos += len(str(day)) if count == 1 else count
                elif c == 'W':
                    # Skip weekday
                    while pos < len(s) and s[pos].isalpha():
                        pos += 1
                elif c == "'":
                    # Quoted literal
                    if count == 2:
                        # '' means literal quote - must match
                        if pos >= len(s) or s[pos] != "'":
                            raise ValueError(f"Expected literal quote at position {pos}")
                        pos += 1
                        i += 2  # Skip both quotes
                        continue
                    else:
                        i += 1
                        while i < pattern_len and pattern[i] != "'":
                            if pos < len(s) and s[pos] == pattern[i]:
                                pos += 1
                            i += 1
                        count = 1
                else:
                    # Literal character
                    if pos < len(s) and s[pos] == c:
                        pos += 1

                i += count

            return Date(year, Month._get(mon - 1), day)
        except Exception as e:
            if checked:
                from .Err import ParseErr
                raise ParseErr.make(f"Date: {s}")
            return None

    #################################################################
    # Python Interop (to_py / from_py)
    #################################################################

    def to_py(self):
        """Convert to native Python datetime.date.

        Returns:
            A datetime.date object.

        Example:
            >>> fantom_date.to_py()
            datetime.date(2025, 1, 21)
        """
        from datetime import date as py_date
        month_num = self._month.ordinal() + 1
        return py_date(self._year, month_num, self._day)

    @staticmethod
    def from_py(d):
        """Create Date from native Python datetime.date.

        Args:
            d: Python datetime.date object

        Returns:
            Fantom Date

        Example:
            >>> from datetime import date
            >>> Date.from_py(date.today())
            Date("2025-01-21")
        """
        return Date(d.year, Month._get(d.month - 1), d.day)


class Time(Obj):
    """Time represents a time of day to nanosecond precision."""

    def __init__(self, hour=0, min_=0, sec=0, ns=0):
        super().__init__()
        self._hour = hour
        self._min = min_
        self._sec = sec
        self._ns = ns

    @staticmethod
    def now(tz=None):
        from .TimeZone import TimeZone
        if tz is None:
            tz = TimeZone.cur()
        # Get current time and convert to requested timezone
        now = DateTime.now(None)  # null = fresh datetime
        if now.tz() != tz:
            now = now.to_time_zone(tz)
        return Time(now.hour(), now.min_(), now.sec(), now.nano_sec())

    def hour(self): return self._hour
    def min_(self): return self._min
    def sec(self): return self._sec
    def nano_sec(self): return self._ns

    def to_str(self):
        base = f"{self._hour:02d}:{self._min:02d}:{self._sec:02d}"
        if self._ns != 0:
            # Add nanoseconds with trailing zeros preserved
            base = f"{base}.{self._ns:09d}"
        return base

    def __str__(self):
        return self.to_str()

    # Identity/comparison methods
    def equals(self, that):
        """Fantom equality"""
        if not isinstance(that, Time):
            return False
        return (self._hour == that._hour and
                self._min == that._min and
                self._sec == that._sec and
                self._ns == that._ns)

    def compare(self, that):
        """Fantom compare - returns -1, 0, or 1"""
        if self._hour != that._hour:
            return -1 if self._hour < that._hour else 1
        if self._min != that._min:
            return -1 if self._min < that._min else 1
        if self._sec != that._sec:
            return -1 if self._sec < that._sec else 1
        if self._ns != that._ns:
            return -1 if self._ns < that._ns else 1
        return 0

    def hash_(self):
        """Fantom hash"""
        return (self._hour << 28) ^ (self._min << 21) ^ (self._sec << 14) ^ self._ns

    def __eq__(self, other):
        if not isinstance(other, Time):
            return False
        return self.equals(other)

    def __hash__(self):
        return self.hash_()

    def __lt__(self, other):
        return self.compare(other) < 0

    def __le__(self, other):
        return self.compare(other) <= 0

    def __gt__(self, other):
        return self.compare(other) > 0

    def __ge__(self, other):
        return self.compare(other) >= 0

    # Constants for time arithmetic
    _NS_PER_SEC = 1000000000
    _NS_PER_MIN = 60 * _NS_PER_SEC
    _NS_PER_HOUR = 60 * _NS_PER_MIN
    _NS_PER_DAY = 24 * _NS_PER_HOUR

    def to_duration(self):
        """Return duration of time elapsed since midnight"""
        from .Duration import Duration
        ticks = (self._hour * Time._NS_PER_HOUR +
                 self._min * Time._NS_PER_MIN +
                 self._sec * Time._NS_PER_SEC +
                 self._ns)
        return Duration.make(ticks)

    @staticmethod
    def from_duration(d):
        """Create Time from duration since midnight"""
        ticks = d.ticks()
        if ticks == 0:
            return Time.def_val()
        if ticks < 0 or ticks >= Time._NS_PER_DAY:
            from .Err import ArgErr
            raise ArgErr.make(f"Duration out of range: {d}")

        hour = ticks // Time._NS_PER_HOUR
        ticks %= Time._NS_PER_HOUR
        min_ = ticks // Time._NS_PER_MIN
        ticks %= Time._NS_PER_MIN
        sec = ticks // Time._NS_PER_SEC
        ns = ticks % Time._NS_PER_SEC

        return Time(hour, min_, sec, ns)

    @staticmethod
    def make(hour=None, min_=None, sec=None, ns=0):
        """Create a Time. If hour is None, returns defVal."""
        if hour is None:
            return Time.def_val()
        if min_ is None:
            min_ = 0
        if sec is None:
            sec = 0
        return Time(hour, min_, sec, ns)

    @staticmethod
    def def_val():
        """Default value: 00:00:00"""
        if not hasattr(Time, '_defVal') or Time._defVal is None:
            Time._defVal = Time(0, 0, 0, 0)
        return Time._defVal

    def _plus_ticks(self, ticks):
        """Internal helper for time arithmetic with rollover"""
        if ticks == 0:
            return self
        if abs(ticks) > Time._NS_PER_DAY:
            from .Err import ArgErr
            from .Duration import Duration
            raise ArgErr.make(f"Duration out of range: {Duration.make(ticks)}")

        new_ticks = self.to_duration().ticks() + ticks
        if new_ticks < 0:
            new_ticks = Time._NS_PER_DAY + new_ticks
        if new_ticks >= Time._NS_PER_DAY:
            new_ticks %= Time._NS_PER_DAY

        from .Duration import Duration
        return Time.from_duration(Duration.make(new_ticks))

    def plus(self, duration):
        """Add duration (0-24hr range, with rollover)"""
        return self._plus_ticks(duration.ticks())

    def minus(self, duration):
        """Subtract duration (0-24hr range, with rollover)"""
        return self._plus_ticks(-duration.ticks())

    def __add__(self, other):
        """Python + operator: Time + Duration -> Time"""
        return self.plus(other)

    def __sub__(self, other):
        """Python - operator: Time - Duration -> Time"""
        return self.minus(other)

    def is_midnight(self):
        """Return true if this time is midnight (00:00:00.000)"""
        return self._hour == 0 and self._min == 0 and self._sec == 0 and self._ns == 0

    def to_iso(self):
        """Format as ISO 8601 time string"""
        if self._ns == 0:
            return f"{self._hour:02d}:{self._min:02d}:{self._sec:02d}"
        else:
            ns_str = f"{self._ns:09d}".rstrip('0')
            return f"{self._hour:02d}:{self._min:02d}:{self._sec:02d}.{ns_str}"

    @staticmethod
    def from_iso(s, checked=True):
        """Parse ISO 8601 time string"""
        return Time.from_str(s, checked)

    @staticmethod
    def from_str(s, checked=True):
        """Parse time from HH:MM:SS string"""
        try:
            parts = s.split(':')
            if len(parts) < 2:
                raise ValueError("Invalid time format")
            hour = int(parts[0])
            min_ = int(parts[1])
            sec = 0
            ns = 0
            if len(parts) >= 3:
                sec_parts = parts[2].split('.')
                sec = int(sec_parts[0])
                if len(sec_parts) > 1:
                    ns_str = sec_parts[1].ljust(9, '0')[:9]
                    ns = int(ns_str)
            # Validate ranges
            if hour < 0 or hour > 23 or min_ < 0 or min_ > 59 or sec < 0 or sec > 59:
                raise ValueError("Invalid time values")
            return Time(hour, min_, sec, ns)
        except Exception:
            if checked:
                from .Err import ParseErr
                raise ParseErr.make(f"Invalid Time: {s}")
            return None

    def to_code(self):
        """Return Fantom code representation"""
        if self.equals(Time.def_val()):
            return "Time.defVal"
        return f'Time("{self.to_str()}")'

    def to_locale(self, pattern=None, locale=None):
        """Format Time using locale pattern"""
        if pattern is None:
            # Use locale-specific default pattern
            from .Locale import Locale
            cur = locale if locale is not None else Locale.cur()
            # US locale uses 12-hour time with AM/PM
            if cur.country() == "US":
                pattern = "k:mmAA"
            else:
                # Non-US locales use 24-hour time
                pattern = "hh:mm"
        result = []
        i = 0
        while i < len(pattern):
            c = pattern[i]
            count = 1
            while i + count < len(pattern) and pattern[i + count] == c:
                count += 1
            if c == 'h':
                # h = 24-hour clock
                result.append(f"{self._hour:02d}" if count >= 2 else str(self._hour))
            elif c == 'k':
                # k = 12-hour clock
                h = self._hour % 12
                if h == 0:
                    h = 12
                result.append(f"{h:02d}" if count >= 2 else str(h))
            elif c == 'm':
                result.append(f"{self._min:02d}" if count >= 2 else str(self._min))
            elif c == 's':
                result.append(f"{self._sec:02d}" if count >= 2 else str(self._sec))
            elif c == 'S':
                # Optional seconds - omit if sec and ns are 0
                if self._sec != 0 or self._ns != 0:
                    result.append(f"{self._sec:02d}" if count >= 2 else str(self._sec))
            elif c == 'f' or c == 'F':
                # Fractional seconds
                req = 0  # required digits
                opt = 0  # optional digits
                if c == 'F':
                    opt = count
                else:
                    req = count
                    # Look ahead for F's
                    while i + count < len(pattern) and pattern[i + count] == 'F':
                        opt += 1
                        count += 1
                # Output fractional digits
                frac = self._ns
                tenth = 100000000  # 10^8
                frac_str = ""
                for x in range(9):
                    if req > 0:
                        req -= 1
                    else:
                        if frac == 0 or opt <= 0:
                            break
                        opt -= 1
                    frac_str += str(frac // tenth)
                    frac %= tenth
                    tenth //= 10
                result.append(frac_str)
            elif c == 'a':
                # 'a' = lowercase a/p, 'aa' = lowercase am/pm
                if count == 1:
                    result.append("a" if self._hour < 12 else "p")
                else:
                    result.append("am" if self._hour < 12 else "pm")
            elif c == 'A':
                # 'A' = uppercase A/P, 'AA' = uppercase AM/PM
                if count == 1:
                    result.append("A" if self._hour < 12 else "P")
                else:
                    result.append("AM" if self._hour < 12 else "PM")
            elif c == "'":
                # Quoted literal - '' means literal quote
                num_literals = 0
                i += 1
                while i < len(pattern) and pattern[i] != "'":
                    result.append(pattern[i])
                    num_literals += 1
                    i += 1
                if num_literals == 0:
                    result.append("'")
                count = 1
            else:
                # Check for symbol skip before S or F
                if i + 1 < len(pattern):
                    next_c = pattern[i + 1]
                    # Don't display symbol before .FFF if fractions is zero
                    if next_c == 'F' and self._ns == 0:
                        i += count
                        continue
                    # Don't display symbol before :SS if secs and ns are zero
                    if next_c == 'S' and self._sec == 0 and self._ns == 0:
                        i += count
                        continue
                result.append(c)
            i += count
        return "".join(result)

    @staticmethod
    def from_locale(s, pattern, checked=True):
        """Parse Time from locale pattern string"""
        try:
            hour = 0
            min_ = 0
            sec = 0
            ns = 0

            pos = 0
            i = 0
            pattern_len = len(pattern)
            skipped_last = False

            while i < pattern_len:
                c = pattern[i]
                count = 1
                while i + count < pattern_len and pattern[i + count] == c:
                    count += 1

                if c == 'h' or c == 'k':
                    hour = DateTime._parse_int(s, pos, count)
                    pos += len(str(hour)) if count == 1 else count
                elif c == 'm':
                    min_ = DateTime._parse_int(s, pos, count)
                    pos += len(str(min_)) if count == 1 else count
                elif c == 's':
                    sec = DateTime._parse_int(s, pos, count)
                    pos += len(str(sec)) if count == 1 else count
                elif c == 'S':
                    # Optional seconds
                    if not skipped_last and pos < len(s) and s[pos].isdigit():
                        sec = DateTime._parse_int(s, pos, count)
                        pos += len(str(sec)) if count == 1 else count
                elif c == 'a' or c == 'A':
                    if pos < len(s):
                        am_pm = s[pos].lower()
                        pos += count
                        if am_pm == 'p':
                            if hour < 12:
                                hour += 12
                        else:
                            if hour == 12:
                                hour = 0
                elif c == 'f' or c == 'F':
                    # Fractional seconds
                    if skipped_last:
                        pass  # Skip
                    else:
                        ns = 0
                        tenth = 100000000
                        while pos < len(s) and s[pos].isdigit():
                            ns += (ord(s[pos]) - 48) * tenth
                            tenth //= 10
                            pos += 1
                elif c == "'":
                    # Quoted literal
                    if count == 2:
                        # '' means literal quote - must match
                        if pos >= len(s) or s[pos] != "'":
                            raise ValueError(f"Expected literal quote at position {pos}")
                        pos += 1
                        i += 2  # Skip both quotes
                        continue
                    else:
                        i += 1
                        while i < pattern_len and pattern[i] != "'":
                            if pos >= len(s) or s[pos] != pattern[i]:
                                raise ValueError(f"Expected literal at position {pos}")
                            pos += 1
                            i += 1
                        count = 1
                else:
                    # Literal character - handle optional skipping for S and F
                    if i + 1 < pattern_len:
                        next_c = pattern[i + 1]
                        if next_c in ('F', 'S'):
                            if pos >= len(s) or s[pos] != c:
                                skipped_last = True
                                i += count
                                continue
                    skipped_last = False
                    if pos < len(s) and s[pos] == c:
                        pos += 1

                i += count

            return Time(hour, min_, sec, ns)
        except Exception as e:
            if checked:
                from .Err import ParseErr
                raise ParseErr.make(f"Time: {s}")
            return None

    def to_date_time(self, date, tz=None):
        """Convert to DateTime with given date"""
        from .TimeZone import TimeZone
        if tz is None:
            tz = TimeZone.cur()
        return DateTime(date.year(), date.month(), date.day(),
                       self._hour, self._min, self._sec, self._ns, tz)

    #################################################################
    # Python Interop (to_py / from_py)
    #################################################################

    def to_py(self):
        """Convert to native Python datetime.time.

        Returns:
            A datetime.time object.

        Note: Python datetime.time only has microsecond precision, so
              nanoseconds are truncated to microseconds.

        Example:
            >>> fantom_time.to_py()
            datetime.time(14, 30, 45, 123456)
        """
        from datetime import time as py_time
        microseconds = self._ns // 1000
        return py_time(self._hour, self._min, self._sec, microseconds)

    @staticmethod
    def from_py(t):
        """Create Time from native Python datetime.time.

        Args:
            t: Python datetime.time object

        Returns:
            Fantom Time

        Example:
            >>> from datetime import time
            >>> Time.from_py(time(14, 30, 45))
            Time("14:30:45")
        """
        ns = t.microsecond * 1000
        return Time(t.hour, t.minute, t.second, ns)


# Static initialization - capture boot time when module loads
# This matches JS behavior: staticInit.js sets DateTime.__boot = DateTime.now()
# Note: We import TimeZone here to ensure boot uses the same tz as TimeZone.cur()
def _init_boot():
    from .TimeZone import TimeZone
    return DateTime.make_ticks(DateTime._now_ticks_raw(), TimeZone.cur())
DateTime._boot = _init_boot()
del _init_boot  # Clean up helper function
