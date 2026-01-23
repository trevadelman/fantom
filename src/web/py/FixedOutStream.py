#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#
# Hand-written Python native for FixedOutStream.
# This is needed because the transpiled version uses self._out which
# conflicts with OutStream's delegation pattern.
#

from fan.sys.OutStream import OutStream
from fan.sys.Err import IOErr


class FixedOutStream(OutStream):
    """
    OutStream wrapper that enforces a fixed byte limit.

    Writes up to 'fixed' bytes to the underlying stream, then throws
    IOErr on any additional writes.
    """

    @staticmethod
    def make(out, fixed):
        return FixedOutStream(out, fixed)

    def __init__(self, out, fixed):
        # Pass None to OutStream so it doesn't delegate via _out
        super().__init__(None)
        # Store underlying stream in a different field name
        self._underlying = out
        self._fixed = int(fixed) if fixed is not None else None
        self._written = 0

    def write(self, b):
        """Write single byte, tracking count."""
        self._check_chunk(1)
        self._underlying.write(b)
        return self

    def write_buf(self, buf, n=None):
        """Write bytes from buffer, tracking count."""
        if n is None:
            n = buf.remaining()
        self._check_chunk(n)
        self._underlying.write_buf(buf, n)
        return self

    def flush(self):
        """Flush underlying stream."""
        self._underlying.flush()
        return self

    def close(self):
        """Close - just flush, don't close underlying stream."""
        try:
            self.flush()
            return True
        except:
            return False

    def _check_chunk(self, n):
        """Check if writing n bytes would exceed the fixed limit."""
        self._written += n
        if self._written > self._fixed:
            raise IOErr.make(f"Attempt to write more than Content-Length: {self._fixed}")

    # Inherit print_, printLine, writeChars, writeChar from OutStream
    # which will call our write() method via the encoder
