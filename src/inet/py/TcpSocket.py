#
# inet::TcpSocket - Python native stub
#
# TcpSocket is not fully implemented because WebClient uses Python's
# requests library directly, which handles sockets internally.
#
# This stub exists so that transpiled code can import the type.
#

from fan.sys.Obj import Obj


class TcpSocket(Obj):
    """TCP socket stub.

    WebClient uses Python's requests library instead of raw sockets,
    so this class is a stub. If you need raw socket access, use
    Python's socket module directly.
    """

    @staticmethod
    def make(config=None):
        """Create a TcpSocket (stub - not fully implemented)."""
        return TcpSocket(config)

    def __init__(self, config=None):
        super().__init__()
        self._config = config
        self._connected = False
        self._closed = False

    def config(self):
        return self._config

    def is_bound(self):
        return False

    def is_connected(self):
        return self._connected

    def is_closed(self):
        return self._closed

    def connect(self, addr, port, timeout=None):
        raise NotImplementedError(
            "TcpSocket.connect() is not implemented. "
            "Use WebClient for HTTP requests, which uses Python's requests library."
        )

    def close(self):
        self._closed = True
        self._connected = False
        return True

    def in_(self):
        raise NotImplementedError("TcpSocket.in_() not implemented")

    def out(self):
        raise NotImplementedError("TcpSocket.out() not implemented")
