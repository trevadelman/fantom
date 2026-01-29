#
# inet::MulticastSocket - Python native implementation
#
# UDP multicast socket support.
#

import socket
import struct
from fan.sys.Obj import Obj
from fan.inet.UdpSocket import UdpSocket


class MulticastSocket(UdpSocket):
    """Multicast UDP socket extending UdpSocket."""

    @staticmethod
    def make(config=None):
        """Create a new MulticastSocket."""
        return MulticastSocket(config)

    def __init__(self, config=None):
        super().__init__(config)
        self._interface_val = None
        self._time_to_live_val = 1
        self._loopback_mode_val = True

    def get_interface(self):
        """Get default network interface."""
        return self._interface_val

    def set_interface(self, val):
        """Set default network interface."""
        self._interface_val = val

    def interface(self, val=None):
        """Get or set default network interface."""
        if val is None:
            # Return default interface if not set
            if self._interface_val is None:
                from fan.inet.IpInterface import IpInterface
                interfaces = IpInterface.list_()
                if interfaces.size > 0:
                    # Return first non-loopback interface, or first interface
                    for i in range(interfaces.size):
                        iface = interfaces[i]
                        if not iface.is_loopback():
                            return iface
                    return interfaces[0]
            return self._interface_val
        self._interface_val = val
        return None

    def time_to_live(self, val=None):
        """Get or set TTL (0-255)."""
        if val is None:
            return self._time_to_live_val
        self._time_to_live_val = val
        if self._socket:
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, val)
        return None

    def loopback_mode(self, val=None):
        """Get or set loopback mode."""
        if val is None:
            return self._loopback_mode_val
        self._loopback_mode_val = val
        if self._socket:
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1 if val else 0)
        return None

    def join_group(self, addr, port=None, interface=None):
        """Join a multicast group."""
        from fan.sys.IOErr import IOErr

        # Create socket if needed
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._apply_options()

        # Get multicast address
        if hasattr(addr, 'numeric'):
            mcast_addr = addr.numeric()
        elif hasattr(addr, '_host'):
            mcast_addr = addr._host
        else:
            mcast_addr = str(addr)

        # Determine interface address
        if interface is not None:
            iface_addrs = interface.addrs()
            if iface_addrs.size > 0:
                iface_addr = iface_addrs[0].numeric()
            else:
                iface_addr = '0.0.0.0'
        elif self._interface is not None:
            iface_addrs = self._interface.addrs()
            if iface_addrs.size > 0:
                iface_addr = iface_addrs[0].numeric()
            else:
                iface_addr = '0.0.0.0'
        else:
            iface_addr = '0.0.0.0'

        try:
            # Create membership request
            mreq = struct.pack('4s4s',
                               socket.inet_aton(mcast_addr),
                               socket.inet_aton(iface_addr))
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except socket.error as e:
            raise IOErr.make(f"Failed to join multicast group: {e}")

        return self

    def leave_group(self, addr, port=None, interface=None):
        """Leave a multicast group."""
        from fan.sys.IOErr import IOErr

        if self._socket is None:
            return self

        # Get multicast address
        if hasattr(addr, 'numeric'):
            mcast_addr = addr.numeric()
        elif hasattr(addr, '_host'):
            mcast_addr = addr._host
        else:
            mcast_addr = str(addr)

        # Determine interface address
        if interface is not None:
            iface_addrs = interface.addrs()
            if iface_addrs.size > 0:
                iface_addr = iface_addrs[0].numeric()
            else:
                iface_addr = '0.0.0.0'
        elif self._interface is not None:
            iface_addrs = self._interface.addrs()
            if iface_addrs.size > 0:
                iface_addr = iface_addrs[0].numeric()
            else:
                iface_addr = '0.0.0.0'
        else:
            iface_addr = '0.0.0.0'

        try:
            # Create membership request
            mreq = struct.pack('4s4s',
                               socket.inet_aton(mcast_addr),
                               socket.inet_aton(iface_addr))
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
        except socket.error as e:
            raise IOErr.make(f"Failed to leave multicast group: {e}")

        return self
