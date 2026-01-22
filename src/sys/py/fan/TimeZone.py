#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from datetime import timezone, timedelta
import zoneinfo
from .Obj import Obj


# ========================================================================
# TimeZone DST Rule Classes
# ========================================================================

class TimeZoneDstTime:
    """Represents a DST transition time (e.g., 'last Sunday of March at 2:00 AM').

    Fields:
        mon: month (0-11, 0=Jan)
        onMode: 'd'=specific day, 'l'=last weekday, '>'=weekday on or after, '<'=weekday on or before
        onWeekday: weekday (0-6, 0=Sun)
        onDay: day of month (1-31)
        atTime: seconds from midnight
        atMode: 'w'=wall time, 's'=standard time, 'u'=UTC
    """

    def __init__(self, mon, onMode, onWeekday, onDay, atTime, atMode):
        self.mon = mon                          # month (0-11)
        self.on_mode = chr(onMode) if isinstance(onMode, int) else onMode  # 'd', 'l', '>', '<'
        self.on_weekday = onWeekday              # weekday (0-6, 0=Sun)
        self.on_day = onDay                      # day of month (1-31)
        self.at_time = atTime                    # seconds from midnight
        self.at_mode = chr(atMode) if isinstance(atMode, int) else atMode  # 'w', 's', 'u'


class TimeZoneRule:
    """Timezone rule for a year range with DST info.

    Fields:
        startYear: year rule took effect
        offset: UTC offset in seconds (standard time)
        stdAbbr: standard time abbreviation (e.g., 'EST')
        dstOffset: DST offset in seconds (0 = no DST)
        dstAbbr: daylight time abbreviation (e.g., 'EDT'), None if no DST
        dstStart: TimeZoneDstTime for DST start, None if no DST
        dstEnd: TimeZoneDstTime for DST end, None if no DST
    """

    def __init__(self):
        self.start_year = None   # year rule took effect
        self.offset = None      # UTC offset in seconds
        self.std_abbr = None     # standard time abbreviation
        self.dst_offset = None   # DST offset in seconds (0 = no DST)
        self.dst_abbr = None     # daylight time abbreviation
        self.dst_start = None    # TimeZoneDstTime for DST start
        self.dst_end = None      # TimeZoneDstTime for DST end

    def is_wall_time(self):
        """Return True if DST transition times are in wall time (vs standard or UTC)"""
        return self.dst_start is not None and self.dst_start.at_mode == 'w'


# ========================================================================
# Binary Buffer Reader for Timezone Data
# ========================================================================

class _TzBuf:
    """Simple binary buffer reader for parsing timezone data.

    Format is big-endian. Methods:
    - read(): read 1 unsigned byte
    - readS2(): read 2-byte signed integer
    - readS4(): read 4-byte signed integer
    - readUtf(): read 2-byte length + UTF-8 string
    - more(): check if more bytes available
    """

    def __init__(self, data):
        """Initialize with bytes data (from base64 decode)"""
        self._data = data
        self._pos = 0

    def read(self):
        """Read 1 unsigned byte"""
        if self._pos >= len(self._data):
            return None
        b = self._data[self._pos]
        self._pos += 1
        return b

    def read_s2(self):
        """Read 2-byte signed integer (big-endian)"""
        c1 = self.read()
        c2 = self.read()
        if c1 is None or c2 is None:
            raise ValueError("Unexpected end of stream")
        c = (c1 << 8) | c2
        # Convert to signed
        return c if c <= 0x7FFF else (c - 0x10000)

    def read_s4(self):
        """Read 4-byte signed integer (big-endian)"""
        c1 = self.read()
        c2 = self.read()
        c3 = self.read()
        c4 = self.read()
        if c1 is None or c2 is None or c3 is None or c4 is None:
            raise ValueError("Unexpected end of stream")
        c = (c1 << 24) | (c2 << 16) | (c3 << 8) | c4
        # Convert to signed
        return c if c <= 0x7FFFFFFF else (c - 0x100000000)

    def read_utf(self):
        """Read 2-byte length + UTF-8 string"""
        len1 = self.read()
        len2 = self.read()
        if len1 is None or len2 is None:
            raise ValueError("Unexpected end of stream")
        utflen = (len1 << 8) | len2
        # Read UTF-8 bytes
        utf_bytes = self._data[self._pos:self._pos + utflen]
        self._pos += utflen
        return utf_bytes.decode('utf-8')

    def more(self):
        """Return True if more bytes available"""
        return self._pos < len(self._data)


# ========================================================================
# Timezone Data Cache (loaded from tz.js base64 strings)
# ========================================================================

# Base64-encoded timezone data from tz.js
# Format: fullName + rules (startYear, offset, stdAbbr, dstOffset, [dstAbbr, dstStart, dstEnd])
_TZ_DATA = {
    # US timezones
    "America/Los_Angeles": "ABNBbWVyaWNhL0xvc19BbmdlbGVzB9f//4+AAANQU1QAAA4QAANQRFQCPgAIAAAcIHcKPgABAAAcIHcHy///j4AAA1BTVAAADhAAA1BEVAM+AAEAABwgdwlsAAAAABwgdw==",
    "America/New_York": "ABBBbWVyaWNhL05ld19Zb3JrB9f//7mwAANFU1QAAA4QAANFRFQCPgAIAAAcIHcKPgABAAAcIHcHy///ubAAA0VTVAAADhAAA0VEVAM+AAEAABwgdwlsAAAAABwgdw==",
    "America/Chicago": "ABBBbWVyaWNhL0NoaWNhZ28H1///nZAAA0NTVAAADhAAA0NEVAI+AAgAABwgdwo+AAEAABwgdwfL//+dkAADQ1NUAAAOEAADQ0RUAz4AAQAAHCB3CWwAAAAAHCB3",
    "America/Denver": "AA9BbWVyaWNhL0RlbnZlcgfX//+RgAADTVNUAAAOEAADTURUAj4ACAAAICB3Cj4AAQAAHCB3B8v//5GAAAdNU1QvTURUAAAOEAAHTVNUL01EVAM+AAEAABwgdwlsAAAAABwgdw==",
    # Europe
    "Europe/Kiev": "AAtFdXJvcGUvS2lldgfMAAAcIAADRUVUAAAOEAAERUVTVAJsAAAAAA4QdQlsAAAAAA4QdQfLAAAcIAADRUVUAAAOEAAERUVTVAJsAAAAAA4QdQhsAAAAAA4QdQ==",
    "Europe/London": "AA1FdXJvcGUvTG9uZG9uB8wAAAAAAAADR01UAAAOEA.ABQlNUAmwAAAAADhB1CWwAAAAADhB1B8sAAAAAAAADR01UAAAOEAADQlNUAmwAAAAADhB1CGwAAAAADhB1",
    "Europe/Amsterdam": "ABFFdXJvcGUvQW1zdGVyZGFtB8wAAA4QAANDRVQAAA4QAARDRVNUAmwAAAAAHCBzCWwAAAAAHCBzB8sAAA4QAANDRVQAAA4QAARDRVNUAmwAAAAAHCBzCGwAAAAAHCBz",
    # Australia (southern hemisphere)
    "Australia/Sydney": "ABBBdXN0cmFsaWEvU3lkbmV5B9gAAIygAARBRVNUAAAOEAAEQUVEVAk+AAEAABwgcwM+AAEAABwgcwfXAACMoAAEQUVTVAAADhAABEFFRFQJbAAAAAAcIHMCbAAAAAAcIHMH1gAAjKAABEFFU1QAAA4QAARBRURUCWwAAAAAHCBzAz4AAQAAHCBzB9EAAIygAARBRVNUAAAOEAAEQUVEVAlsAAAAABwgcwJsAAAAABwgcwfQAACMoAAEQUVTVAAADhAABEFFRFQHbAAAAAAcIHMCbAAAAAAcIHMHzAAAjKAABEFFU1QAAA4QAARBRURUCWwAAAAAHCBzAmwAAAAAHCBzB8sAAIygAARBRVNUAAAOEAAEQUVEVAlsAAAAABwgcwI+AAEAABwgcw==",
    # Brazil (southern hemisphere) - correct data from tz.js
    "America/Sao_Paulo": "ABFBbWVyaWNhL1Nhb19QYXVsbwfj///V0AAHLTAzLy0wMgAAAAAH4v//1dAABy0wMy8tMDIAAA4QAActMDMvLTAyCj4AAQAAAAB3AT4ADwAAAAB3B+D//9XQAActMDMvLTAyAAAOEAAHLTAzLy0wMgk+AA8AAAAAdwE+AA8AAAAAdwff///V0AAHLTAzLy0wMgAADhAABy0wMy8tMDIJPgAPAAAAAHcBPgAWAAAAAHcH3f//1dAABy0wMy8tMDIAAA4QAActMDMvLTAyCT4ADwAAAAB3AT4ADwAAAAB3B9z//9XQAActMDMvLTAyAAAOEAAHLTAzLy0wMgk+AA8AAAAAdwE+ABYAAAAAdwfY///V0AAHLTAzLy0wMgAADhAABy0wMy8tMDIJPgAPAAAAAHcBPgAPAAAAAHcH1///1dAABy0wMy8tMDIAAA4QAActMDMvLTAyCT4ACAAAAAB3AWQAGQAAAAB3B9b//9XQAActMDMvLTAyAAAOEAAHLTAzLy0wMgpkAAUAAAAAdwE+AA8AAAAAdwfV///V0AAHLTAzLy0wMgAADhAABy0wMy8tMDIJZAAQAAAAAHcBPgAPAAAAAHcH1P//1dAABy0wMy8tMDIAAA4QAActMDMvLTAyCmQAAgAAAAB3AT4ADwAAAAB3B9P//9XQAActMDMvLTAyAAAOEAAHLTAzLy0wMglkABMAAAAAdwE+AA8AAAAAdwfS///V0AAHLTAzLy0wMgAADhAABy0wMy8tMDIKZAADAAAAAHcBPgAPAAAAAHcH0f//1dAABy0wMy8tMDIAAA4QAActMDMvLTAyCT4ACAAAAAB3AT4ADwAAAAB3B9D//9XQAActMDMvLTAyAAAOEAAHLTAzLy0wMgk+AAgAAAAAdwFkABsAAAAAdwfP///V0AAHLTAzLy0wMgAADhAABy0wMy8tMDIJZAADAAAAAHcBZAAVAAAAAHcHzv//1dAABy0wMy8tMDIAAA4QAActMDMvLTAyCWQACwAAAAB3AmQAAQAAAAB3B83//9XQAActMDMvLTAyAAAOEAAHLTAzLy0wMglkAAYAAAAAdwFkABAAAAAAdwfM///V0AAHLTAzLy0wMgAADhAABy0wMy8tMDIJZAAGAAAAAHcBZAALAAAAAHcHy///1dAABy0wMy8tMDIAAA4QAActMDMvLTAyCT4ACwAAAAB3AT4ADwAAAAB3",
}

# Parsed rules cache - populated lazily
_TZ_RULES = {}

def _decode_dst(buf):
    """Decode a DST transition time from binary buffer"""
    return TimeZoneDstTime(
        buf.read(),    # mon (0-11)
        buf.read(),    # onMode ('d', 'l', '>', '<')
        buf.read(),    # onWeekday (0-6)
        buf.read(),    # onDay (1-31)
        buf.read_s4(),  # atTime (seconds from midnight)
        buf.read()     # atMode ('w', 's', 'u')
    )


def _decode_tz_rules(base64_data):
    """Decode timezone rules from base64-encoded data.

    Returns: (fullName, rules_list)
    """
    import base64

    # Decode base64 to bytes
    data = base64.b64decode(base64_data)
    buf = _TzBuf(data)

    # Read full name
    fullName = buf.read_utf()

    # Read rules
    rules = []
    while buf.more():
        rule = TimeZoneRule()
        rule.startYear = buf.read_s2()
        rule.offset = buf.read_s4()
        rule.stdAbbr = buf.read_utf()
        rule.dstOffset = buf.read_s4()
        if rule.dstOffset != 0:
            rule.dstAbbr = buf.read_utf()
            rule.dstStart = _decode_dst(buf)
            rule.dstEnd = _decode_dst(buf)
        rules.append(rule)

    return fullName, rules


# ========================================================================
# DST Offset Calculator
# ========================================================================

def _weekday_in_month(year, month_ord, weekday_ord, count):
    """Get the nth (or last if count=-1) occurrence of weekday in month.

    Args:
        year: year
        month_ord: month ordinal (0-11, 0=Jan)
        weekday_ord: weekday ordinal (0-6, 0=Sun)
        count: 1=first, 2=second, -1=last

    Returns:
        day of month (1-31)
    """
    import calendar

    # Python uses Mon=0, Sun=6; Fantom uses Sun=0, Sat=6
    # Convert Fantom weekday to Python weekday
    py_weekday = (weekday_ord - 1) % 7  # Sun(0)->6, Mon(1)->0, etc.

    month = month_ord + 1  # Convert 0-11 to 1-12
    _, days_in_month = calendar.monthrange(year, month)

    if count == -1:
        # Find last occurrence
        for day in range(days_in_month, 0, -1):
            if calendar.weekday(year, month, day) == py_weekday:
                return day
    elif count > 0:
        # Find nth occurrence
        found = 0
        for day in range(1, days_in_month + 1):
            if calendar.weekday(year, month, day) == py_weekday:
                found += 1
                if found == count:
                    return day

    return 1  # Fallback


def _compare_month(x, mon):
    """Compare DST time month to specified month."""
    if x.mon < mon:
        return -1
    if x.mon > mon:
        return 1
    return 0


def _compare_on_day(rule, x, year, mon, day):
    """Compare DST day specification to specified day.

    onMode:
        'd': specific day of month
        'l': last weekday in month
        '>': weekday on or after specified day
        '<': weekday on or before specified day
    """
    # Universal atTime might push us into the previous day
    if x.at_mode == 'u' and rule.offset + x.at_time < 0:
        day += 1

    if x.on_mode == 'd':
        # Specific day of month
        if x.on_day < day:
            return -1
        if x.on_day > day:
            return 1
        return 0

    elif x.on_mode == 'l':
        # Last weekday in month
        last = _weekday_in_month(year, mon, x.on_weekday, -1)
        if last < day:
            return -1
        if last > day:
            return 1
        return 0

    elif x.on_mode == '>':
        # Weekday on or after specified day
        start = _weekday_in_month(year, mon, x.on_weekday, 1)
        while start < x.on_day:
            start += 7
        if start < day:
            return -1
        if start > day:
            return 1
        return 0

    elif x.on_mode == '<':
        # Weekday on or before specified day
        lastw = _weekday_in_month(year, mon, x.on_weekday, -1)
        while lastw > x.on_day:
            lastw -= 7
        if lastw < day:
            return -1
        if lastw > day:
            return 1
        return 0

    else:
        raise ValueError(f"Unknown on_mode: {x.on_mode}")


def _compare_at_time(rule, x, time):
    """Compare DST transition time to specified time in seconds."""
    atTime = x.at_time

    # If universal time, convert to local time
    if x.at_mode == 'u':
        if rule.offset + x.at_time < 0:
            atTime = 24 * 60 * 60 + rule.offset + x.at_time
        else:
            atTime += rule.offset

    if atTime < time:
        return -1
    if atTime > time:
        return 1
    return 0


def _compare(rule, x, year, mon, day, time):
    """Compare specified datetime to DST transition.

    Returns: -1 if x < specified time, +1 if x > specified time, 0 if equal
    """
    c = _compare_month(x, mon)
    if c != 0:
        return c

    c = _compare_on_day(rule, x, year, mon, day)
    if c != 0:
        return c

    return _compare_at_time(rule, x, time)


def _dst_offset(rule, year, mon, day, time):
    """Calculate DST offset for given datetime.

    Args:
        rule: TimeZoneRule for the year
        year: year
        mon: month ordinal (0-11)
        day: day of month (1-31)
        time: seconds from midnight

    Returns:
        DST offset in seconds (0 if not in DST)
    """
    start = rule.dstStart
    end = rule.dstEnd

    if start is None:
        return 0

    s = _compare(rule, start, year, mon, day, time)
    e = _compare(rule, end, year, mon, day, time)

    # If end month comes earlier than start month,
    # then this is DST in southern hemisphere
    if end.mon < start.mon:
        if e > 0 or s <= 0:
            return rule.dstOffset
    else:
        if s <= 0 and e > 0:
            return rule.dstOffset

    return 0


def _is_dst_date(rule, x, year, mon, day):
    """Return True if given date is the DST transition date."""
    return (_compare_month(x, mon) == 0 and
            _compare_on_day(rule, x, year, mon, day) == 0)


class TimeZone(Obj):
    """TimeZone represents a geographic timezone with historical daylight savings rules."""

    # TimeZone is a value type - same name = same identity (like Duration, etc.)
    _same_uses_equals = True

    _cache = {}
    _utc = None
    _cur = None

    def __new__(cls, name):
        """Use __new__ to return cached instances for timezone singletons"""
        # Resolve aliases first
        if name in cls._aliases:
            name = cls._aliases[name]

        # Check cache
        if name in cls._cache:
            return cls._cache[name]

        # Create new instance
        instance = super().__new__(cls)
        return instance

    def __init__(self, name):
        # Prevent re-initialization of cached instances
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        super().__init__()

        # Store original name for Etc/ prefixed names
        original_name = name

        # Resolve aliases first (but NOT for Etc/UTC or Etc/Rel - they need special handling)
        if name in TimeZone._aliases and name not in ("Etc/UTC", "Etc/Rel"):
            name = TimeZone._aliases[name]

        # Map Fantom short names to Python zoneinfo full names
        short_to_full = {
            "UTC": "UTC",
            "Rel": "UTC",
            # Americas
            "New_York": "America/New_York",
            "Los_Angeles": "America/Los_Angeles",
            "Chicago": "America/Chicago",
            "Denver": "America/Denver",
            "Phoenix": "America/Phoenix",
            "St_Johns": "America/St_Johns",
            "Sao_Paulo": "America/Sao_Paulo",
            "Godthab": "America/Godthab",
            # Europe
            "London": "Europe/London",
            "Paris": "Europe/Paris",
            "Amsterdam": "Europe/Amsterdam",
            "Kiev": "Europe/Kiev",
            "Riga": "Europe/Riga",
            "Madrid": "Europe/Madrid",
            # Asia
            "Tokyo": "Asia/Tokyo",
            "Jerusalem": "Asia/Jerusalem",
            "Kolkata": "Asia/Kolkata",
            "Ho_Chi_Minh": "Asia/Ho_Chi_Minh",
            "Taipei": "Asia/Taipei",
            # Australia/Pacific
            "Sydney": "Australia/Sydney",
            "Melbourne": "Australia/Melbourne",
        }

        # Map full names back to short names
        full_to_short = {v: k for k, v in short_to_full.items()}
        full_to_short["UTC"] = "UTC"

        # Determine short name and full Python timezone name
        if name in short_to_full:
            # Input is a short name like "New_York"
            self._name = name
            py_name = short_to_full[name]
        elif name in full_to_short:
            # Input is a full name like "America/New_York"
            self._name = full_to_short[name]
            py_name = name
        else:
            # Unknown - extract short name from full if possible
            if '/' in name:
                self._name = name.split('/')[-1]
            else:
                self._name = name
            py_name = name

        # Set fullName - for UTC and Rel, the full name uses Etc/ prefix
        if self._name == "UTC":
            self._fullName = "Etc/UTC"
        elif self._name == "Rel":
            self._fullName = "Etc/Rel"
        else:
            self._fullName = py_name

        try:
            if py_name == "UTC":
                self._tz = timezone.utc
            elif py_name.startswith("GMT+") or py_name.startswith("GMT-"):
                # Fantom GMT+N = IANA Etc/GMT+N (both use reversed signs: +N means N hours WEST of UTC)
                # So GMT+5 = Etc/GMT+5 = UTC-5
                iana_name = f"Etc/{py_name}"
                self._tz = zoneinfo.ZoneInfo(iana_name)
            else:
                self._tz = zoneinfo.ZoneInfo(py_name)
        except Exception:
            # Fallback to UTC if timezone not found
            self._tz = timezone.utc

        # Add to cache using all name forms for singleton lookup
        TimeZone._cache[name] = self
        TimeZone._cache[self._name] = self  # Short name like "New_York"
        # Only cache under fullName if it's different and won't overwrite a different timezone
        # (e.g., don't let "Rel" overwrite the "UTC" cache entry)
        if self._fullName != self._name and self._fullName not in TimeZone._cache:
            TimeZone._cache[self._fullName] = self  # Full name like "America/New_York"

        # Initialize rules as None - loaded lazily
        self._rules = None

    def _get_rules(self):
        """Get timezone rules (lazily loaded from _TZ_DATA)."""
        if self._rules is not None:
            return self._rules

        # Check global cache first
        fullName = self._fullName
        if fullName in _TZ_RULES:
            self._rules = _TZ_RULES[fullName]
            return self._rules

        # Try to load from _TZ_DATA
        if fullName in _TZ_DATA:
            try:
                _, rules = _decode_tz_rules(_TZ_DATA[fullName])
                _TZ_RULES[fullName] = rules
                self._rules = rules
                return rules
            except Exception:
                pass

        # No rules available - return empty list
        self._rules = []
        return self._rules

    def _get_rule(self, year):
        """Get the timezone rule for a specific year.

        Rules are sorted by startYear descending - find the first rule
        where startYear <= year.
        """
        rules = self._get_rules()
        if not rules:
            return None

        # Rules are stored newest-first (highest startYear first)
        for rule in rules:
            if year >= rule.startYear:
                return rule

        # Fallback to oldest rule
        return rules[-1] if rules else None

    @staticmethod
    def utc():
        """Get the UTC timezone"""
        if TimeZone._utc is None:
            TimeZone._utc = TimeZone("UTC")
            TimeZone._cache["UTC"] = TimeZone._utc
        return TimeZone._utc

    @staticmethod
    def def_val():
        """Default value is UTC timezone"""
        return TimeZone.utc()

    @staticmethod
    def cur():
        """Get the current default timezone"""
        if TimeZone._cur is None:
            from datetime import datetime
            try:
                # Get the local timezone offset from the system
                local_dt = datetime.now().astimezone()
                offset = local_dt.utcoffset()
                if offset is not None:
                    offset_hrs = offset.total_seconds() / 3600
                    # Map common offsets to timezone names
                    offset_map = {
                        -8: "America/Los_Angeles",
                        -7: "America/Denver",
                        -6: "America/Chicago",
                        -5: "America/New_York",
                        0: "UTC",
                        1: "Europe/Paris",
                        2: "Europe/Amsterdam",
                        9: "Asia/Tokyo",
                        10: "Australia/Sydney",
                    }
                    mapped_name = offset_map.get(int(offset_hrs))
                    if mapped_name:
                        TimeZone._cur = TimeZone.from_str(mapped_name, checked=False)
                if TimeZone._cur is None:
                    TimeZone._cur = TimeZone.utc()
            except Exception:
                TimeZone._cur = TimeZone.utc()
        return TimeZone._cur

    @staticmethod
    def rel():
        """Get the relative timezone (no historical daylight savings)"""
        return TimeZone("Rel")

    # Timezone aliases - map old/alternate names to canonical names
    _aliases = {
        "Asia/Saigon": "Asia/Ho_Chi_Minh",
        "Saigon": "Asia/Ho_Chi_Minh",
        "Ho_Chi_Minh": "Asia/Ho_Chi_Minh",
        "Australia/Victoria": "Australia/Melbourne",
        "Victoria": "Australia/Melbourne",
        "America/Argentina/ComodRivadavia": "America/Argentina/Catamarca",
        "ComodRivadavia": "America/Argentina/Catamarca",
        # Fantom uses Etc/ prefix for UTC and Rel
        "Etc/UTC": "UTC",
        "Etc/Rel": "Rel",
    }

    # Known valid timezone names (Fantom short names and full IANA names)
    _valid_names = {
        "UTC", "Rel", "Etc/UTC", "Etc/Rel",
        # Americas
        "New_York", "America/New_York",
        "Los_Angeles", "America/Los_Angeles",
        "Chicago", "America/Chicago",
        "Denver", "America/Denver",
        "Phoenix", "America/Phoenix",
        "St_Johns", "America/St_Johns",
        "Sao_Paulo", "America/Sao_Paulo",
        "Godthab", "America/Godthab",
        # Europe
        "London", "Europe/London",
        "Paris", "Europe/Paris",
        "Amsterdam", "Europe/Amsterdam",
        "Kiev", "Europe/Kiev",
        "Riga", "Europe/Riga",
        "Madrid", "Europe/Madrid",
        # Asia
        "Tokyo", "Asia/Tokyo",
        "Jerusalem", "Asia/Jerusalem",
        "Kolkata", "Asia/Kolkata",
        "Ho_Chi_Minh", "Asia/Ho_Chi_Minh",
        "Taipei", "Asia/Taipei",
        # Australia/Pacific
        "Sydney", "Australia/Sydney",
        "Melbourne", "Australia/Melbourne",
    }

    # Common region prefixes to try when resolving short timezone names
    _region_prefixes = [
        "Europe/", "America/", "Asia/", "Africa/", "Australia/",
        "Pacific/", "Atlantic/", "Indian/", "Antarctica/"
    ]

    @staticmethod
    def from_str(name, checked=True):
        """Find timezone by name"""
        # Check for alias first
        if name in TimeZone._aliases:
            name = TimeZone._aliases[name]

        if name in TimeZone._cache:
            return TimeZone._cache[name]

        # Check if it's a valid known timezone or a valid zoneinfo name
        is_valid = name in TimeZone._valid_names
        resolved_name = name  # The name we'll actually use for zoneinfo

        if not is_valid:
            # Try to validate against zoneinfo directly
            try:
                import zoneinfo
                zoneinfo.ZoneInfo(name)
                is_valid = True
            except Exception:
                pass

        if not is_valid:
            # Check for Etc/GMT+X or GMT+X style offsets
            if name.startswith("Etc/GMT") or name.startswith("GMT+") or name.startswith("GMT-"):
                is_valid = True

        if not is_valid:
            # Try common region prefixes (e.g., "Warsaw" -> "Europe/Warsaw")
            import zoneinfo
            for prefix in TimeZone._region_prefixes:
                try:
                    full_name = prefix + name
                    zoneinfo.ZoneInfo(full_name)
                    # Found it! Use the full name
                    resolved_name = full_name
                    is_valid = True
                    break
                except Exception:
                    pass

        if not is_valid:
            if checked:
                from .Err import ParseErr
                raise ParseErr(f"Invalid TimeZone: {name}")
            return None

        try:
            tz = TimeZone(resolved_name)
            # Cache under both the original name and resolved name
            TimeZone._cache[name] = tz
            if resolved_name != name:
                TimeZone._cache[resolved_name] = tz
            return tz
        except Exception as e:
            if checked:
                from .Err import ParseErr
                raise ParseErr(f"Invalid TimeZone: {name}")
            return None

    @staticmethod
    def list_names():
        """List all available timezone names"""
        from .List import List
        # Must include Rel and UTC plus common timezone names
        common = ["Rel", "UTC", "New_York", "Los_Angeles", "Chicago", "Denver",
                  "London", "Paris", "Tokyo", "Sydney"]
        return List.to_immutable(List.from_list(common))

    @staticmethod
    def list_full_names():
        """List all available full timezone names"""
        from .List import List
        # Full names including region prefixes (UTC and Rel use Etc/ prefix)
        full = ["Etc/Rel", "Etc/UTC", "America/New_York", "America/Los_Angeles",
                "America/Chicago", "America/Denver", "Europe/London",
                "Europe/Paris", "Asia/Tokyo", "Australia/Sydney"]
        return List.to_immutable(List.from_list(full))

    def name(self):
        """Short name like 'New_York'"""
        return self._name

    def full_name(self):
        """Full name like 'America/New_York'"""
        return self._fullName

    def offset(self, year):
        """Get the offset from UTC for this timezone as a Duration"""
        from datetime import datetime
        from .Duration import Duration
        # Get offset for January 1 of the given year
        dt = datetime(year, 1, 1, tzinfo=self._tz)
        offset = dt.utcoffset()
        if offset is None:
            return Duration.make(0)
        # Convert seconds to nanoseconds for Duration
        return Duration.make(int(offset.total_seconds() * 1_000_000_000))

    def dst_offset(self, year):
        """Get the daylight savings offset as a Duration. Returns None if no DST."""
        from datetime import datetime
        from .Duration import Duration
        # Get DST offset for July 1 (typically during DST)
        dt = datetime(year, 7, 1, tzinfo=self._tz)
        dst = dt.dst()
        if dst is None or dst.total_seconds() == 0:
            return None  # No DST for this timezone
        # Convert seconds to nanoseconds for Duration
        return Duration.make(int(dst.total_seconds() * 1_000_000_000))

    def std_abbr(self, year):
        """Standard abbreviation like 'EST'"""
        from datetime import datetime
        # Special case for Rel timezone - always return "Rel"
        if self._name == "Rel":
            return "Rel"
        # Special case for UTC timezone - always return "UTC"
        if self._name == "UTC":
            return "UTC"
        # Get abbreviation for January 1 (typically standard time)
        try:
            dt = datetime(year, 1, 1, 12, 0, 0, tzinfo=self._tz)
            abbr = dt.tzname()
            if abbr:
                return abbr
        except Exception:
            pass
        return self._name

    def dst_abbr(self, year):
        """Daylight savings abbreviation like 'EDT'. Returns None if no DST."""
        from datetime import datetime
        # First check if this timezone has DST
        dst = self.dst_offset(year)
        if dst is None or (hasattr(dst, 'ticks') and dst.ticks() == 0):
            return None  # No DST for this timezone
        # Get abbreviation for July 1 (typically daylight time)
        try:
            dt = datetime(year, 7, 1, 12, 0, 0, tzinfo=self._tz)
            abbr = dt.tzname()
            if abbr:
                return abbr
        except Exception:
            pass
        return self._name

    def to_str(self):
        return self._name

    def __str__(self):
        return self.to_str()

    def equals(self, other):
        """Fantom equals - compare by timezone name"""
        if not isinstance(other, TimeZone):
            return False
        return self._name == other._name

    def __eq__(self, other):
        if not isinstance(other, TimeZone):
            return False
        return self._name == other._name

    def __hash__(self):
        return hash(self._name)

    # Allow calling TimeZone("name") to create a timezone
    @staticmethod
    def make(name=None):
        """Create a TimeZone. If name is None, returns defVal (UTC)."""
        if name is None:
            return TimeZone.def_val()
        return TimeZone.from_str(name)

    @staticmethod
    def _from_gmt_offset(offset_secs):
        """Create a TimeZone from a GMT offset in seconds.

        This is used for parsing timezone offsets like +05:00 or -07:00
        when the offset doesn't match the default timezone.
        """
        if offset_secs == 0:
            return TimeZone.utc()

        # Try to find a matching GMT timezone
        hrs = abs(offset_secs) // 3600
        # GMT timezones use opposite sign (GMT+5 = UTC-5)
        sign = '-' if offset_secs > 0 else '+'
        gmt_name = f"Etc/GMT{sign}{hrs}"

        try:
            return TimeZone.from_str(gmt_name)
        except:
            # Fall back to UTC if we can't find the timezone
            return TimeZone.utc()

    def typeof(self):
        """Return the Fantom type of this object."""
        from fan.sys.Type import Type
        return Type.find("sys::TimeZone")

    def literal_encode(self, encoder):
        """Encode for serialization.

        Simple types serialize as: Type("toStr")
        Example: sys::TimeZone("New_York")
        """
        encoder.w_type(self.typeof())
        encoder.w('(')
        encoder.w_str_literal(self.to_str(), '"')
        encoder.w(')')
