#
# inet::IpAddr - Python native implementation
#
# IP address representation for network operations.
#

import socket
import struct
from fan.sys.Obj import Obj


class IpAddr(Obj):
    """IP address representation.

    Supports both IPv4 and IPv6 addresses with numeric representation,
    byte conversion, and DNS resolution.
    """

    _local_instance = None

    @staticmethod
    def make(host):
        """Create an IpAddr from a hostname or IP string."""
        from fan.inet.UnknownHostErr import UnknownHostErr

        if isinstance(host, str):
            host_str = host
        elif hasattr(host, 'to_str'):
            host_str = host.to_str()
        else:
            host_str = str(host)

        # Validate the address - check for invalid IPv6 format
        if ':' in host_str:
            # IPv6 address - validate
            try:
                socket.inet_pton(socket.AF_INET6, host_str)
            except socket.error:
                # Invalid IPv6 format
                raise UnknownHostErr.make(f"Unknown host: {host_str}")

        return IpAddr(host_str)

    @staticmethod
    def local():
        """Get the local host address (singleton)."""
        if IpAddr._local_instance is None:
            IpAddr._local_instance = IpAddr(socket.gethostname())
        return IpAddr._local_instance

    @staticmethod
    def make_all(host):
        """Get all IP addresses for a hostname.

        Returns a List of IpAddr for all resolved addresses.
        """
        from fan.sys.List import List
        try:
            # For numeric IPs, just return a single-element list
            if IpAddr._is_numeric_ip(host):
                return List.from_list([IpAddr(host)], "inet::IpAddr")

            # DNS lookup - get all addresses
            infos = socket.getaddrinfo(host, None)
            addrs = []
            seen = set()
            for info in infos:
                addr = info[4][0]
                if addr not in seen:
                    seen.add(addr)
                    ip = IpAddr(addr)
                    ip._hostname = host  # Preserve original hostname
                    addrs.append(ip)

            if not addrs:
                addrs.append(IpAddr(host))

            return List.from_list(addrs, "inet::IpAddr")
        except socket.gaierror:
            # Return single entry with original hostname
            return List.from_list([IpAddr(host)], "inet::IpAddr")

    @staticmethod
    def make_bytes(buf):
        """Create an IpAddr from a Buf of raw bytes.

        4 bytes = IPv4, 16 bytes = IPv6.
        """
        # Read bytes from buf
        buf.seek(0)
        data = []
        while True:
            b = buf.read()
            if b is None:
                break
            data.append(b)

        if len(data) == 4:
            # IPv4
            addr_str = ".".join(str(b) for b in data)
            ip = IpAddr(addr_str)
            ip._raw_bytes = bytes(data)
            return ip
        elif len(data) == 16:
            # IPv6 - convert to standard notation
            parts = []
            for i in range(0, 16, 2):
                val = (data[i] << 8) | data[i + 1]
                parts.append(format(val, 'x'))
            addr_str = ":".join(parts)
            ip = IpAddr(addr_str)
            ip._raw_bytes = bytes(data)
            return ip
        else:
            raise ValueError(f"Invalid byte length for IP address: {len(data)}")

    @staticmethod
    def _is_numeric_ip(host):
        """Check if host is a numeric IP (v4 or v6)."""
        try:
            socket.inet_aton(host)
            return True
        except socket.error:
            pass
        try:
            socket.inet_pton(socket.AF_INET6, host)
            return True
        except socket.error:
            pass
        return False

    def __init__(self, host):
        super().__init__()
        self._host = host
        self._hostname = None  # Original hostname if resolved
        self._raw_bytes = None  # Cached raw bytes

    def host(self):
        """Get the hostname string."""
        return self._host

    def hostname(self):
        """Get the original hostname (or IP string if made from IP)."""
        return self._hostname if self._hostname else self._host

    def numeric(self):
        """Get the numeric IP address string.

        For IPv4: returns dotted decimal (e.g., "192.168.1.1")
        For IPv6: returns full hex notation (e.g., "fe80:0:0:0:0:0:0:1")
        """
        # If already numeric, return as-is
        if self._is_numeric_ip(self._host):
            # Normalize IPv6 addresses
            try:
                socket.inet_pton(socket.AF_INET6, self._host)
                # Parse and reformat to full notation
                return self._normalize_ipv6(self._host)
            except socket.error:
                return self._host

        # DNS resolution needed
        try:
            return socket.gethostbyname(self._host)
        except socket.gaierror:
            return self._host

    def _normalize_ipv6(self, addr):
        """Normalize IPv6 address to full notation."""
        try:
            # Use socket to parse and normalize
            packed = socket.inet_pton(socket.AF_INET6, addr)
            parts = []
            for i in range(0, 16, 2):
                val = (packed[i] << 8) | packed[i + 1]
                parts.append(format(val, 'x'))
            return ":".join(parts)
        except:
            return addr

    def bytes(self):
        """Get the raw bytes of this IP address as a Buf.

        Returns 4 bytes for IPv4, 16 bytes for IPv6.
        """
        from fan.sys.Buf import Buf

        if self._raw_bytes is not None:
            buf = Buf.make(len(self._raw_bytes))
            for b in self._raw_bytes:
                buf.write(b)
            buf.seek(0)
            return buf

        # Try IPv4 first
        try:
            packed = socket.inet_aton(self._host)
            buf = Buf.make(4)
            for b in packed:
                buf.write(b)
            buf.seek(0)
            self._raw_bytes = packed
            return buf
        except socket.error:
            pass

        # Try IPv6
        try:
            packed = socket.inet_pton(socket.AF_INET6, self._host)
            buf = Buf.make(16)
            for b in packed:
                buf.write(b)
            buf.seek(0)
            self._raw_bytes = packed
            return buf
        except socket.error:
            pass

        # Resolve hostname and get bytes
        try:
            numeric = socket.gethostbyname(self._host)
            packed = socket.inet_aton(numeric)
            buf = Buf.make(4)
            for b in packed:
                buf.write(b)
            buf.seek(0)
            self._raw_bytes = packed
            return buf
        except socket.error:
            # Return empty buf if can't resolve
            return Buf.make(0)

    def is_i_pv4(self):
        """Check if this is an IPv4 address.

        Note: Method name follows transpiler snake_case convention (isIPv4 -> is_i_pv4).
        """
        try:
            socket.inet_aton(self._host)
            return True
        except socket.error:
            pass

        # Check if hostname resolves to IPv4
        try:
            numeric = socket.gethostbyname(self._host)
            socket.inet_aton(numeric)
            return True
        except socket.error:
            return False

    def is_i_pv6(self):
        """Check if this is an IPv6 address.

        Note: Method name follows transpiler snake_case convention (isIPv6 -> is_i_pv6).
        """
        try:
            socket.inet_pton(socket.AF_INET6, self._host)
            return True
        except socket.error:
            return False

    # Keep aliases for backward compatibility and direct Python use
    def is_ipv4(self):
        return self.is_i_pv4()

    def is_ipv6(self):
        return self.is_i_pv6()

    def to_str(self):
        return self._host

    def __str__(self):
        return self._host

    def hash_(self):
        """Return hash code (snake_case for transpiler compatibility)."""
        # Use numeric representation for consistent hashing
        try:
            return hash(self.numeric().lower())
        except:
            return hash(self._host.lower())

    def equals(self, other):
        """Fantom-style equals method for ObjUtil comparison."""
        if other is None:
            return False
        if isinstance(other, IpAddr):
            # First try direct string comparison (case-insensitive)
            if self._host.lower() == other._host.lower():
                return True

            # Try comparing numeric representations (handles hostname vs IP, IPv6 formats)
            try:
                self_numeric = self.numeric()
                other_numeric = other.numeric()
                if self_numeric == other_numeric:
                    return True
            except:
                pass

            # For IPv6, normalize and compare
            if self.is_i_pv6() and other.is_i_pv6():
                try:
                    self_norm = self._normalize_ipv6(self._host)
                    other_norm = other._normalize_ipv6(other._host)
                    return self_norm == other_norm
                except:
                    pass

            return False
        return False

    def __eq__(self, other):
        return self.equals(other)

    def __hash__(self):
        return self.hash_()
