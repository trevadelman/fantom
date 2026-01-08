#
# concurrent::Future
# Represents the result of an asynchronous computation
#

from fan.sys.Obj import Obj


class Future(Obj):
    """
    Future represents the result of an asynchronous computation.
    This is the abstract base class that can wrap an ActorFuture.
    Subclasses can extend Future and use wrap() to customize behavior.
    """

    def __init__(self, wraps=None):
        """
        Constructor for Future. Accepts optional wrapped future.
        Subclasses should call super().__init__(wraps) with the wrapped Future.
        """
        # Note: Don't call super().__init__() with arguments - Obj doesn't take any
        super().__init__()
        self._wraps = wraps

    @staticmethod
    def make_completable():
        """Construct a completable future instance in the pending state."""
        from fan.concurrent.ActorFuture import ActorFuture
        return ActorFuture.make()

    @staticmethod
    def wait_for_all(futures, timeout=None):
        """
        Block on a list of futures until they all transition to a completed state.
        If timeout is null block forever, otherwise raise TimeoutErr if any one
        of the futures does not complete before the timeout elapses.
        """
        from fan.concurrent.ActorFuture import ActorFuture
        ActorFuture.wait_for_all(futures, timeout)

    def wraps(self):
        """Return the wrapped future or null if this is an ActorFuture."""
        return self._wraps

    def _wrapped(self):
        """Get the wrapped future, raising error if not set."""
        if self._wraps is None:
            from fan.sys.Err import UnsupportedErr
            raise UnsupportedErr.make("Future missing wraps")
        return self._wraps

    def wrap(self, future):
        """
        Abstract method - create new instance of subclass that wraps given future.
        Subclasses must override this.
        """
        raise NotImplementedError("Future.wrap must be overridden by subclass")

    # Delegating methods to wrapped future

    def is_done(self):
        """Return if this future has completed."""
        return self.status().is_complete()

    def is_cancelled(self):
        """Return if this future was cancelled."""
        return self.status().is_cancelled()

    def status(self):
        """Return current status of this future."""
        return self._wrapped().status()

    def get(self, timeout=None):
        """Block current thread until result is ready."""
        return self._wrapped().get(timeout)

    def err(self):
        """Return the exception or null if completed successfully."""
        return self._wrapped().err()

    def wait_for(self, timeout=None):
        """Block until this future transitions to a completed state."""
        self._wrapped().wait_for(timeout)
        return self

    def then(self, onOk, onErr=None):
        """Register callback when this future completes."""
        result = self._wrapped().then(onOk, onErr)
        return self.wrap(result)

    def cancel(self):
        """Cancel this computation."""
        self._wrapped().cancel()

    def complete(self, result):
        """Complete the future successfully with given value."""
        self._wrapped().complete(result)
        return self

    def complete_err(self, err):
        """Complete the future with a failure condition."""
        self._wrapped().complete_err(err)
        return self

    def promise(self):
        """Get JavaScript Promise object - not available in Python."""
        from fan.sys.Err import UnsupportedErr
        raise UnsupportedErr.make("Not available in Python VM")
