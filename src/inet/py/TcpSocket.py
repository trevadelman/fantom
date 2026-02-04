#
# inet::TcpSocket - Python native implementation
#
# Implements raw TCP socket support using Python's socket module.
# This enables use of the pure-Fantom Redis client and other TCP-based protocols.
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
        self._bound = False
        self._connected = False
        self._closed = False
        self._in = None
        self._out = None
        self._local_addr = None
        self._local_port = None
        self._remote_addr = None
        self._remote_port = None
        self._options = None

    def config(self):
        return self._config

    def is_bound(self):
        return self._bound

    def is_connected(self):
        return self._connected

    def is_closed(self):
        return self._closed

    def local_addr(self):
        """Get the local IP address, or null if not bound."""
        return self._local_addr

    def local_port(self):
        """Get the local port, or null if not bound."""
        return self._local_port

    def remote_addr(self):
        """Get the remote IP address, or null if not connected."""
        return self._remote_addr

    def remote_port(self):
        """Get the remote port, or null if not connected."""
        return self._remote_port

    def options(self):
        """Get socket options."""
        if self._options is None:
            self._options = TcpSocketOptions(self)
        return self._options

    def bind(self, addr, port):
        """Bind to a local address and port.

        Args:
            addr: IpAddr to bind to, or null for any local address
            port: Port to bind to, or null for system-assigned port

        Returns:
            This socket
        """
        from fan.sys.IOErr import IOErr

        if self._closed:
            raise IOErr.make("Socket is closed")

        # Create socket if not already created
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow address reuse
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Determine bind address
        if addr is not None:
            if hasattr(addr, 'numeric'):
                bind_addr = addr.numeric()
            elif hasattr(addr, '_host'):
                bind_addr = addr._host
            else:
                bind_addr = str(addr)
        else:
            bind_addr = ''

        # Determine bind port
        bind_port = int(port) if port is not None else 0

        try:
            self._socket.bind((bind_addr, bind_port))
            self._bound = True

            # Get actual bound address/port
            actual_addr, actual_port = self._socket.getsockname()
            from fan.inet.IpAddr import IpAddr
            self._local_addr = IpAddr(actual_addr) if actual_addr else None
            self._local_port = actual_port

        except socket.error as e:
            raise IOErr.make(f"Bind failed: {e}")

        return self

    def connect(self, addr, port, timeout=None):
        """Connect to a remote address and port."""
        from fan.sys.IOErr import IOErr
        from fan.inet.IpAddr import IpAddr

        if self._closed:
            raise IOErr.make("Socket is closed")

        # Create socket if not already created
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set timeout if specified
        if timeout is not None:
            if hasattr(timeout, 'to_millis'):
                self._socket.settimeout(timeout.to_millis() / 1000.0)
            else:
                self._socket.settimeout(float(timeout) / 1_000_000_000.0)

        # Get hostname from IpAddr
        if hasattr(addr, '_host'):
            hostname = addr._host
        elif hasattr(addr, 'numeric'):
            hostname = addr.numeric()
        else:
            hostname = str(addr)

        try:
            self._socket.connect((hostname, int(port)))
            self._connected = True
            self._bound = True

            # Get local address info
            local = self._socket.getsockname()
            self._local_addr = IpAddr(local[0]) if local[0] else None
            self._local_port = local[1]

            # Store remote address info
            self._remote_addr = addr if isinstance(addr, IpAddr) else IpAddr(str(addr))
            self._remote_port = int(port)

            # Create wrapped streams
            self._in = TcpSocketInStream(self._socket)
            self._out = TcpSocketOutStream(self._socket)

        except socket.timeout as e:
            raise IOErr.make(f"Connection timed out: {e}")
        except socket.error as e:
            raise IOErr.make(f"Connection failed: {e}")

        return self

    def in_(self):
        """Get the input stream."""
        from fan.sys.IOErr import IOErr
        if not self._connected or self._closed:
            raise IOErr.make("Socket not connected")
        return self._in

    def out(self):
        """Get the output stream."""
        from fan.sys.IOErr import IOErr
        if not self._connected or self._closed:
            raise IOErr.make("Socket not connected")
        return self._out

    def shutdown_in(self):
        """Shutdown the input side of the socket."""
        from fan.sys.IOErr import IOErr
        if not self._connected or self._closed:
            raise IOErr.make("Socket not connected")
        try:
            self._socket.shutdown(socket.SHUT_RD)
        except socket.error as e:
            raise IOErr.make(f"Shutdown failed: {e}")
        return self

    def shutdown_out(self):
        """Shutdown the output side of the socket."""
        from fan.sys.IOErr import IOErr
        if not self._connected or self._closed:
            raise IOErr.make("Socket not connected")
        try:
            self._socket.shutdown(socket.SHUT_WR)
        except socket.error as e:
            raise IOErr.make(f"Shutdown failed: {e}")
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


# Sentinel for distinguishing no argument from None argument
_UNSET = object()


class TcpSocketOptions(Obj):
    """Socket options for TcpSocket."""

    def __init__(self, socket_obj):
        super().__init__()
        self._socket_obj = socket_obj
        self._in_buffer_size = 4096
        self._out_buffer_size = 4096
        self._keep_alive = False
        self._receive_buffer_size = 8192
        self._send_buffer_size = 8192
        self._reuse_addr = False
        self._linger = None
        self._receive_timeout = None
        self._no_delay = True
        self._traffic_class = 0
        self._broadcast = False  # Stored for copyFrom
        self._broadcast_copied = False  # True if broadcast was copied from another socket

    def in_buffer_size(self, val=None):
        if val is None:
            return self._in_buffer_size
        if self._socket_obj._connected:
            from fan.sys.Err import Err
            raise Err.make("Cannot change buffer size after connect")
        self._in_buffer_size = val
        return None

    def out_buffer_size(self, val=None):
        if val is None:
            return self._out_buffer_size
        if self._socket_obj._connected:
            from fan.sys.Err import Err
            raise Err.make("Cannot change buffer size after connect")
        self._out_buffer_size = val
        return None

    def keep_alive(self, val=None):
        if val is None:
            return self._keep_alive
        self._keep_alive = val
        if self._socket_obj._socket is not None:
            self._socket_obj._socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1 if val else 0
            )
        return None

    def receive_buffer_size(self, val=None):
        if val is None:
            return self._receive_buffer_size
        self._receive_buffer_size = val
        if self._socket_obj._socket is not None:
            self._socket_obj._socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF, val
            )
        return None

    def send_buffer_size(self, val=None):
        if val is None:
            return self._send_buffer_size
        self._send_buffer_size = val
        if self._socket_obj._socket is not None:
            self._socket_obj._socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_SNDBUF, val
            )
        return None

    def reuse_addr(self, val=None):
        if val is None:
            return self._reuse_addr
        self._reuse_addr = val
        if self._socket_obj._socket is not None:
            self._socket_obj._socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 if val else 0
            )
        return None

    def linger(self, val=_UNSET):
        if val is _UNSET:
            return self._linger
        self._linger = val
        if self._socket_obj._socket is not None:
            if val is None:
                import struct
                self._socket_obj._socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 0, 0)
                )
            else:
                # val is Duration, convert to seconds
                secs = int(val.to_sec()) if hasattr(val, 'to_sec') else int(val / 1_000_000_000)
                import struct
                self._socket_obj._socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, secs)
                )
        return None

    def receive_timeout(self, val=_UNSET):
        if val is _UNSET:
            return self._receive_timeout
        self._receive_timeout = val
        if self._socket_obj._socket is not None:
            if val is None:
                self._socket_obj._socket.settimeout(None)
            else:
                # val is Duration, convert to seconds
                secs = val.to_sec() if hasattr(val, 'to_sec') else float(val) / 1_000_000_000.0
                self._socket_obj._socket.settimeout(secs)
        return None

    def no_delay(self, val=None):
        if val is None:
            return self._no_delay
        self._no_delay = val
        if self._socket_obj._socket is not None:
            self._socket_obj._socket.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_NODELAY, 1 if val else 0
            )
        return None

    def traffic_class(self, val=None):
        if val is None:
            return self._traffic_class
        self._traffic_class = val
        if self._socket_obj._socket is not None:
            try:
                self._socket_obj._socket.setsockopt(
                    socket.IPPROTO_IP, socket.IP_TOS, val
                )
            except:
                pass  # May not be supported on all platforms
        return None

    def broadcast(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        if val is None:
            # Getting only allowed if broadcast was copied from another socket
            if self._broadcast_copied:
                return self._broadcast
            raise UnsupportedErr.make("Broadcast not supported for TCP sockets")
        # Setting always throws - broadcast not supported for TCP
        raise UnsupportedErr.make("Broadcast not supported for TCP sockets")

    def copy_from(self, other):
        """Copy options from another socket options object."""
        # Copy broadcast for storage (even though TCP can't use it)
        if hasattr(other, 'broadcast'):
            try:
                self._broadcast = other.broadcast()
                self._broadcast_copied = True  # Mark that broadcast was copied
            except:
                pass

        # Copy common options that exist on both TcpSocketOptions and UdpSocketOptions
        if hasattr(other, 'receive_buffer_size'):
            try:
                self._receive_buffer_size = other.receive_buffer_size()
            except:
                pass
        if hasattr(other, 'send_buffer_size'):
            try:
                self._send_buffer_size = other.send_buffer_size()
            except:
                pass
        if hasattr(other, 'reuse_addr'):
            try:
                self._reuse_addr = other.reuse_addr()
            except:
                pass
        if hasattr(other, 'traffic_class'):
            try:
                self._traffic_class = other.traffic_class()
            except:
                pass

        # TCP-specific options - only copy if the other object has them
        if hasattr(other, '_in_buffer_size'):
            self._in_buffer_size = other._in_buffer_size
        elif hasattr(other, 'in_buffer_size'):
            try:
                self._in_buffer_size = other.in_buffer_size()
            except:
                pass

        if hasattr(other, '_out_buffer_size'):
            self._out_buffer_size = other._out_buffer_size
        elif hasattr(other, 'out_buffer_size'):
            try:
                self._out_buffer_size = other.out_buffer_size()
            except:
                pass

        if hasattr(other, '_keep_alive'):
            self._keep_alive = other._keep_alive
        elif hasattr(other, 'keep_alive'):
            try:
                self._keep_alive = other.keep_alive()
            except:
                pass

        if hasattr(other, '_linger'):
            self._linger = other._linger
        elif hasattr(other, 'linger'):
            try:
                self._linger = other.linger()
            except:
                pass

        if hasattr(other, '_receive_timeout'):
            self._receive_timeout = other._receive_timeout
        elif hasattr(other, 'receive_timeout'):
            try:
                self._receive_timeout = other.receive_timeout()
            except:
                pass

        if hasattr(other, '_no_delay'):
            self._no_delay = other._no_delay
        elif hasattr(other, 'no_delay'):
            try:
                self._no_delay = other.no_delay()
            except:
                pass

        return self


class TcpSocketInStream(InStream):
    """Input stream wrapper for a TCP socket."""

    def __init__(self, sock):
        super().__init__(None)
        self._socket = sock
        self._file = sock.makefile('rb')
        self._pushback = []  # For unread/peek support

    def read(self):
        """Read a single byte, return as int or None at EOF."""
        # Check pushback first
        if self._pushback:
            return self._pushback.pop()
        b = self._file.read(1)
        if not b:
            return None
        return b[0]

    def peek(self):
        """Peek at next byte without consuming it."""
        if self._pushback:
            return self._pushback[-1]
        b = self._file.read(1)
        if not b:
            return None
        val = b[0]
        self._pushback.append(val)
        return val

    def unread(self, b):
        """Push back a byte to be read again."""
        if b is not None:
            self._pushback.append(int(b))
        return self

    def unread_char(self, c):
        """Push back a character to be read again.

        For ASCII/UTF-8 single-byte chars, this is equivalent to unread.
        """
        if c is not None:
            self._pushback.append(int(c))
        return self

    def read_char(self):
        """Read a single character (byte as int)."""
        # Delegate to read() which handles pushback
        return self.read()

    def read_buf(self, buf, n):
        """Read up to n bytes into buf."""
        data = self._file.read(n)
        if not data:
            return None
        if hasattr(buf, '_data'):
            buf._data.extend(data)
        elif hasattr(buf, 'write_bytes'):
            buf.write_bytes(data)
        else:
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

    def read_line(self, max_len=None):
        """Read a line of text."""
        if max_len:
            line = self._file.readline(max_len)
        else:
            line = self._file.readline()
        if not line:
            return None
        # Strip trailing \r\n or \n
        line = line.decode('utf-8')
        if line.endswith('\r\n'):
            line = line[:-2]
        elif line.endswith('\n'):
            line = line[:-1]
        return line

    def close(self):
        """Close the stream."""
        try:
            self._file.close()
        except:
            pass
        return self


class TcpSocketOutStream(OutStream):
    """Output stream wrapper for a TCP socket."""

    def __init__(self, sock):
        super().__init__(None)
        self._socket = sock
        self._file = sock.makefile('wb')

    def write(self, val):
        """Write a byte."""
        if isinstance(val, int):
            self._file.write(bytes([val]))
        else:
            self._file.write(bytes([int(val)]))
        return self

    def write_buf(self, buf, n=None):
        """Write buffer contents.

        Args:
            buf: Buffer to write from
            n: Number of bytes to write (None = all remaining)
        """
        if hasattr(buf, '_data'):
            size = buf._size if hasattr(buf, '_size') else len(buf._data)
            pos = buf._pos if hasattr(buf, '_pos') else 0
            if n is not None:
                size = min(int(n), size - pos)
            else:
                size = size - pos
            data = bytes(buf._data[pos:pos + size])
        elif hasattr(buf, 'to_bytes'):
            data = buf.to_bytes()
            if n is not None:
                data = data[:int(n)]
        elif hasattr(buf, 'size'):
            count = int(n) if n is not None else buf.size()
            data = bytearray()
            for i in range(count):
                data.append(buf.get(i))
            data = bytes(data)
        else:
            data = bytes(buf) if isinstance(buf, (bytes, bytearray)) else str(buf).encode('utf-8')
            if n is not None:
                data = data[:int(n)]
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
        self._file.write(b'\r\n')
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
