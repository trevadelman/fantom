#
# inet::SocketConfig - Python native implementation
#
# Socket configuration for TCP and UDP sockets.
# All socket types accept a socket configuration for connection setup.
#

from fan.sys.Obj import Obj
from fan.sys.Duration import Duration


class SocketConfig(Obj):
    """Socket configuration for TCP and UDP sockets.

    Configuration options include timeouts, buffer sizes, and TLS settings.
    A system-wide default can be obtained with SocketConfig.cur() and set
    with SocketConfig.set_cur().
    """

    _cur_instance = None
    _cur_changed = False

    @staticmethod
    def cur():
        """Get the current default socket configuration."""
        if SocketConfig._cur_instance is None:
            SocketConfig._cur_instance = SocketConfig()
        return SocketConfig._cur_instance

    @staticmethod
    def set_cur(config):
        """Set a new default socket configuration.

        This configuration will only apply to new sockets created after
        this is called. This method may only be called once to change
        the default socket configuration.
        """
        if SocketConfig._cur_changed:
            raise Exception("Default socket configuration already set")
        SocketConfig._cur_instance = config
        SocketConfig._cur_changed = True

    @staticmethod
    def make(it_block=None):
        """Create a new SocketConfig with default settings.

        Args:
            it_block: Optional closure to configure the instance
        """
        config = SocketConfig()
        if it_block is not None:
            it_block(config)
        return config

    def __init__(self):
        super().__init__()

        # TLS Configuration
        self._keystore = None       # KeyStore for secure sockets
        self._truststore = None     # KeyStore for trusted certificates
        self._tls_params = {}       # TLS parameters map

        # Buffer Configuration
        self._in_buffer_size = 4096
        self._out_buffer_size = 4096

        # Socket Options
        self._keep_alive = False
        self._receive_buffer_size = 65536
        self._send_buffer_size = 65536
        self._reuse_addr = False
        self._linger = None

        # Timeouts
        self._connect_timeout = Duration.make(60_000_000_000)  # 60sec
        self._receive_timeout = Duration.make(60_000_000_000)  # 60sec
        self._accept_timeout = None  # infinite

        # TCP Options
        self._no_delay = True
        self._traffic_class = 0

        # UDP Options
        self._broadcast = False

    def copy(self, it_block=None):
        """Create a copy of this configuration, optionally modified.

        Args:
            it_block: Optional closure to modify the copy
        """
        config = SocketConfig()

        # Copy TLS config
        config._keystore = self._keystore
        config._truststore = self._truststore
        config._tls_params = dict(self._tls_params) if self._tls_params else {}

        # Copy buffer config
        config._in_buffer_size = self._in_buffer_size
        config._out_buffer_size = self._out_buffer_size

        # Copy socket options
        config._keep_alive = self._keep_alive
        config._receive_buffer_size = self._receive_buffer_size
        config._send_buffer_size = self._send_buffer_size
        config._reuse_addr = self._reuse_addr
        config._linger = self._linger

        # Copy timeouts
        config._connect_timeout = self._connect_timeout
        config._receive_timeout = self._receive_timeout
        config._accept_timeout = self._accept_timeout

        # Copy TCP options
        config._no_delay = self._no_delay
        config._traffic_class = self._traffic_class

        # Copy UDP options
        config._broadcast = self._broadcast

        if it_block is not None:
            it_block(config)
        return config

    def set_timeouts(self, connect_timeout, receive_timeout=None):
        """Convenience to create a copy with specified timeouts.

        Args:
            connect_timeout: Connect timeout Duration (or None for infinite)
            receive_timeout: Receive timeout Duration (defaults to connect_timeout)
        """
        if receive_timeout is None:
            receive_timeout = connect_timeout

        def configure(it):
            it._connect_timeout = connect_timeout
            it._receive_timeout = receive_timeout

        return self.copy(configure)

    # TLS Config Accessors
    def keystore(self, val=None):
        if val is None:
            return self._keystore
        self._keystore = val
        return self

    def truststore(self, val=None):
        if val is None:
            return self._truststore
        self._truststore = val
        return self

    def tls_params(self, val=None):
        if val is None:
            return self._tls_params
        self._tls_params = val
        return self

    # Buffer Accessors
    def in_buffer_size(self, val=None):
        if val is None:
            return self._in_buffer_size
        self._in_buffer_size = val
        return self

    def out_buffer_size(self, val=None):
        if val is None:
            return self._out_buffer_size
        self._out_buffer_size = val
        return self

    # Socket Options Accessors
    def keep_alive(self, val=None):
        if val is None:
            return self._keep_alive
        self._keep_alive = val
        return self

    def receive_buffer_size(self, val=None):
        if val is None:
            return self._receive_buffer_size
        self._receive_buffer_size = val
        return self

    def send_buffer_size(self, val=None):
        if val is None:
            return self._send_buffer_size
        self._send_buffer_size = val
        return self

    def reuse_addr(self, val=None):
        if val is None:
            return self._reuse_addr
        self._reuse_addr = val
        return self

    def linger(self, val=None):
        if val is None:
            return self._linger
        self._linger = val
        return self

    # Timeout Accessors
    def connect_timeout(self, val=None):
        if val is None:
            return self._connect_timeout
        self._connect_timeout = val
        return self

    def receive_timeout(self, val=None):
        if val is None:
            return self._receive_timeout
        self._receive_timeout = val
        return self

    def accept_timeout(self, val=None):
        if val is None:
            return self._accept_timeout
        self._accept_timeout = val
        return self

    # TCP Options Accessors
    def no_delay(self, val=None):
        if val is None:
            return self._no_delay
        self._no_delay = val
        return self

    def traffic_class(self, val=None):
        if val is None:
            return self._traffic_class
        self._traffic_class = val
        return self

    # UDP Options Accessors
    def broadcast(self, val=None):
        if val is None:
            return self._broadcast
        self._broadcast = val
        return self

    # Utility Methods
    def get_timeout_seconds(self):
        """Get timeouts as seconds tuple for Python requests library."""
        connect_secs = self._connect_timeout.to_sec() if self._connect_timeout else None
        read_secs = self._receive_timeout.to_sec() if self._receive_timeout else None
        return (connect_secs, read_secs)

    def to_str(self):
        return f"SocketConfig(connect={self._connect_timeout}, receive={self._receive_timeout})"
