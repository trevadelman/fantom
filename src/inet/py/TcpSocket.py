#
# inet::TcpSocket - Python native implementation
#
# Implements raw TCP socket support using Python's socket module.
# This enables use of the pure-Fantom Redis client and other TCP-based protocols.
#
# Note: TcpSocketInStream and TcpSocketOutStream are kept in this file as
# internal implementation details - they're not standalone types meant for
# general use. They extend the base InStream/OutStream for type compatibility.
#

import socket
from fan.sys.Obj import Obj
from fan.sys.InStream import InStream
from fan.sys.OutStream import OutStream


class TcpSocket(Obj):
    """TCP socket implementation using Python's socket module."""

    @staticmethod
    def make(config=None):
        """Create a TcpSocket."""
        return TcpSocket(config)

    def __init__(self, config=None):
        super().__init__()
        self._config = config
        self._socket = None
        self._connected = False
        self._closed = False
        self._in = None
        self._out = None

    def config(self):
        return self._config

    def is_bound(self):
        return self._socket is not None

    def is_connected(self):
        return self._connected

    def is_closed(self):
        return self._closed

    def connect(self, addr, port, timeout=None):
        """Connect to a remote address and port."""
        # Create socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set timeout if specified
        if timeout is not None:
            # timeout is Duration, convert to seconds
            if hasattr(timeout, 'to_millis'):
                self._socket.settimeout(timeout.to_millis() / 1000.0)
            else:
                self._socket.settimeout(float(timeout) / 1_000_000_000.0)

        # Get hostname from IpAddr
        if hasattr(addr, '_hostname'):
            hostname = addr._hostname
        elif hasattr(addr, 'numeric'):
            hostname = addr.numeric()
        else:
            hostname = str(addr)

        # Connect
        self._socket.connect((hostname, int(port)))
        self._connected = True

        # Create wrapped streams
        self._in = TcpSocketInStream(self._socket)
        self._out = TcpSocketOutStream(self._socket)

        return self

    def close(self):
        """Close the socket."""
        if self._socket is not None:
            try:
                self._socket.close()
            except:
                pass
        self._closed = True
        self._connected = False
        return True

    def in_(self):
        """Get the input stream."""
        if self._in is None:
            raise Exception("Socket not connected")
        return self._in

    def out(self):
        """Get the output stream."""
        if self._out is None:
            raise Exception("Socket not connected")
        return self._out


class TcpSocketInStream(InStream):
    """Input stream wrapper for a TCP socket.

    Extends InStream for type compatibility with Fantom code that expects InStream.
    This is an internal implementation detail of TcpSocket.
    """

    def __init__(self, sock):
        super().__init__(None)  # No wrapped stream
        self._socket = sock
        self._file = sock.makefile('rb')

    def read(self):
        """Read a single byte, return as int or None at EOF."""
        b = self._file.read(1)
        if not b:
            return None
        return b[0]

    def read_char(self):
        """Read a single character (byte as int)."""
        b = self._file.read(1)
        if not b:
            return None
        return b[0]

    def read_buf(self, buf, n):
        """Read up to n bytes into buf."""
        data = self._file.read(n)
        if not data:
            return None
        # Append to buf
        if hasattr(buf, '_data'):
            buf._data.extend(data)
        elif hasattr(buf, 'write_bytes'):
            buf.write_bytes(data)
        else:
            # Assume it's a Buf with internal bytearray
            for b in data:
                buf.write(b)
        return len(data)

    def read_all_buf(self):
        """Read all remaining bytes."""
        from fan.sys.Buf import Buf
        data = self._file.read()
        buf = Buf.make(len(data))
        buf._data = bytearray(data)
        buf._size = len(data)
        return buf

    def read_all_str(self, charset=None):
        """Read all as string."""
        data = self._file.read()
        return data.decode('utf-8')

    def read_chars(self, n):
        """Read n characters as string."""
        data = self._file.read(n)
        return data.decode('utf-8')

    def close(self):
        """Close the stream."""
        try:
            self._file.close()
        except:
            pass
        return self


class TcpSocketOutStream(OutStream):
    """Output stream wrapper for a TCP socket.

    Extends OutStream for type compatibility with Fantom code that expects OutStream.
    This is an internal implementation detail of TcpSocket.
    """

    def __init__(self, sock):
        super().__init__(None)  # No wrapped stream
        self._socket = sock
        self._file = sock.makefile('wb')

    def write(self, val):
        """Write a byte."""
        if isinstance(val, int):
            self._file.write(bytes([val]))
        else:
            self._file.write(bytes([int(val)]))
        return self

    def write_buf(self, buf):
        """Write buffer contents."""
        if hasattr(buf, '_data'):
            # Buf has internal bytearray
            size = buf._size if hasattr(buf, '_size') else len(buf._data)
            data = bytes(buf._data[:size])
        elif hasattr(buf, 'to_bytes'):
            # Buf.toBytes() method
            data = buf.to_bytes()
        elif hasattr(buf, 'size'):
            # Buf with size() method - read byte by byte
            data = bytearray()
            for i in range(buf.size()):
                data.append(buf.get(i))
            data = bytes(data)
        else:
            # Fallback - treat as bytes-like
            data = bytes(buf) if isinstance(buf, (bytes, bytearray)) else str(buf).encode('utf-8')
        self._file.write(data)
        return self

    def write_chars(self, s):
        """Write string as bytes."""
        self._file.write(s.encode('utf-8'))
        return self

    def print_(self, s):
        """Print a string (no newline)."""
        if s is not None:
            self._file.write(str(s).encode('utf-8'))
        return self

    def print_line(self, s=None):
        """Print a string with newline."""
        if s is not None:
            self._file.write(str(s).encode('utf-8'))
        self._file.write(b'\n')
        return self

    def flush(self):
        """Flush the stream."""
        self._file.flush()
        return self

    def close(self):
        """Close the stream."""
        try:
            self._file.flush()
            self._file.close()
        except:
            pass
        return self
