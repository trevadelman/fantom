#
# inet::UdpPacket - Python native implementation
#
# UDP datagram packet representation.
#

from fan.sys.Obj import Obj


class UdpPacket(Obj):
    """UDP packet containing address, port, and data buffer."""

    @staticmethod
    def make(addr=None, port=None, data=None):
        """Create a new UdpPacket."""
        return UdpPacket(addr, port, data)

    def __init__(self, addr=None, port=None, data=None):
        super().__init__()
        self._addr = addr
        self._port = port
        self._data = data

    def addr(self, val=None):
        """Get or set the address."""
        if val is None:
            return self._addr
        self._addr = val
        return None

    def port(self, val=None):
        """Get or set the port."""
        if val is None:
            return self._port
        self._port = val
        return None

    def data(self, val=None):
        """Get or set the data buffer."""
        if val is None:
            return self._data
        self._data = val
        return None

    def to_str(self):
        addr_str = str(self._addr) if self._addr else "null"
        port_str = str(self._port) if self._port else "null"
        return f"UdpPacket({addr_str}:{port_str})"

    def __str__(self):
        return self.to_str()
