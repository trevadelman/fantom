#
# inet::TcpListener - Python native implementation
#
# Server socket that listens for incoming TCP connections.
#

import socket
from fan.sys.Obj import Obj


class TcpListener(Obj):
    """TCP server socket for accepting incoming connections."""

    @staticmethod
    def make(config=None):
        """Create a new TcpListener."""
        return TcpListener(config)

    def __init__(self, config=None):
        super().__init__()
        self._config = config
        self._socket = None
        self._bound = False
        self._closed = False
        self._local_addr = None
        self._local_port = None
        self._options = None
        self._receive_buffer_size = 8192
        self._reuse_addr = False

    def init(self, config):
        """Initialize with config (called by constructor)."""
        self._config = config
        return self

    def config(self):
        """Get the socket configuration."""
        return self._config

    def is_bound(self):
        """Is this socket bound to a local address."""
        return self._bound

    def is_closed(self):
        """Is this socket closed."""
        return self._closed

    def local_addr(self):
        """Get bound local address, or null if not bound."""
        return self._local_addr

    def local_port(self):
        """Get bound local port, or null if not bound."""
        return self._local_port

    def bind(self, addr, port, backlog=50):
        """Bind to local address and port.

        Args:
            addr: IpAddr to bind to, or null for any
            port: Port number, or null for ephemeral
            backlog: Listen backlog (default 50)

        Returns:
            This listener
        """
        from fan.sys.IOErr import IOErr
        from fan.inet.IpAddr import IpAddr

        if self._closed:
            raise IOErr.make("Listener is closed")

        # Create socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Apply options before bind
        if self._reuse_addr:
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
            self._socket.listen(backlog)
            self._bound = True

            # Get actual address/port
            actual_addr, actual_port = self._socket.getsockname()
            self._local_addr = IpAddr(actual_addr) if actual_addr else None
            self._local_port = actual_port

        except socket.error as e:
            raise IOErr.make(f"Bind failed: {e}")

        return self

    def accept(self):
        """Accept next incoming connection (blocking)."""
        return self.do_accept()

    def do_accept(self):
        """Internal accept implementation."""
        from fan.sys.IOErr import IOErr
        from fan.inet.IpAddr import IpAddr
        from fan.inet.TcpSocket import TcpSocket, TcpSocketInStream, TcpSocketOutStream

        if not self._bound or self._closed:
            raise IOErr.make("Listener not bound or closed")

        try:
            client_socket, client_addr = self._socket.accept()

            # Create TcpSocket wrapper
            tcp = TcpSocket()
            tcp._socket = client_socket
            tcp._bound = True
            tcp._connected = True
            tcp._closed = False

            # Set addresses
            local = client_socket.getsockname()
            tcp._local_addr = IpAddr(local[0]) if local[0] else None
            tcp._local_port = local[1]
            tcp._remote_addr = IpAddr(client_addr[0])
            tcp._remote_port = client_addr[1]

            # Create streams
            tcp._in = TcpSocketInStream(client_socket)
            tcp._out = TcpSocketOutStream(client_socket)

            return tcp

        except socket.timeout:
            raise IOErr.make("Accept timed out")
        except socket.error as e:
            raise IOErr.make(f"Accept failed: {e}")

    def close(self):
        """Close this listener."""
        if self._socket is not None:
            try:
                self._socket.close()
            except:
                pass
        self._closed = True
        return True

    def options(self):
        """Get socket options."""
        if self._options is None:
            self._options = TcpListenerOptions(self)
        return self._options

    # Internal option accessors
    def get_receive_buffer_size(self):
        return self._receive_buffer_size

    def set_receive_buffer_size(self, v):
        self._receive_buffer_size = v
        if self._socket is not None:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, v)

    def get_reuse_addr(self):
        return self._reuse_addr

    def set_reuse_addr(self, v):
        self._reuse_addr = v
        if self._socket is not None:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 if v else 0)


class TcpListenerOptions(Obj):
    """Socket options for TcpListener."""

    def __init__(self, listener):
        super().__init__()
        self._listener = listener

    def receive_buffer_size(self, val=None):
        if val is None:
            return self._listener.get_receive_buffer_size()
        self._listener.set_receive_buffer_size(val)
        return None

    def reuse_addr(self, val=None):
        if val is None:
            return self._listener.get_reuse_addr()
        self._listener.set_reuse_addr(val)
        return None

    # Unsupported options throw UnsupportedErr
    def broadcast(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("broadcast not supported for TcpListener")

    def in_buffer_size(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("inBufferSize not supported for TcpListener")

    def out_buffer_size(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("outBufferSize not supported for TcpListener")

    def keep_alive(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("keepAlive not supported for TcpListener")

    def send_buffer_size(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("sendBufferSize not supported for TcpListener")

    def linger(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("linger not supported for TcpListener")

    def no_delay(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("noDelay not supported for TcpListener")

    def traffic_class(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("trafficClass not supported for TcpListener")

    def receive_timeout(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("receiveTimeout not supported for TcpListener")
