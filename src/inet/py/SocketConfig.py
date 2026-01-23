#
# inet::SocketConfig - Python native implementation
#
# Socket configuration for timeouts and other socket options.
# Used by WebClient to configure request timeouts.
#

from fan.sys.Obj import Obj
from fan.sys.Duration import Duration


class SocketConfig(Obj):
    """Socket configuration holder.

    This is a Python-native implementation that stores timeout configuration
    for use by WebClient (which uses Python's requests library).
    """

    _cur_instance = None

    @staticmethod
    def cur():
        """Get the current default SocketConfig singleton."""
        if SocketConfig._cur_instance is None:
            SocketConfig._cur_instance = SocketConfig()
        return SocketConfig._cur_instance

    @staticmethod
    def make():
        """Create a new SocketConfig with default settings."""
        return SocketConfig()

    def __init__(self):
        super().__init__()
        # Default timeout: 60 seconds (same as Fantom default)
        self._connect_timeout = Duration.make(60_000_000_000)  # 60s in nanoseconds
        self._receive_timeout = Duration.make(60_000_000_000)

    def connect_timeout(self, val=None):
        """Get or set the connect timeout."""
        if val is None:
            return self._connect_timeout
        self._connect_timeout = val
        return self

    def receive_timeout(self, val=None):
        """Get or set the receive timeout."""
        if val is None:
            return self._receive_timeout
        self._receive_timeout = val
        return self

    def set_timeouts(self, timeout):
        """Set both connect and receive timeouts to the same value.

        Args:
            timeout: Duration for both timeouts

        Returns:
            New SocketConfig with the specified timeouts
        """
        # Create a new config (don't modify singleton)
        config = SocketConfig()
        config._connect_timeout = timeout
        config._receive_timeout = timeout
        return config

    def get_timeout_seconds(self):
        """Get timeout as seconds (float) for use with Python requests library.

        Returns:
            Tuple of (connect_timeout, read_timeout) in seconds
        """
        connect_secs = self._connect_timeout.to_sec() if self._connect_timeout else 60.0
        read_secs = self._receive_timeout.to_sec() if self._receive_timeout else 60.0
        return (connect_secs, read_secs)

    def to_str(self):
        return f"SocketConfig(connect={self._connect_timeout}, receive={self._receive_timeout})"
