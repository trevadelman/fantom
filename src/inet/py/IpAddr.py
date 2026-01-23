#
# inet::IpAddr - Python native implementation
#
# IP address representation. Minimal implementation needed for WebClient.
#

import socket
from fan.sys.Obj import Obj


class IpAddr(Obj):
    """IP address representation.

    This is a minimal Python-native implementation that wraps hostname/IP
    for use by WebClient. Since we use Python's requests library, most
    DNS resolution is handled automatically - this class just holds the
    hostname string.
    """

    @staticmethod
    def make(host):
        """Create an IpAddr from a hostname or IP string."""
        return IpAddr(host)

    @staticmethod
    def local():
        """Get the local host address."""
        return IpAddr(socket.gethostname())

    def __init__(self, host):
        super().__init__()
        if isinstance(host, str):
            self._host = host
        elif hasattr(host, 'to_str'):
            self._host = host.to_str()
        else:
            self._host = str(host)

    def host(self):
        """Get the hostname string."""
        return self._host

    def numeric(self):
        """Get the numeric IP address string.

        Attempts DNS resolution. Returns the IP as a string.
        """
        try:
            return socket.gethostbyname(self._host)
        except socket.gaierror:
            return self._host

    def is_ipv4(self):
        """Check if this is an IPv4 address."""
        try:
            socket.inet_aton(self._host)
            return True
        except socket.error:
            return False

    def is_ipv6(self):
        """Check if this is an IPv6 address."""
        try:
            socket.inet_pton(socket.AF_INET6, self._host)
            return True
        except socket.error:
            return False

    def to_str(self):
        return self._host

    def __str__(self):
        return self._host

    def __eq__(self, other):
        if isinstance(other, IpAddr):
            return self._host == other._host
        return False

    def __hash__(self):
        return hash(self._host)
