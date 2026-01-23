#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#
# Hand-written Python native for ChunkOutStream.
# This is needed because the transpiled version uses self._out which
# conflicts with OutStream's delegation pattern.
#

from fan.sys.OutStream import OutStream
from fan.sys.Buf import Buf
from fan.sys.Err import IOErr
from fan.sys.Int import Int


class ChunkOutStream(OutStream):
    """
    OutStream wrapper that writes using HTTP chunked transfer encoding.

    Data is buffered until chunkSize (1024) bytes are accumulated,
    then written as a chunk to the underlying stream.
    """

    CHUNK_SIZE = 1024

    @staticmethod
    def chunk_size():
        return ChunkOutStream.CHUNK_SIZE

    @staticmethod
    def make(out):
        return ChunkOutStream(out)

    def __init__(self, out):
        # Pass None to OutStream so it doesn't delegate via _out
        super().__init__(None)
        # Store underlying stream in a different field name
        self._underlying = out
        self._buffer = Buf.make(ChunkOutStream.CHUNK_SIZE + 256)
        self._closed = False

    def write(self, b):
        """Write single byte to buffer."""
        self._buffer.write(b)
        self._check_chunk()
        return self

    def write_buf(self, buf, n=None):
        """Write bytes from buffer."""
        if n is None:
            n = buf.remaining()
        self._buffer.write_buf(buf, n)
        self._check_chunk()
        return self

    def flush(self):
        """Flush buffered data as a chunk."""
        if self._closed:
            raise IOErr.make("ChunkOutStream is closed")
        if self._buffer.size() > 0:
            # Write chunk header (hex size + CRLF)
            self._underlying.print_(Int.to_hex(self._buffer.size()))
            self._underlying.print_("\r\n")
            # Write chunk data
            self._buffer.flip()
            self._underlying.write_buf(self._buffer, self._buffer.remaining())
            # Write chunk terminator CRLF
            self._underlying.print_("\r\n")
            self._underlying.flush()
            self._buffer.clear()
        return self

    def close(self):
        """Close the chunked stream - writes final zero-length chunk."""
        if self._closed:
            return True
        try:
            self.flush()
            self._closed = True
            # Write terminating chunk (0 length + double CRLF)
            self._underlying.print_("0\r\n\r\n")
            self._underlying.flush()
            return True
        except:
            return False

    def _check_chunk(self):
        """Flush if buffer exceeds chunk size."""
        if self._buffer.size() >= ChunkOutStream.CHUNK_SIZE:
            self.flush()

    # Inherit print_, printLine, writeChars, writeChar from OutStream
    # which will call our write() method via the encoder
