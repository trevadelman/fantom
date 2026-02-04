#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

import zipfile
import gzip
import zlib
import io
from .Obj import Obj


class Zip(Obj):
    """
    Zip provides support for reading and writing compressed zip archives.
    """

    def __init__(self):
        self._file = None
        self._zip_file = None
        self._contents = None
        self._mode = None  # 'open', 'read', 'write'
        self._out_stream = None
        self._in_stream = None
        self._zip_out = None
        self._current_entry = None

    # =========================================================================
    # Static factory methods
    # =========================================================================

    @staticmethod
    def open_(file):
        """
        Open a zip file for reading.
        Returns a Zip instance with file and contents accessible.
        """
        from .File import File
        from .Map import Map
        from .Uri import Uri

        z = Zip()
        z._file = file
        z._mode = 'open'

        # Get the OS path from the file
        os_path = file.os_path()
        if os_path is None:
            from .Err import IOErr
            raise IOErr("Cannot get OS path for file")

        try:
            z._zip_file = zipfile.ZipFile(os_path, 'r')
        except Exception as e:
            from .Err import IOErr
            raise IOErr(f"Cannot open zip file: {e}")

        # Build contents map
        contents = Map()
        for name in z._zip_file.namelist():
            # Create Uri with leading slash
            uri_str = '/' + name if not name.startswith('/') else name
            uri = Uri.from_str(uri_str)
            # Create a ZipEntryFile for each entry
            entry_file = ZipEntryFile(z._zip_file, name, uri)
            contents.set_(uri, entry_file)

        z._contents = Map.ro(contents)  # Make readonly as per Fantom spec
        return z

    @staticmethod
    def read(in_stream):
        """
        Open a zip file from an input stream for reading.
        Use readNext() to iterate through the entries.
        """
        z = Zip()
        z._mode = 'read'
        z._in_stream = in_stream

        # Read the entire stream into a bytes buffer for zipfile
        # Get all bytes from the input stream
        buf = io.BytesIO()
        while True:
            b = in_stream.read()
            if b is None:
                break
            buf.write(bytes([b]))

        buf.seek(0)
        try:
            z._zip_file = zipfile.ZipFile(buf, 'r')
            z._zip_entries = iter(z._zip_file.namelist())
        except Exception as e:
            from .Err import IOErr
            raise IOErr(f"Cannot read zip stream: {e}")

        return z

    @staticmethod
    def write(out_stream):
        """
        Create a zip output stream for writing.
        Use writeNext() to add entries.
        """
        z = Zip()
        z._mode = 'write'
        z._out_stream = out_stream
        z._zip_buffer = io.BytesIO()
        z._zip_out = zipfile.ZipFile(z._zip_buffer, 'w', zipfile.ZIP_DEFLATED)
        return z

    # =========================================================================
    # Compression stream wrappers
    # =========================================================================

    @staticmethod
    def gzip_out_stream(out):
        """
        Wrap an output stream with gzip compression.
        Returns a GzipOutStream that compresses data written to it.
        """
        return GzipOutStream(out)

    @staticmethod
    def gzip_in_stream(in_stream):
        """
        Wrap an input stream with gzip decompression.
        Returns a GzipInStream that decompresses data read from it.
        """
        return GzipInStream(in_stream)

    @staticmethod
    def deflate_out_stream(out, opts=None):
        """
        Wrap an output stream with deflate compression.
        Options:
            - nowrap (bool): if true, don't write zlib header/trailer
            - level (int): 0-9, compression level (0=none, 9=best)
        """
        nowrap = False
        level = -1  # default compression
        if opts is not None:
            nowrap = opts.get("nowrap", False)
            if opts.get("level") is not None:
                level = int(opts.get("level"))
        return DeflateOutStream(out, nowrap, level)

    @staticmethod
    def deflate_in_stream(in_stream, opts=None):
        """
        Wrap an input stream with deflate decompression.
        Options: nowrap (bool) - if true, expect raw deflate without zlib header
        """
        nowrap = False
        if opts is not None:
            nowrap = opts.get("nowrap", False)
        return DeflateInStream(in_stream, nowrap)

    @staticmethod
    def unzip_into(zip_file, target_dir):
        """
        Unzip all entries from zip_file into target_dir.
        Returns the count of entries extracted.
        """
        os_path = zip_file.os_path()
        target_path = target_dir.os_path()

        with zipfile.ZipFile(os_path, 'r') as zf:
            entries = zf.namelist()
            for name in entries:
                # Extract preserving modified time
                info = zf.getinfo(name)
                zf.extract(name, target_path)

                # Try to preserve modification time
                import os
                import time
                extracted_path = os.path.join(target_path, name)
                if os.path.exists(extracted_path) and not name.endswith('/'):
                    # Convert zipfile date_time to timestamp
                    dt = info.date_time
                    mtime = time.mktime((dt[0], dt[1], dt[2], dt[3], dt[4], dt[5], 0, 0, -1))
                    os.utime(extracted_path, (mtime, mtime))

            return len(entries)

    # =========================================================================
    # Instance properties
    # =========================================================================

    def file(self):
        """Return the file if opened from a file, else null."""
        return self._file

    def contents(self):
        """
        Return the map of Uri to File entries if opened in 'open' mode.
        Returns null if opened in 'read' or 'write' mode.
        """
        if self._mode != 'open':
            return None
        return self._contents

    # =========================================================================
    # Read mode methods
    # =========================================================================

    def read_next(self):
        """
        Read the next entry in the zip as a File.
        Returns null at end of entries.
        """
        if self._mode == 'open':
            from .Err import UnsupportedErr
            raise UnsupportedErr("readNext not supported in open mode")

        if self._mode != 'read':
            from .Err import UnsupportedErr
            raise UnsupportedErr("readNext requires read mode")

        try:
            name = next(self._zip_entries)
            from .Uri import Uri
            uri_str = '/' + name if not name.startswith('/') else name
            uri = Uri.from_str(uri_str)
            return ZipEntryFile(self._zip_file, name, uri)
        except StopIteration:
            return None

    def read_each(self, func):
        """
        Iterate through all entries calling func for each.
        """
        while True:
            entry = self.read_next()
            if entry is None:
                break
            func(entry)

    # =========================================================================
    # Write mode methods
    # =========================================================================

    def write_next(self, uri, modified=None):
        """
        Write the next entry with the given URI path.
        Returns an OutStream to write the entry contents.
        """
        if self._mode != 'write':
            from .Err import UnsupportedErr
            raise UnsupportedErr("writeNext requires write mode")

        # Validate URI
        uri_str = str(uri)
        if '#' in uri_str:
            from .Err import ArgErr
            raise ArgErr(f"URI cannot contain fragment: {uri}")
        if '?' in uri_str:
            from .Err import ArgErr
            raise ArgErr(f"URI cannot contain query: {uri}")

        # Remove leading slash for zipfile
        name = uri_str.lstrip('/')

        # Create a buffer to collect the entry data
        entry_buffer = io.BytesIO()
        self._current_entry = (name, modified, entry_buffer)

        return ZipEntryOutStream(self, entry_buffer)

    def finish(self):
        """
        Finish writing the zip stream.
        Must be called when done adding entries.
        """
        if self._mode != 'write':
            from .Err import UnsupportedErr
            raise UnsupportedErr("finish requires write mode")

        # Close the zip file
        self._zip_out.close()

        # Write the zip data to the output stream
        self._zip_buffer.seek(0)
        for byte in self._zip_buffer.read():
            self._out_stream.write(byte)
        self._out_stream.flush()

    def _finish_entry(self, entry_buffer, name, modified):
        """Internal: finish writing an entry to the zip."""
        import time as time_mod
        import os
        from datetime import datetime

        # Get the data
        data = entry_buffer.getvalue()

        # Create ZipInfo with proper date
        info = zipfile.ZipInfo(name)
        if modified is not None:
            # Convert Fantom DateTime to epoch millis then to local time tuple
            # This preserves the instant in time for round-trip
            epoch_millis = modified.to_java()
            epoch_secs = epoch_millis / 1000.0
            local_time = time_mod.localtime(epoch_secs)
            info.date_time = (local_time.tm_year, local_time.tm_mon, local_time.tm_mday,
                              local_time.tm_hour, local_time.tm_min, local_time.tm_sec)
        else:
            # Use current time
            now = datetime.now()
            info.date_time = (now.year, now.month, now.day,
                              now.hour, now.minute, now.second)

        self._zip_out.writestr(info, data)

    # =========================================================================
    # Common methods
    # =========================================================================

    def close(self):
        """Close the zip file."""
        if self._zip_file is not None:
            self._zip_file.close()
            self._zip_file = None
        if self._zip_out is not None:
            # For write mode, close writes the buffered data to output stream
            self._zip_out.close()
            self._zip_buffer.seek(0)
            for byte in self._zip_buffer.read():
                self._out_stream.write(byte)
            self._out_stream.flush()
            self._zip_out = None
        return True

    def to_str(self):
        """String representation."""
        if self._file is not None:
            return str(self._file.uri())
        return "Zip"

    def __str__(self):
        return self.to_str()


# =============================================================================
# ZipEntryFile - File implementation for zip entries
# =============================================================================

class ZipEntryFile:
    """
    A File representing an entry within a zip file.
    """

    def __init__(self, zip_file, name, uri):
        self._zip_file = zip_file
        self._name = name
        self._uri = uri
        self._info = zip_file.getinfo(name) if name in zip_file.namelist() else None

    def uri(self):
        return self._uri

    def parent(self):
        return None

    def os_path(self):
        return None

    def size(self):
        if self._info is not None:
            return self._info.file_size
        return None

    def modified(self):
        if self._info is not None:
            import time as time_mod
            from .DateTime import DateTime
            dt = self._info.date_time
            # date_time is (year, month, day, hour, min, sec) in local time
            # Convert to epoch millis then to Fantom DateTime
            local_time_tuple = (dt[0], dt[1], dt[2], dt[3], dt[4], dt[5], 0, 0, -1)
            epoch_secs = time_mod.mktime(local_time_tuple)
            epoch_millis = int(epoch_secs * 1000)
            return DateTime.from_java(epoch_millis)
        return None

    def in_(self, bufSize=4096):
        """Get an input stream to read the entry."""
        data = self._zip_file.read(self._name)
        from .Buf import Buf
        buf = Buf.make(len(data))
        for b in data:
            buf.write(b)
        buf.flip()
        return buf.in_()

    def read_all_str(self, normalizeNewlines=True):
        """Read entire entry as string."""
        data = self._zip_file.read(self._name)
        text = data.decode('utf-8')
        if normalizeNewlines:
            text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text

    def read_all_buf(self):
        """Read entire entry as Buf."""
        data = self._zip_file.read(self._name)
        from .Buf import Buf
        buf = Buf.make(len(data))
        for b in data:
            buf.write(b)
        buf.flip()
        return buf

    def copy_into(self, target_dir, options=None):
        """Copy this entry into the target directory."""
        from .File import File
        target = target_dir.plus(self._uri.name())
        data = self._zip_file.read(self._name)

        out = target.out()
        for b in data:
            out.write(b)
        out.close()

        return target

    def out(self, append=False, bufSize=4096):
        from .Err import IOErr
        raise IOErr("Cannot write to zip entry")

    def create(self):
        from .Err import IOErr
        raise IOErr("Cannot create zip entry")

    def delete(self):
        from .Err import IOErr
        raise IOErr("Cannot delete zip entry")

    def delete_on_exit(self):
        from .Err import IOErr
        raise IOErr("Cannot deleteOnExit zip entry")

    def move_to(self, target):
        from .Err import IOErr
        raise IOErr("Cannot move zip entry")

    def typeof(self):
        from .Type import Type
        return Type.find("sys::File")


# =============================================================================
# ZipEntryOutStream - OutStream for writing zip entries
# =============================================================================

class ZipEntryOutStream:
    """OutStream wrapper for writing a zip entry."""

    def __init__(self, zip_instance, buffer):
        self._zip = zip_instance
        self._buffer = buffer
        self._closed = False

    def write(self, byte):
        if self._closed:
            from .Err import IOErr
            raise IOErr("Stream closed")
        self._buffer.write(bytes([byte & 0xFF]))
        return self

    def write_buf(self, buf, n=None):
        if self._closed:
            from .Err import IOErr
            raise IOErr("Stream closed")
        if n is None:
            n = buf.remaining()
        for _ in range(n):
            b = buf.read()
            if b is None:
                break
            self._buffer.write(bytes([b & 0xFF]))
        return self

    def write_i4(self, val):
        """Write 4-byte integer in big-endian."""
        self._buffer.write(bytes([
            (val >> 24) & 0xFF,
            (val >> 16) & 0xFF,
            (val >> 8) & 0xFF,
            val & 0xFF
        ]))
        return self

    def print_(self, obj):
        """Print string."""
        s = str(obj) if obj is not None else ""
        self._buffer.write(s.encode('utf-8'))
        return self

    def print_line(self, obj=""):
        """Print string with newline."""
        s = str(obj) if obj is not None else ""
        self._buffer.write((s + "\n").encode('utf-8'))
        return self

    def write_props(self, props, close=True):
        """Write map as props file format.

        Args:
            props: Map of string key/value pairs
            close: Whether to close the stream when done (default True)

        Returns:
            self for chaining
        """
        for key, val in props.items():
            # Escape key and value
            escaped_key = self._escape_props_key(str(key))
            escaped_val = self._escape_props_val(str(val))
            # Write line
            line = f"{escaped_key}={escaped_val}\n"
            self._buffer.write(line.encode('utf-8'))

        if close:
            self.close()
        return self

    def _escape_props_key(self, s):
        """Escape special characters in props key."""
        result = []
        for ch in s:
            if ch == '=':
                result.append('\\u003d')
            elif ch == ':':
                result.append('\\u003a')
            elif ch == '\\':
                result.append('\\\\')
            elif ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            elif ord(ch) > 127:
                result.append(f'\\u{ord(ch):04x}')
            else:
                result.append(ch)
        return ''.join(result)

    def _escape_props_val(self, s):
        """Escape special characters in props value."""
        result = []
        for ch in s:
            if ch == '\\':
                result.append('\\\\')
            elif ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            elif ord(ch) > 127:
                result.append(f'\\u{ord(ch):04x}')
            else:
                result.append(ch)
        return ''.join(result)

    def flush(self):
        return self

    def close(self):
        if not self._closed:
            self._closed = True
            # Finish this entry
            name, modified, buffer = self._zip._current_entry
            self._zip._finish_entry(buffer, name, modified)
        return True


# =============================================================================
# GzipOutStream - Gzip compression wrapper
# =============================================================================

class GzipOutStream:
    """OutStream that compresses output with gzip."""

    def __init__(self, out):
        self._out = out
        self._buffer = io.BytesIO()
        self._gzip = gzip.GzipFile(fileobj=self._buffer, mode='wb')

    def write(self, byte):
        self._gzip.write(bytes([byte & 0xFF]))
        return self

    def write_buf(self, buf, n=None):
        if n is None:
            n = buf.remaining()
        data = bytearray()
        for _ in range(n):
            b = buf.read()
            if b is None:
                break
            data.append(b & 0xFF)
        self._gzip.write(bytes(data))
        return self

    def print_(self, obj):
        s = str(obj) if obj is not None else ""
        self._gzip.write(s.encode('utf-8'))
        return self

    def print_line(self, obj=""):
        s = str(obj) if obj is not None else ""
        self._gzip.write((s + "\n").encode('utf-8'))
        return self

    def write_char(self, c):
        """Write single character using UTF-8 encoding."""
        ch = chr(c) if isinstance(c, int) else c
        self._gzip.write(ch.encode('utf-8'))
        return self

    def write_chars(self, s, off=0, length=None):
        """Write string characters using UTF-8 encoding."""
        if length is None:
            length = len(s) - off
        self._gzip.write(s[off:off+length].encode('utf-8'))
        return self

    def flush(self):
        self._gzip.flush()
        self._flush_to_out()
        return self

    def _flush_to_out(self):
        """Flush buffered data to underlying stream."""
        data = self._buffer.getvalue()
        self._buffer.seek(0)
        self._buffer.truncate()
        for b in data:
            self._out.write(b)

    def close(self):
        self._gzip.close()
        self._flush_to_out()
        return True


# =============================================================================
# GzipInStream - Gzip decompression wrapper
# =============================================================================

class GzipInStream:
    """InStream that decompresses gzip input."""

    def __init__(self, in_stream):
        self._in = in_stream
        # Read all input data first
        data = bytearray()
        while True:
            b = in_stream.read()
            if b is None:
                break
            data.append(b)

        # Decompress
        self._buffer = io.BytesIO(gzip.decompress(bytes(data)))

    def read(self):
        b = self._buffer.read(1)
        if not b:
            return None
        return b[0]

    def read_buf(self, buf, n):
        data = self._buffer.read(n)
        if not data:
            return None
        for b in data:
            buf.write(b)
        return len(data)

    def read_all_str(self, normalizeNewlines=True):
        data = self._buffer.read()
        text = data.decode('utf-8')
        if normalizeNewlines:
            text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text

    def close(self):
        return True


# =============================================================================
# DeflateOutStream - Deflate compression wrapper
# =============================================================================

class DeflateOutStream:
    """OutStream that compresses output with deflate."""

    def __init__(self, out, nowrap=False, level=-1):
        self._out = out
        self._nowrap = nowrap
        # wbits: negative for raw deflate (no header), positive for zlib format
        wbits = -zlib.MAX_WBITS if nowrap else zlib.MAX_WBITS
        # level: -1 = default, 0 = no compression, 9 = best
        if level < 0:
            level = zlib.Z_DEFAULT_COMPRESSION
        self._compressor = zlib.compressobj(level, zlib.DEFLATED, wbits)
        self._buffer = bytearray()

    def write(self, byte):
        self._buffer.append(byte & 0xFF)
        return self

    def write_buf(self, buf, n=None):
        if n is None:
            n = buf.remaining()
        for _ in range(n):
            b = buf.read()
            if b is None:
                break
            self._buffer.append(b & 0xFF)
        return self

    def print_(self, obj):
        s = str(obj) if obj is not None else ""
        self._buffer.extend(s.encode('utf-8'))
        return self

    def print_line(self, obj=""):
        s = str(obj) if obj is not None else ""
        self._buffer.extend((s + "\n").encode('utf-8'))
        return self

    def flush(self):
        if self._buffer:
            compressed = self._compressor.compress(bytes(self._buffer))
            self._buffer.clear()
            for b in compressed:
                self._out.write(b)
        return self

    def close(self):
        # Compress remaining data
        if self._buffer:
            compressed = self._compressor.compress(bytes(self._buffer))
            for b in compressed:
                self._out.write(b)
            self._buffer.clear()

        # Flush compressor
        final = self._compressor.flush()
        for b in final:
            self._out.write(b)
        return True


# =============================================================================
# DeflateInStream - Deflate decompression wrapper
# =============================================================================

class DeflateInStream:
    """InStream that decompresses deflate input."""

    def __init__(self, in_stream, nowrap=False):
        self._in = in_stream
        self._nowrap = nowrap

        # Read all input data first
        data = bytearray()
        while True:
            b = in_stream.read()
            if b is None:
                break
            data.append(b)

        # Decompress
        wbits = -zlib.MAX_WBITS if nowrap else zlib.MAX_WBITS
        self._buffer = io.BytesIO(zlib.decompress(bytes(data), wbits))

    def read(self):
        b = self._buffer.read(1)
        if not b:
            return None
        return b[0]

    def read_buf(self, buf, n):
        data = self._buffer.read(n)
        if not data:
            return None
        for b in data:
            buf.write(b)
        return len(data)

    def read_all_str(self, normalizeNewlines=True):
        data = self._buffer.read()
        text = data.decode('utf-8')
        if normalizeNewlines:
            text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text

    def close(self):
        return True
