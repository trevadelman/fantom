#
# concurrent::Lock
# Hand-written runtime implementation for mutual exclusion lock
#

import threading
from fan.sys.Obj import Obj


class Lock(Obj):
    """Mutual exclusion lock for synchronization between actors.

    Supports Python context manager protocol for `with lock:` usage.
    """

    def __init__(self):
        super().__init__()
        self._lock = threading.RLock()

    @staticmethod
    def make():
        return Lock()

    @staticmethod
    def makeReentrant():
        """Construct mutual exclusion lock (reentrant)."""
        return Lock()

    def lock(self):
        """Acquire the lock; if not available then block until available."""
        self._lock.acquire()

    def unlock(self):
        """Release the lock. Raise exception if not holding the lock."""
        try:
            self._lock.release()
        except RuntimeError as e:
            from fan.sys.Err import Err
            raise Err(f"Cannot unlock: {e}")

    def tryLock(self, timeout=None):
        """Acquire the lock if free, return True. Otherwise return False.

        If timeout is non-null, block up to timeout waiting for lock.
        """
        if timeout is None:
            # Non-blocking try
            return self._lock.acquire(blocking=False)
        else:
            # Block with timeout
            timeout_secs = timeout.toMillis() / 1000.0 if hasattr(timeout, 'toMillis') else float(timeout) / 1000.0
            return self._lock.acquire(timeout=timeout_secs)

    def __enter__(self):
        """Context manager entry - acquire lock."""
        self.lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - release lock."""
        self.unlock()
        return False  # Don't suppress exceptions

    def toStr(self):
        return "Lock"

    def __str__(self):
        return self.toStr()


# Type metadata registration for reflection
from fan.sys.Type import Type
from fan.sys.Param import Param

_t = Type.find('concurrent::Lock')
_t.tf_({'sys::Js': {}})
_t.am_('makeReentrant', 265, 'concurrent::Lock', [], {})
_t.am_('lock', 1, 'sys::Void', [], {})
_t.am_('unlock', 1, 'sys::Void', [], {})
_t.am_('tryLock', 1, 'sys::Bool', [Param('timeout', Type.find('sys::Duration?'), True)], {})
