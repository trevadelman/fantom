#
# concurrent::Actor
# Actor is a worker who processes messages asynchronously
#

import threading
import time
from fan.sys.Obj import Obj
from fan.sys.Map import Map
from fan.sys.Err import Err, ArgErr, NotImmutableErr


class Actor(Obj):
    """
    Actor is a worker who processes messages asynchronously.
    """

    # Thread-local storage for actor locals
    _thread_locals = threading.local()

    # Sentinel value for idle state
    _idle_msg = "_idle_"

    def __init__(self, pool=None, receive=None):
        super().__init__()
        from fan.concurrent.ActorPool import ActorPool

        # Validate pool
        if pool is None:
            raise ArgErr.make("pool is null")

        # Validate receive - must supply func or subclass Actor
        if receive is None:
            from fan.sys.Type import Type
            if self.typeof().qname() == "concurrent::Actor":
                raise ArgErr.make("must supply receive func or subclass Actor")
        else:
            # Ensure receive function is immutable
            from fan.sys.ObjUtil import ObjUtil
            if not ObjUtil.is_immutable(receive):
                receive = receive.to_immutable()

        self._pool = pool
        self._receive_func = receive
        self._context = Actor._Context(self)
        self._queue = Actor._Queue()
        self._lock = threading.Lock()
        self._cur_msg = Actor._idle_msg
        self._submitted = False
        self._receive_count = 0
        self._receive_ticks = 0

    @staticmethod
    def make(pool, receive=None):
        """Factory method"""
        return Actor(pool, receive)

    @staticmethod
    def make_coalescing(pool, toKey, coalesce, receive=None):
        """Create an actor with a coalescing message loop"""
        from fan.sys.ObjUtil import ObjUtil

        # Make functions immutable
        if toKey is not None and hasattr(toKey, 'to_immutable'):
            toKey = toKey.to_immutable()
        if coalesce is not None and hasattr(coalesce, 'to_immutable'):
            coalesce = coalesce.to_immutable()

        # Create actor with coalescing queue
        actor = Actor(pool, receive)
        actor._queue = Actor._CoalescingQueue(toKey, coalesce)
        return actor

    # Actor API

    def pool(self):
        """The pool used to control execution of this actor."""
        return self._pool

    def send(self, msg):
        """
        Asynchronously send a message to this actor for processing.
        If msg is not immutable, then NotImmutableErr is thrown.
        Return a future which may be used to obtain the result.
        """
        return self._send(msg, None, None)

    def send_later(self, duration, msg):
        """
        Schedule a message for delivery after the specified duration.
        If msg is not immutable, then NotImmutableErr is thrown.
        Return a future which may be used to obtain the result.
        """
        # Ensure message is immutable
        msg = Actor._safe(msg)

        # Don't deliver new messages to a stopped pool
        if self._pool.is_stopped():
            raise Err.make(f"ActorPool is stopped [{self._pool.name()}]")

        # Create future for this message
        from fan.concurrent.ActorFuture import ActorFuture
        future = ActorFuture(msg)

        # Schedule with the pool's scheduler
        self._pool.schedule(self, duration, future)

        return future

    def send_when_complete(self, future, msg):
        """
        Schedule a message for delivery after the given future completes.
        If msg is not immutable, then NotImmutableErr is thrown.
        Return a future which may be used to obtain the result.
        """
        # Ensure message is immutable
        msg = Actor._safe(msg)

        # Don't deliver new messages to a stopped pool
        if self._pool.is_stopped():
            raise Err.make(f"ActorPool is stopped [{self._pool.name()}]")

        # Create future for this message
        from fan.concurrent.ActorFuture import ActorFuture
        new_future = ActorFuture(msg)

        # Get the ActorFuture from the passed future (handle wrapping)
        when_done_future = Actor._to_when_done_future(future)

        # Register to be notified when the original future completes
        when_done_future.send_when_done(self, new_future)

        return new_future

    def send_when_done(self, future, msg):
        """Deprecated - use send_when_complete"""
        return self.send_when_complete(future, msg)

    @staticmethod
    def _to_when_done_future(future):
        """Extract the ActorFuture from a Future (handles wrapping)"""
        from fan.concurrent.ActorFuture import ActorFuture

        # If it's already an ActorFuture, return it
        if isinstance(future, ActorFuture):
            return future

        # Check if it wraps an ActorFuture
        wraps = future.wraps() if hasattr(future, 'wraps') else None
        if isinstance(wraps, ActorFuture):
            return wraps

        # Not an actor future
        raise ArgErr.make("Only actor Futures supported for send_when_complete")

    def receive(self, msg):
        """
        The receive behavior for this actor.
        Override in subclass or provide function to constructor.
        """
        if self._receive_func is not None:
            # Handle functions with variable arity - Fantom allows
            # functions to ignore extra parameters
            try:
                return self._receive_func(msg)
            except TypeError as e:
                # If the function doesn't accept the message parameter, call without it
                if "positional argument" in str(e):
                    return self._receive_func()
                raise
        print(f"WARNING: {self.typeof()}.receive not overridden")
        return None

    # Diagnostics

    def thread_state(self):
        """Return debug string for current state: idle, running, or pending"""
        if self._cur_msg != Actor._idle_msg:
            return "running"
        if self._submitted:
            return "pending"
        return "idle"

    def is_queue_full(self):
        """Return if queue_size >= pool's max_queue"""
        return self._queue.size >= self._pool.max_queue()

    def queue_size(self):
        """Get current number of messages pending"""
        return self._queue.size

    def queue_peak(self):
        """Get peak number of messages queued"""
        return self._queue.peak

    def receive_count(self):
        """Get total number of messages processed"""
        return self._receive_count

    def receive_ticks(self):
        """Get total nanoseconds spent in receive"""
        return self._receive_ticks

    # Static utilities

    @staticmethod
    def sleep(duration):
        """Put the currently executing actor thread to sleep"""
        if hasattr(duration, 'ticks'):
            ns = duration.ticks()
        else:
            ns = int(duration)
        time.sleep(ns / 1_000_000_000.0)

    @staticmethod
    def locals():
        """
        Return the map of actor-local variables visible only to the current actor.
        """
        if not hasattr(Actor._thread_locals, 'actor_locals') or Actor._thread_locals.actor_locals is None:
            Actor._thread_locals.actor_locals = Map()
        return Actor._thread_locals.actor_locals

    # Internal implementation

    def _send(self, msg, duration, when_done):
        """Internal send implementation"""
        # Ensure message is immutable
        msg = Actor._safe(msg)

        # Don't deliver new messages to a stopped pool
        if self._pool.is_stopped():
            raise Err.make(f"ActorPool is stopped [{self._pool.name()}]")

        # Create future for this message
        from fan.concurrent.ActorFuture import ActorFuture
        future = ActorFuture(msg)

        # Enqueue the message
        future = self._enqueue(future, True, True)

        return future

    def _enqueue(self, future, coalesce=True, check_max_queue=True):
        """Add a future to the queue and submit to pool if needed"""
        from fan.concurrent.ActorFuture import ActorFuture
        from fan.sys.Err import QueueOverflowErr

        with self._lock:
            # Attempt to coalesce with existing pending message
            if coalesce and hasattr(self._queue, 'coalesce'):
                coalesced = self._queue.coalesce(future)
                if coalesced is not None:
                    return coalesced

            # Check queue size
            if self._queue.size + 1 > self._pool.max_queue() and check_max_queue:
                future.complete_err(QueueOverflowErr.make(f"queue_size: {self._queue.size}"))
                return future

            # Add to queue
            self._queue.add(future)

            # Submit to thread pool if not already submitted or running
            if not self._submitted:
                self._submitted = True
                self._pool.submit(self)

            return future

    def _enqueue_later(self, future):
        """Enqueue a scheduled message"""
        return self._enqueue(future, False, False)

    def _enqueue_when_done(self, future):
        """Enqueue a when-done message"""
        return self._enqueue(future, False, True)

    def _work(self):
        """Called by pool to process messages"""
        # Reset environment for this actor
        Actor._thread_locals.actor_locals = self._context.locals
        from fan.sys.Locale import Locale
        Locale.set_cur(self._context.locale)

        # Process messages
        start_ticks = time.time_ns()
        max_ticks = self._pool.max_time_before_yield().ticks() if self._pool.max_time_before_yield() else 1_000_000_000

        while True:
            # Get next message
            future = None
            with self._lock:
                future = self._queue.get()
            if future is None:
                break

            # Dispatch the message
            self._cur_msg = future.msg
            self._dispatch(future)
            self._cur_msg = Actor._idle_msg

            # Check if we should yield our thread
            if self._pool.has_pending():
                cur_ticks = time.time_ns()
                if cur_ticks - start_ticks >= max_ticks:
                    break

        # Update receive ticks
        self._receive_ticks += time.time_ns() - start_ticks

        # Flush environment back to context
        self._context.locale = Locale.cur()

        # Either clear submitted flag or resubmit to pool
        with self._lock:
            if self._queue.size == 0:
                self._submitted = False
            else:
                self._submitted = True
                self._pool.submit(self)

    def _dispatch(self, future):
        """Process a single message"""
        try:
            if future.is_cancelled():
                return
            if self._pool.killed:
                future.cancel()
                return
            self._receive_count += 1
            result = self.receive(future.msg)
            future.complete(result)
        except Err as e:
            future.complete_err(e)
        except Exception as e:
            future.complete_err(Err.make(str(e)))

    def _kill(self):
        """Cancel all pending messages"""
        queue = None
        with self._lock:
            queue = self._queue
            self._queue = Actor._Queue()

        while True:
            future = queue.get()
            if future is None:
                break
            future.cancel()

    @staticmethod
    def _safe(obj):
        """Ensure object is immutable"""
        from fan.sys.ObjUtil import ObjUtil
        return ObjUtil.to_immutable(obj)

    # Inner classes

    class _Queue:
        """Simple linked list queue for messages"""

        def __init__(self):
            self.head = None
            self.tail = None
            self.size = 0
            self.peak = 0

        def get(self):
            """Remove and return head of queue, or None if empty"""
            if self.head is None:
                return None
            f = self.head
            self.head = f.next
            if self.head is None:
                self.tail = None
            f.next = None
            self.size -= 1
            return f

        def add(self, f):
            """Add future to tail of queue"""
            if self.tail is None:
                self.head = self.tail = f
                f.next = None
            else:
                self.tail.next = f
                self.tail = f
            self.size += 1
            if self.size > self.peak:
                self.peak = self.size

    class _Context:
        """Mutable world state of an actor"""

        def __init__(self, actor):
            self.actor = actor
            self.locals = Map()
            from fan.sys.Locale import Locale
            self.locale = Locale.cur()

    class _CoalescingQueue(_Queue):
        """Queue that coalesces messages with the same key"""

        def __init__(self, to_key_func, coalesce_func):
            super().__init__()
            self.to_key_func = to_key_func
            self.coalesce_func = coalesce_func
            self.pending = {}  # key -> ActorFuture

        def get(self):
            """Remove and return head, also remove from pending"""
            f = super().get()
            if f is not None:
                try:
                    key = self._to_key(f.msg)
                    if key is not None:
                        self.pending.pop(key, None)
                except:
                    pass
            return f

        def add(self, f):
            """Add to queue and pending map"""
            try:
                key = self._to_key(f.msg)
                if key is not None:
                    self.pending[key] = f
            except:
                pass
            super().add(f)

        def coalesce(self, incoming):
            """Try to coalesce with existing pending message"""
            key = self._to_key(incoming.msg)
            if key is None:
                return None

            orig = self.pending.get(key)
            if orig is None:
                return None

            # Coalesce the messages
            orig.msg = self._coalesce_msg(orig.msg, incoming.msg)
            return orig

        def _to_key(self, msg):
            if self.to_key_func is None:
                return msg
            return self.to_key_func(msg)

        def _coalesce_msg(self, orig, incoming):
            if self.coalesce_func is None:
                return incoming
            return self.coalesce_func(orig, incoming)
