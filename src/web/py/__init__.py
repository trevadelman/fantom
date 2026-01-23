# Hand-written web module for Python
# Contains native implementations for HTTP client using Python's requests library

# Import and patch WebOutStream first
# This ensures the patch is applied before any other code imports it
from . import WebOutStream as _WebOutStreamModule

# Sentinel to distinguish "not passed" from "passed None"
_MISSING = object()


def _style_fixed(self, attrs=_MISSING):
    """Fixed style() that applies default when not passed.

    Uses sentinel to distinguish:
    - style() -> attrs is _MISSING -> use default "type='text/css'"
    - style(None) -> attrs is None -> no default, produces <style>
    Original Fantom: style(Str? attrs := "type='text/css'")
    """
    if attrs is _MISSING:
        attrs = "type='text/css'"
    return self.tag("style", attrs).nl()


_WebOutStreamModule.WebOutStream.style = _style_fixed


def _script_fixed(self, attrs=_MISSING):
    """Fixed script() that applies default when not passed.

    Uses sentinel to distinguish:
    - script() -> attrs is _MISSING -> use default "type='text/javascript'"
    - script(None) -> attrs is None -> no default, produces <script>
    Original Fantom: script(Str? attrs := "type='text/javascript'")
    """
    if attrs is _MISSING:
        attrs = "type='text/javascript'"
    return self.tag("script", attrs).nl()


_WebOutStreamModule.WebOutStream.script = _script_fixed

# Import other patches after WebOutStream
from . import WebClient
from . import Cookie


# Patch MultiPartInStream.check_line to handle EOF gracefully
# The transpiled code uses read_u1() which throws IOErr at EOF
# We patch it to use read() + None check instead
from . import MultiPartInStream as _MultiPartInStreamModule
from fan.sys.ObjUtil import ObjUtil
from fan import sys as _fan_sys


def _check_line_fixed(self):
    """Read and buffer next line, checking for boundary.

    Fixed version that uses read() instead of read_u1() to handle EOF.
    """
    if ObjUtil.compare_gt(self._cur_line.remaining(), 0):
        return True
    if self._end_of_part:
        return False
    self._cur_line.clear()

    # Read bytes until we find LF or hit 1024 bytes or EOF
    while True:
        c = self._in_.read()  # Use read() instead of read_u1()
        if c is None:
            # EOF - mark as end of part and return what we have
            self._end_of_part = True
            if self._cur_line.pos() > 0:
                self._cur_line.flip()
                return True
            return False

        self._cur_line.write(c)
        if ObjUtil.equals(c, 13):  # CR
            continue
        if ObjUtil.compare_ge(self._cur_line.size(), 1024):
            break
        if ObjUtil.equals(c, 10):  # LF
            break

    # Check if line ends with CRLF (potential boundary)
    if ObjUtil.compare_lt(self._cur_line.size(), 2) or ObjUtil.compare_ne(self._cur_line[-2], 13):
        self._cur_line.seek(0)
        return True

    # Check if boundary follows - MUST write chars to cur_line as we go
    # This is important because if boundary matches, we truncate cur_line
    # to remove the CRLF + boundary chars that were appended
    i = 0
    boundary_len = _fan_sys.Str.size(self._boundary)

    while ObjUtil.compare_lt(i, boundary_len):
        c = self._in_.read()  # Use read() instead of read_u1()
        if c is None:
            # EOF during boundary check - return what we have
            self._end_of_part = True
            self._cur_line.seek(0)
            return True

        if ObjUtil.compare_ne(c, _fan_sys.Str.get(self._boundary, i)):
            # Not a boundary match - write the non-matching char and return
            if ObjUtil.equals(c, 13):
                self._in_.unread(c)
            else:
                self._cur_line.write(c)
            self._cur_line.seek(0)
            return True

        # Matches so far - write char to cur_line (will be truncated if full match)
        self._cur_line.write(c)
        i += 1

    # Matched boundary - remove CRLF and boundary from cur_line
    # cur_line now has: content + CRLF + boundary
    # We want just: content
    self._cur_line.size(self._cur_line.size() - _fan_sys.Str.size(self._boundary) - 2)

    # Check what follows
    c1 = self._in_.read()  # Use read() instead of read_u1()
    c2 = self._in_.read()

    if c1 is None or c2 is None:
        self._end_of_parts = True
        self._end_of_part = True
        if self._cur_line.size() > 0:
            self._cur_line.seek(0)
        return self._cur_line.size() > 0

    if ObjUtil.equals(c1, 45) and ObjUtil.equals(c2, 45):  # '--'
        self._end_of_parts = True
        c1 = self._in_.read()
        c2 = self._in_.read()

    if c1 is not None and c2 is not None:
        if ObjUtil.compare_ne(c1, 13) or ObjUtil.compare_ne(c2, 10):
            raise _fan_sys.IOErr.make(f"Fishy boundary {_fan_sys.Str.to_code(_fan_sys.Int.to_char(c1) + _fan_sys.Int.to_char(c2), 34, True)}")

    self._end_of_part = True
    if self._cur_line.size() > 0:
        self._cur_line.seek(0)
    return ObjUtil.compare_gt(self._cur_line.size(), 0)


# Apply patch directly to the class
_MultiPartInStreamModule.MultiPartInStream.check_line = _check_line_fixed
