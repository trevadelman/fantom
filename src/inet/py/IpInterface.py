#
# inet::IpInterface - Python native implementation
#
# Network interface enumeration using Python's netifaces or psutil library.
#

import socket
from fan.sys.Obj import Obj


class IpInterface(Obj):
    """Network interface representation.

    Uses Python's socket module and platform APIs to enumerate
    network interfaces and their addresses.
    """

    _interfaces_cache = None

    @staticmethod
    def list_():
        """List all network interfaces on this machine."""
        from fan.sys.List import List

        interfaces = IpInterface._enumerate_interfaces()
        return List.from_list(interfaces, "inet::IpInterface")

    # Alias for direct Python usage
    @staticmethod
    def list():
        return IpInterface.list_()

    @staticmethod
    def find_by_addr(addr, checked=True):
        """Find interface bound to the given IP address."""
        from fan.sys.UnresolvedErr import UnresolvedErr

        # Get target address string and its numeric form
        if hasattr(addr, '_host'):
            target = addr._host
        elif hasattr(addr, 'numeric'):
            target = addr.numeric()
        else:
            target = str(addr)

        # Also get numeric representation for hostname resolution
        target_numeric = None
        if hasattr(addr, 'numeric'):
            try:
                target_numeric = addr.numeric()
            except:
                pass
        else:
            import socket
            try:
                target_numeric = socket.gethostbyname(target)
            except:
                pass

        # Search interfaces
        for iface in IpInterface._enumerate_interfaces():
            for ip in iface._addrs:
                # Direct match
                if ip._host == target:
                    return iface
                # Numeric match
                if target_numeric and ip._host == target_numeric:
                    return iface
                # Try numeric comparison
                try:
                    if ip.numeric() == target_numeric:
                        return iface
                except:
                    pass

        if checked:
            raise UnresolvedErr.make(f"No interface for address: {target}")
        return None

    @staticmethod
    def find_by_name(name, checked=True):
        """Find interface by name."""
        from fan.sys.UnresolvedErr import UnresolvedErr

        for iface in IpInterface._enumerate_interfaces():
            if iface._name == name:
                return iface

        if checked:
            raise UnresolvedErr.make(f"Unknown interface: {name}")
        return None

    @staticmethod
    def _enumerate_interfaces():
        """Enumerate all network interfaces using platform-specific APIs."""
        from fan.inet.IpAddr import IpAddr

        interfaces = []

        try:
            # Try using netifaces if available
            import netifaces
            for name in netifaces.interfaces():
                iface = IpInterface()
                iface._name = name
                iface._dis = name
                iface._addrs = []
                iface._broadcast_addrs = []

                addrs = netifaces.ifaddresses(name)

                # Get IPv4 addresses
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        if 'addr' in addr_info:
                            iface._addrs.append(IpAddr(addr_info['addr']))
                        if 'broadcast' in addr_info:
                            iface._broadcast_addrs.append(IpAddr(addr_info['broadcast']))

                # Get IPv6 addresses
                if netifaces.AF_INET6 in addrs:
                    for addr_info in addrs[netifaces.AF_INET6]:
                        if 'addr' in addr_info:
                            # Remove zone ID suffix (%en0 etc)
                            addr = addr_info['addr'].split('%')[0]
                            iface._addrs.append(IpAddr(addr))

                interfaces.append(iface)
        except ImportError:
            # Fallback: create basic interface info from socket
            iface = IpInterface()
            iface._name = "lo0"
            iface._dis = "Loopback"
            iface._addrs = [IpAddr("127.0.0.1")]
            iface._broadcast_addrs = []
            iface._is_loopback = True
            interfaces.append(iface)

            # Try to get hostname-based interface
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                if ip != "127.0.0.1":
                    iface2 = IpInterface()
                    iface2._name = "en0"
                    iface2._dis = "Primary"
                    iface2._addrs = [IpAddr(ip)]
                    iface2._broadcast_addrs = []
                    interfaces.append(iface2)
            except:
                pass

        return interfaces

    def __init__(self):
        super().__init__()
        self._name = ""
        self._dis = ""
        self._addrs = []
        self._broadcast_addrs = []
        self._is_up = True
        self._hardware_addr = None
        self._mtu = 1500
        self._supports_multicast = True
        self._is_point_to_point = False
        self._is_loopback = False

    def name(self):
        """Name of the interface."""
        return self._name

    def dis(self):
        """Display name of the interface."""
        return self._dis

    def addrs(self):
        """List of IP addresses bound to this interface."""
        from fan.sys.List import List
        return List.from_list(self._addrs, "inet::IpAddr")

    def broadcast_addrs(self):
        """List of broadcast IP addresses."""
        from fan.sys.List import List
        return List.from_list(self._broadcast_addrs, "inet::IpAddr")

    def prefix_size(self, addr):
        """Network prefix length (subnet mask bits)."""
        # Default to common values
        if hasattr(addr, 'is_i_pv4') and addr.is_i_pv4():
            return 24  # Common /24 network
        return 64  # Common IPv6 prefix

    def is_up(self):
        """True if interface is up and running."""
        return self._is_up

    def hardware_addr(self):
        """MAC address as Buf, or null if not available."""
        return self._hardware_addr

    def mtu(self):
        """Maximum transmission unit."""
        return self._mtu

    def supports_multicast(self):
        """True if interface supports multicast."""
        return self._supports_multicast

    def is_point_to_point(self):
        """True if point-to-point interface."""
        return self._is_point_to_point

    def is_loopback(self):
        """True if loopback interface."""
        return self._is_loopback or self._name in ("lo", "lo0", "Loopback")

    def hash_(self):
        """Hash code."""
        return hash((self._name, tuple(a._host for a in self._addrs)))

    def __hash__(self):
        return self.hash_()

    def __eq__(self, other):
        if isinstance(other, IpInterface):
            return self._name == other._name
        return False

    def to_str(self):
        addrs_str = ", ".join(a._host for a in self._addrs)
        return f"{self._name} [{addrs_str}]"

    def __str__(self):
        return self.to_str()
