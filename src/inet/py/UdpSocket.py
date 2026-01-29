#
# inet::UdpSocket - Python native implementation
#
# UDP datagram socket support.
#

import socket
from fan.sys.Obj import Obj


class UdpSocket(Obj):
    """UDP socket for datagram communication."""

    @staticmethod
    def make(config=None):
        """Create a new UdpSocket."""
        return UdpSocket(config)

    def __init__(self, config=None):
        super().__init__()
        self._config = config
        self._socket = None
        self._bound = False
        self._connected = False
        self._closed = False
        self._local_addr = None
        self._local_port = None
        self._remote_addr = None
        self._remote_port = None
        self._options = None
        # Option values
        self._broadcast = False
        self._receive_buffer_size = 8192
        self._send_buffer_size = 8192
        self._reuse_addr = False
        self._receive_timeout = None
        self._traffic_class = 0

    def init(self, config):
        """Initialize with config."""
        self._config = config
        return self

    def config(self):
        return self._config

    def is_bound(self):
        return self._bound

    def is_connected(self):
        return self._connected

    def is_closed(self):
        return self._closed

    def local_addr(self):
        return self._local_addr

    def local_port(self):
        return self._local_port

    def remote_addr(self):
        return self._remote_addr

    def remote_port(self):
        return self._remote_port

    def bind(self, addr, port):
        """Bind to local address and port."""
        from fan.sys.IOErr import IOErr
        from fan.inet.IpAddr import IpAddr

        if self._closed:
            raise IOErr.make("Socket is closed")

        # Create socket if needed
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._apply_options()

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

        bind_port = int(port) if port is not None else 0

        try:
            self._socket.bind((bind_addr, bind_port))
            self._bound = True

            actual_addr, actual_port = self._socket.getsockname()
            self._local_addr = IpAddr(actual_addr) if actual_addr else None
            self._local_port = actual_port

        except socket.error as e:
            raise IOErr.make(f"Bind failed: {e}")

        return self

    def connect(self, addr, port):
        """Connect to remote address (for send/receive without specifying address)."""
        from fan.sys.IOErr import IOErr
        from fan.inet.IpAddr import IpAddr

        if self._closed:
            raise IOErr.make("Socket is closed")

        # Create socket if needed
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._apply_options()

        # Get hostname
        if hasattr(addr, 'numeric'):
            hostname = addr.numeric()
        elif hasattr(addr, '_host'):
            hostname = addr._host
        else:
            hostname = str(addr)

        try:
            self._socket.connect((hostname, int(port)))
            self._connected = True
            self._bound = True

            # Store remote info
            self._remote_addr = addr if isinstance(addr, IpAddr) else IpAddr(str(addr))
            self._remote_port = int(port)

            # Get local info
            local = self._socket.getsockname()
            self._local_addr = IpAddr(local[0]) if local[0] else None
            self._local_port = local[1]

        except socket.error as e:
            raise IOErr.make(f"Connect failed: {e}")

        return self

    def send(self, packet):
        """Send a UDP packet."""
        from fan.sys.IOErr import IOErr
        from fan.sys.ArgErr import ArgErr

        if self._closed:
            raise IOErr.make("Socket is closed")

        # Get packet data
        buf = packet.data()

        # Extract bytes from Buf - use remaining() to get bytes from pos to size
        if hasattr(buf, '_data'):
            pos = buf._pos if hasattr(buf, '_pos') else 0
            size = buf._size if hasattr(buf, '_size') else len(buf._data)
            data = bytes(buf._data[pos:size])
        elif hasattr(buf, 'remaining'):
            # Use the remaining bytes (pos to size)
            remaining = buf.remaining()
            data_list = []
            for _ in range(remaining):
                b = buf.read()
                if b is not None:
                    data_list.append(b)
            data = bytes(data_list)
        else:
            # Fallback
            data = b''

        # Determine destination
        addr = packet.addr()
        port = packet.port()

        if self._connected:
            # When connected, addr/port must be null
            if addr is not None:
                raise ArgErr.make("addr must be null when connected")
            if port is not None:
                raise ArgErr.make("port must be null when connected")
            try:
                self._socket.send(data)
            except socket.error as e:
                raise IOErr.make(f"Send failed: {e}")
        else:
            # When not connected, addr/port cannot be null
            if addr is None:
                raise ArgErr.make("addr cannot be null when not connected")
            if port is None:
                raise ArgErr.make("port cannot be null when not connected")

            # Get destination address
            if hasattr(addr, 'numeric'):
                dest_addr = addr.numeric()
            elif hasattr(addr, '_host'):
                dest_addr = addr._host
            else:
                dest_addr = str(addr)

            try:
                self._socket.sendto(data, (dest_addr, int(port)))
            except socket.error as e:
                raise IOErr.make(f"Send failed: {e}")

    def receive(self, packet=None):
        """Receive a UDP packet."""
        from fan.sys.IOErr import IOErr
        from fan.sys.Buf import Buf
        from fan.inet.IpAddr import IpAddr
        from fan.inet.UdpPacket import UdpPacket

        if self._closed:
            raise IOErr.make("Socket is closed")

        # Create default packet if none provided
        if packet is None:
            packet = UdpPacket.make(None, None, Buf.make(1024))

        # Get buffer
        buf = packet.data()

        # Determine receive size
        if hasattr(buf, 'capacity'):
            capacity = buf.capacity()
        elif hasattr(buf, '_capacity'):
            capacity = buf._capacity
        else:
            capacity = 1024

        # Account for current position
        pos = buf._pos if hasattr(buf, '_pos') else 0
        recv_size = capacity - pos

        try:
            data, sender = self._socket.recvfrom(recv_size)

            # Write data to buffer at current position
            if hasattr(buf, '_data'):
                for i, b in enumerate(data):
                    if pos + i < len(buf._data):
                        buf._data[pos + i] = b
                    else:
                        buf._data.append(b)
                buf._size = pos + len(data)
                buf._pos = buf._size
            else:
                for b in data:
                    buf.write(b)

            # Update packet with sender info
            packet._addr = IpAddr(sender[0])
            packet._port = sender[1]

            return packet

        except socket.timeout:
            raise IOErr.make("Receive timed out")
        except socket.error as e:
            raise IOErr.make(f"Receive failed: {e}")

    def disconnect(self):
        """Disconnect from remote address."""
        if self._socket is not None and self._connected:
            try:
                # Disconnect by connecting to AF_UNSPEC
                self._socket.connect(('', 0))
            except:
                pass
        self._connected = False
        self._remote_addr = None
        self._remote_port = None
        return self

    def close(self):
        """Close this socket."""
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
            self._options = UdpSocketOptions(self)
        return self._options

    def _apply_options(self):
        """Apply current options to socket."""
        if self._socket is None:
            return
        if self._broadcast:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self._receive_buffer_size)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self._send_buffer_size)
        if self._reuse_addr:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self._receive_timeout is not None:
            secs = self._receive_timeout.to_sec() if hasattr(self._receive_timeout, 'to_sec') else 60
            self._socket.settimeout(secs)

    # Internal option accessors
    def get_broadcast(self):
        return self._broadcast

    def set_broadcast(self, v):
        self._broadcast = v
        if self._socket:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1 if v else 0)

    def get_receive_buffer_size(self):
        return self._receive_buffer_size

    def set_receive_buffer_size(self, v):
        self._receive_buffer_size = v
        if self._socket:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, v)

    def get_send_buffer_size(self):
        return self._send_buffer_size

    def set_send_buffer_size(self, v):
        self._send_buffer_size = v
        if self._socket:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, v)

    def get_reuse_addr(self):
        return self._reuse_addr

    def set_reuse_addr(self, v):
        self._reuse_addr = v
        if self._socket:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 if v else 0)

    def get_receive_timeout(self):
        return self._receive_timeout

    def set_receive_timeout(self, v):
        self._receive_timeout = v
        if self._socket:
            if v is None:
                self._socket.settimeout(None)
            else:
                secs = v.to_sec() if hasattr(v, 'to_sec') else 60
                self._socket.settimeout(secs)

    def get_traffic_class(self):
        return self._traffic_class

    def set_traffic_class(self, v):
        self._traffic_class = v
        if self._socket:
            try:
                self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, v)
            except:
                pass


# Sentinel for distinguishing no argument from None argument
_UNSET = object()


class UdpSocketOptions(Obj):
    """Socket options for UdpSocket."""

    def __init__(self, sock):
        super().__init__()
        self._socket = sock

    def broadcast(self, val=None):
        if val is None:
            return self._socket.get_broadcast()
        self._socket.set_broadcast(val)
        return None

    def receive_buffer_size(self, val=None):
        if val is None:
            return self._socket.get_receive_buffer_size()
        self._socket.set_receive_buffer_size(val)
        return None

    def send_buffer_size(self, val=None):
        if val is None:
            return self._socket.get_send_buffer_size()
        self._socket.set_send_buffer_size(val)
        return None

    def reuse_addr(self, val=None):
        if val is None:
            return self._socket.get_reuse_addr()
        self._socket.set_reuse_addr(val)
        return None

    def receive_timeout(self, val=_UNSET):
        if val is _UNSET:
            return self._socket.get_receive_timeout()
        self._socket.set_receive_timeout(val)
        return None

    def traffic_class(self, val=None):
        if val is None:
            return self._socket.get_traffic_class()
        self._socket.set_traffic_class(val)
        return None

    # Unsupported options
    def in_buffer_size(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("inBufferSize not supported for UdpSocket")

    def out_buffer_size(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("outBufferSize not supported for UdpSocket")

    def keep_alive(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("keepAlive not supported for UdpSocket")

    def linger(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("linger not supported for UdpSocket")

    def no_delay(self, val=None):
        from fan.sys.UnsupportedErr import UnsupportedErr
        raise UnsupportedErr.make("noDelay not supported for UdpSocket")

    def copy_from(self, other):
        """Copy options from another socket options object."""
        # Copy common options that may exist on the other object
        if hasattr(other, 'broadcast'):
            try:
                val = other.broadcast()
                self._socket.set_broadcast(val if val is not None else False)
            except:
                pass
        elif hasattr(other, '_socket') and hasattr(other._socket, 'get_broadcast'):
            try:
                self._socket.set_broadcast(other._socket.get_broadcast())
            except:
                pass

        if hasattr(other, 'receive_buffer_size'):
            try:
                val = other.receive_buffer_size()
                if val is not None:
                    self._socket.set_receive_buffer_size(val)
            except:
                pass
        elif hasattr(other, '_socket') and hasattr(other._socket, 'get_receive_buffer_size'):
            try:
                self._socket.set_receive_buffer_size(other._socket.get_receive_buffer_size())
            except:
                pass

        if hasattr(other, 'send_buffer_size'):
            try:
                val = other.send_buffer_size()
                if val is not None:
                    self._socket.set_send_buffer_size(val)
            except:
                pass
        elif hasattr(other, '_socket') and hasattr(other._socket, 'get_send_buffer_size'):
            try:
                self._socket.set_send_buffer_size(other._socket.get_send_buffer_size())
            except:
                pass

        if hasattr(other, 'reuse_addr'):
            try:
                val = other.reuse_addr()
                self._socket.set_reuse_addr(val if val is not None else False)
            except:
                pass
        elif hasattr(other, '_socket') and hasattr(other._socket, 'get_reuse_addr'):
            try:
                self._socket.set_reuse_addr(other._socket.get_reuse_addr())
            except:
                pass

        if hasattr(other, 'receive_timeout'):
            try:
                self._socket.set_receive_timeout(other.receive_timeout())
            except:
                pass
        elif hasattr(other, '_socket') and hasattr(other._socket, 'get_receive_timeout'):
            try:
                self._socket.set_receive_timeout(other._socket.get_receive_timeout())
            except:
                pass

        if hasattr(other, 'traffic_class'):
            try:
                val = other.traffic_class()
                if val is not None:
                    self._socket.set_traffic_class(val)
            except:
                pass

        return self
