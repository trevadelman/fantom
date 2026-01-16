#
# concurrent::ActorPool
# Controller for a group of actors which manages their execution using pooled thread resources
#

import threading
from concurrent.futures import ThreadPoolExecutor
from fan.sys.Obj import Obj
from fan.sys.Err import Err, ArgErr, TimeoutErr


class ActorPool(Obj):
    """
    Controller for a group of actors which manages their execution
    using pooled thread resources.
    """

    # Lifecycle states
    RUNNING = 0
    STOPPING = 1
    DONE = 2

    def __init__(self, it_block=None):
        super().__init__()
        # Default values matching Java
        self._name = "ActorPool"
        self._max_threads = 100
        self._max_queue = 100_000_000
        self._max_time_before_yield = None  # Duration - 1sec default

        # Apply it-block configuration if provided
        if it_block is not None:
            if callable(it_block):
                it_block(self)

        # Validate configuration
        if self._max_threads < 1:
            raise ArgErr.make(f"ActorPool.max_threads must be >= 1, not {self._max_threads}")
        if self._max_queue < 1:
            raise ArgErr.make(f"ActorPool.max_queue must be >= 1, not {self._max_queue}")

        # Create thread pool with daemon threads to prevent hang on exit
        import concurrent.futures
        self._executor = ThreadPoolExecutor(max_workers=self._max_threads, thread_name_prefix=self._name)
        # Make executor threads daemon so they don't block exit
        self._executor._threads = set()  # Clear to allow daemon thread creation
        self._state = ActorPool.RUNNING
        self._lock = threading.Lock()
        self._pending_count = 0
        self.killed = False

        # Create scheduler for send_later support
        from fan.concurrent.Scheduler import Scheduler
        self._scheduler = Scheduler(self._name)

    @staticmethod
    def make(it_block=None):
        """Factory method with optional it-block for configuration"""
        return ActorPool(it_block)

    # Property accessors matching Fantom API (getter/setter pattern)

    def name(self, val=None):
        if val is None:
            return self._name
        else:
            self._name = val

    def max_threads(self, val=None):
        if val is None:
            return self._max_threads
        else:
            self._max_threads = val

    def max_queue(self, val=None):
        if val is None:
            return self._max_queue
        else:
            self._max_queue = val

    def max_time_before_yield(self, val=None):
        if val is not None:
            self._max_time_before_yield = val
            return
        if self._max_time_before_yield is None:
            from fan.sys.Duration import Duration
            return Duration.from_str("1sec")
        return self._max_time_before_yield

    # Lifecycle methods

    def is_stopped(self):
        """Has this pool been stopped or killed."""
        return self._state != ActorPool.RUNNING

    def is_done(self):
        """Has all the work in this queue finished processing and all threads terminated."""
        if self._state == ActorPool.DONE:
            return True
        with self._lock:
            if self._state == ActorPool.RUNNING:
                return False
            # Check if executor is done
            self._executor.shutdown(wait=False)
            # If no pending work, we're done
            if self._pending_count == 0:
                self._state = ActorPool.DONE
                return True
            return False

    def stop(self):
        """Orderly shutdown of threads. All pending work items are processed."""
        self._scheduler.stop()
        with self._lock:
            self._state = ActorPool.STOPPING
        return self

    def kill(self):
        """Unorderly shutdown of threads. All pending work are discarded."""
        self._scheduler.stop()
        with self._lock:
            self._state = ActorPool.STOPPING
            self.killed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        return self

    def join(self, timeout=None):
        """
        Wait for all threads to stop.
        Return this on success or raise TimeoutErr on timeout.
        """
        if not self.is_stopped():
            raise Err.make("ActorPool is not stopped")

        # Convert timeout to seconds
        timeout_secs = None
        if timeout is not None:
            if hasattr(timeout, 'ticks'):
                timeout_secs = timeout.ticks() / 1_000_000_000.0
            else:
                timeout_secs = float(timeout) / 1_000_000_000.0

        if timeout_secs is None:
            # No timeout - wait forever
            self._executor.shutdown(wait=True)
            with self._lock:
                self._state = ActorPool.DONE
            return self

        # With timeout - use a separate thread to wait
        import time
        done_event = threading.Event()

        def wait_for_shutdown():
            self._executor.shutdown(wait=True)
            done_event.set()

        waiter = threading.Thread(target=wait_for_shutdown, daemon=True)
        waiter.start()

        # Wait with timeout
        if not done_event.wait(timeout=timeout_secs):
            # Timeout expired before shutdown completed
            raise TimeoutErr.make("ActorPool.join timed out")

        with self._lock:
            self._state = ActorPool.DONE

        return self

    # Work submission

    def has_pending(self):
        """Return if we have pending workers awaiting a thread."""
        with self._lock:
            return self._pending_count > 0

    def submit(self, actor):
        """Submit actor work to the thread pool."""
        with self._lock:
            self._pending_count += 1

        def run_actor():
            try:
                actor._work()
            finally:
                with self._lock:
                    self._pending_count -= 1

        self._executor.submit(run_actor)

    def schedule(self, actor, duration, future):
        """Schedule a future to be enqueued to an actor after a duration."""
        from fan.concurrent.Scheduler import ScheduledWork
        # Get duration in nanoseconds
        ns = duration.ticks() if hasattr(duration, 'ticks') else int(duration)
        work = ScheduledWork(actor, future)
        self._scheduler.schedule(ns, work)

    def balance(self, actors):
        """Select actor with smallest queue size."""
        from fan.sys.Err import IndexErr
        from fan.sys.List import List

        # Handle Fantom List
        if isinstance(actors, List):
            actors = list(actors)

        if len(actors) == 0:
            raise IndexErr.make("Empty actor list")

        best = actors[0]
        best_size = best.queue_size()
        if best_size == 0:
            return best

        for actor in actors[1:]:
            size = actor.queue_size()
            if size < best_size:
                best = actor
                best_size = size
                if best_size == 0:
                    return best

        return best


# Type metadata registration for reflection
from fan.sys.Type import Type
from fan.sys.Param import Param

_t = Type.find('concurrent::ActorPool')
_t.tf_({'sys::Js': {}})
_t.af_('name', 1, 'sys::Str', {})
_t.af_('max_threads', 1, 'sys::Int', {})
_t.af_('max_queue', 1, 'sys::Int', {})
_t.af_('max_time_before_yield', 1, 'sys::Duration', {})
_t.am_('make', 257, 'sys::Void', [Param('f', Type.find('sys::Func?'), True)], {})
_t.am_('is_stopped', 1, 'sys::Bool', [], {})
_t.am_('is_done', 1, 'sys::Bool', [], {})
_t.am_('stop', 1, 'concurrent::ActorPool', [], {})
_t.am_('kill', 1, 'concurrent::ActorPool', [], {})
_t.am_('join', 1, 'concurrent::ActorPool', [Param('timeout', Type.find('sys::Duration?'), True)], {})
