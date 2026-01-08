#
# concurrent::ActorFuture
# Future implementation used by actor framework
#

import threading
from fan.sys.Obj import Obj
from fan.sys.Err import TimeoutErr, CancelledErr, InterruptedErr, NotCompleteErr, Err
from fan.concurrent.FutureStatus import FutureStatus


class ActorFuture(Obj):
    """
    ActorFuture is the future implementation used by the actor framework.
    It manages the lifecycle of each message sent to an Actor.
    """

    # State constants matching Java implementation
    PENDING = 0x00
    DONE = 0x0F
    DONE_CANCEL = 0x1F
    DONE_OK = 0x2F
    DONE_ERR = 0x4F

    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg              # Message sent to Actor
        self.next = None            # Linked list pointer for Actor queue
        self._state = ActorFuture.PENDING
        self._result = None         # Result or exception of processing
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._when_done = []        # List of (actor, future) tuples to notify

    @staticmethod
    def make():
        """Factory method for creating completable future"""
        return ActorFuture(None)

    def wraps(self):
        """Return wrapped future if this is a subclass (None for ActorFuture)"""
        return None

    def wrap(self, future):
        """Create new instance of subclass that wraps given future"""
        return future  # ActorFuture doesn't wrap, just returns the given future

    def is_done(self):
        """Return if this future has completed"""
        return self.status().is_complete()

    def is_cancelled(self):
        """Return if this future was cancelled"""
        return self.status().is_cancelled()

    def status(self):
        """Return current status of this future"""
        state = self._state
        if state == ActorFuture.PENDING:
            return FutureStatus.pending()
        elif state == ActorFuture.DONE_OK:
            return FutureStatus.ok()
        elif state == ActorFuture.DONE_ERR:
            return FutureStatus.err()
        elif state == ActorFuture.DONE_CANCEL:
            return FutureStatus.cancelled()
        else:
            raise Err.make(f"Internal error: unknown state {state}")

    def get(self, timeout=None):
        """
        Block current thread until result is ready.
        If timeout occurs then TimeoutErr is raised.
        A null timeout blocks forever.
        If an exception was raised by the asynchronous computation,
        then it is raised to the caller of this method.
        """
        result = None

        with self._condition:
            # Wait until we enter a done state
            if timeout is None:
                # Wait forever until done
                while (self._state & ActorFuture.DONE) == 0:
                    self._condition.wait()
            else:
                # Wait with timeout
                if (self._state & ActorFuture.DONE) == 0:
                    # Convert Duration to seconds
                    if hasattr(timeout, 'ticks'):
                        timeout_secs = timeout.ticks() / 1_000_000_000.0
                    else:
                        timeout_secs = float(timeout) / 1_000_000_000.0

                    deadline = threading.Event()
                    import time
                    start = time.time()

                    while (self._state & ActorFuture.DONE) == 0:
                        left = timeout_secs - (time.time() - start)
                        if left <= 0:
                            break
                        self._condition.wait(timeout=left)

                    # If still not done, raise timeout
                    if (self._state & ActorFuture.DONE) == 0:
                        raise TimeoutErr.make("Future.get timed out")

            # Check final state
            if self._state == ActorFuture.DONE_CANCEL:
                raise CancelledErr.make("Future cancelled")

            if self._state == ActorFuture.DONE_ERR:
                # Re-raise the stored error
                err = self._result
                if hasattr(err, 'rebase'):
                    raise err.rebase()
                raise err

            result = self._result

        # Return immutable copy of result
        from fan.sys.ObjUtil import ObjUtil
        return ObjUtil.to_immutable(result) if result is not None else result

    def wait_for(self, timeout=None):
        """
        Block until this future transitions to a completed state.
        If timeout is null then block forever, otherwise raise TimeoutErr
        if timeout elapses. Return this.
        """
        with self._condition:
            if timeout is None:
                # Wait forever until done
                while (self._state & ActorFuture.DONE) == 0:
                    self._condition.wait()
            else:
                if (self._state & ActorFuture.DONE) == 0:
                    # Convert Duration to seconds
                    if hasattr(timeout, 'ticks'):
                        timeout_secs = timeout.ticks() / 1_000_000_000.0
                    else:
                        timeout_secs = float(timeout) / 1_000_000_000.0

                    import time
                    start = time.time()

                    while (self._state & ActorFuture.DONE) == 0:
                        left = timeout_secs - (time.time() - start)
                        if left <= 0:
                            break
                        self._condition.wait(timeout=left)

                    if (self._state & ActorFuture.DONE) == 0:
                        raise TimeoutErr.make("Future.get timed out")

        return self

    def err(self):
        """
        Return the exception raised by the asynchronous computation or null
        if the future completed successfully. This method can only be used
        after completion, otherwise raise NotCompleteErr.
        """
        state = self._state
        if state == ActorFuture.DONE_OK:
            return None
        elif state == ActorFuture.DONE_ERR:
            return self._result
        elif state == ActorFuture.DONE_CANCEL:
            return CancelledErr.make("Future cancelled")
        else:
            raise NotCompleteErr.make("Future is pending")

    def cancel(self):
        """
        Cancel this computation if it has not begun processing.
        No guarantee is made that the computation will be cancelled.
        """
        when_done = None
        with self._condition:
            if (self._state & ActorFuture.DONE) == 0:
                self._state = ActorFuture.DONE_CANCEL
            self.msg = None
            self._result = None
            self._condition.notify_all()
            when_done = self._when_done
            self._when_done = []

        # Send when-done notifications outside of lock
        self._send_when_done(when_done)

    def complete(self, result):
        """
        Complete the future successfully with given value.
        Raise an exception if value is not immutable or the future is
        already complete (ignore this call if cancelled).
        Return this.
        """
        # Ensure result is immutable
        from fan.sys.ObjUtil import ObjUtil
        result = ObjUtil.to_immutable(result) if result is not None else result

        when_done = None
        with self._condition:
            if self._state == ActorFuture.DONE_CANCEL:
                return self
            if self._state != ActorFuture.PENDING:
                raise Err.make("Future already complete")
            self._state = ActorFuture.DONE_OK
            self._result = result
            self._condition.notify_all()
            when_done = self._when_done
            self._when_done = []

        self._send_when_done(when_done)
        return self

    def complete_err(self, err):
        """
        Complete the future with a failure condition using given exception.
        Raise an exception if the future is already complete
        (ignore this call if cancelled). Return this.
        """
        when_done = None
        with self._condition:
            if self._state == ActorFuture.DONE_CANCEL:
                return self
            if self._state != ActorFuture.PENDING:
                raise Err.make("Future already complete")
            self._state = ActorFuture.DONE_ERR
            self._result = err
            self._condition.notify_all()
            when_done = self._when_done
            self._when_done = []

        self._send_when_done(when_done)
        return self

    def then(self, onOk, onErr=None):
        """
        Register a callback function when this future completes.
        In Python this is a blocking operation (like Java VM).
        """
        self.wait_for(None)
        chain = None
        try:
            state = self._state
            if state == ActorFuture.DONE_OK:
                chain = onOk(self._result)
            elif state == ActorFuture.DONE_ERR:
                if onErr is not None:
                    chain = onErr(self._result)
            elif state == ActorFuture.DONE_CANCEL:
                if onErr is not None:
                    chain = onErr(CancelledErr.make("Future cancelled"))
            else:
                raise NotCompleteErr.make("Future is pending")

            result_future = ActorFuture.make()
            result_future.complete(chain)
            return result_future
        except Exception as e:
            result_future = ActorFuture.make()
            if isinstance(e, Err):
                result_future.complete_err(e)
            else:
                result_future.complete_err(Err.make(str(e)))
            return result_future

    def promise(self):
        """Get JavaScript Promise object - not available in Python"""
        from fan.sys.Err import UnsupportedErr
        raise UnsupportedErr.make("Not available in Python VM")

    # Methods for send_when_done/send_when_complete support

    def send_when_done(self, actor, future):
        """
        Register actor/future to be notified when this future completes.
        Used by Actor.send_when_complete().
        """
        immediate = False
        with self._condition:
            if self.is_done():
                immediate = True
            else:
                self._when_done.append((actor, future))

        if immediate:
            try:
                actor._enqueue_when_done(future)
            except Exception as e:
                import traceback
                traceback.print_exc()

    def _register_when_done(self, actor, future):
        """Alias for send_when_done for backwards compatibility"""
        return self.send_when_done(actor, future)

    def _send_when_done(self, when_done_list):
        """Send notifications to all registered when-done handlers"""
        if when_done_list is None:
            return
        for actor, future in when_done_list:
            try:
                actor._enqueue_when_done(future)
            except Exception as e:
                import traceback
                traceback.print_exc()

    # Static helper for wait_for_all
    @staticmethod
    def wait_for_all(futures, timeout=None):
        """
        Block on a list of futures until they all transition to a completed state.
        If timeout is null block forever, otherwise raise TimeoutErr if any one
        of the futures does not complete before the timeout elapses.
        """
        if timeout is None:
            for f in futures:
                f.wait_for(None)
        else:
            import time
            # Convert Duration to milliseconds
            if hasattr(timeout, 'millis'):
                deadline = time.time() * 1000 + timeout.millis()
            else:
                deadline = time.time() * 1000 + float(timeout) / 1_000_000

            for f in futures:
                left = deadline - time.time() * 1000
                from fan.sys.Duration import Duration
                f.wait_for(Duration.make_millis(int(left)))


# Type metadata registration for reflection
from fan.sys.Type import Type
from fan.sys.Param import Param

_t = Type.find('concurrent::ActorFuture')
# Set base type to concurrent::Future (use _base_qname for Type.base() lookup)
_t._base_qname = 'concurrent::Future'
_t.tf_({'sys::Js': {}})
_t.am_('make', 265, 'concurrent::ActorFuture', [], {})
_t.am_('status', 1, 'concurrent::FutureStatus', [], {})
_t.am_('is_done', 1, 'sys::Bool', [], {})
_t.am_('is_cancelled', 1, 'sys::Bool', [], {})
_t.am_('get', 1, 'sys::Obj?', [Param('timeout', Type.find('sys::Duration?'), True)], {})
_t.am_('wait_for', 1, 'concurrent::Future', [Param('timeout', Type.find('sys::Duration?'), True)], {})
_t.am_('cancel', 1, 'sys::Void', [], {})
_t.am_('complete', 1, 'concurrent::Future', [Param('result', Type.find('sys::Obj?'), False)], {})
_t.am_('complete_err', 1, 'concurrent::Future', [Param('err', Type.find('sys::Err'), False)], {})
_t.am_('then', 1, 'concurrent::Future', [Param('onOk', Type.find('|sys::Obj?->sys::Obj?|'), False), Param('onErr', Type.find('|sys::Err->sys::Obj?|?'), True)], {})
