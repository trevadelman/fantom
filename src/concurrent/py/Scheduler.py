#
# concurrent::Scheduler
# Scheduler is used to schedule work to be run after an elapsed period of time.
# It is optimized for use with the actor framework.
#

import threading
import time


class Scheduler:
    """
    Scheduler is used to schedule work to be run after an elapsed
    period of time. It is optimized for use with the actor framework.
    Scheduler lazily launches a background thread the first time an
    item of work is scheduled.
    """

    def __init__(self, name):
        """Constructor."""
        self.name = name
        self.alive = True
        self.head = None  # Linked list of scheduled work, sorted by deadline
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._thread = None

    def schedule(self, ns, work):
        """
        Schedule the work item to be executed after
        the given duration of nanoseconds has elapsed.
        """
        with self._condition:
            # Insert into our linked list
            new_head = self._add(ns, work)

            # If we haven't launched our thread yet, then launch it
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run,
                    name=f"{self.name}-Scheduler",
                    daemon=True  # Daemon thread so it doesn't block exit
                )
                self._thread.start()

            # If we added to the head of our linked list, then we
            # modified our earliest deadline, so we need to notify thread
            if new_head:
                self._condition.notify_all()

    def _add(self, ns, work):
        """
        Add the work item into the linked list so that the list
        is always sorted by earliest deadline to oldest deadline.
        Return True if we have a new head which changes our
        next earliest deadline.
        """
        # Create new node for our linked list
        node = _Node()
        node.deadline = time.time_ns() + ns
        node.work = work

        # If no items, this is easy
        if self.head is None:
            self.head = node
            return True

        # If new item has earliest deadline it becomes new head
        if node.deadline < self.head.deadline:
            node.next = self.head
            self.head = node
            return True

        # Find insertion point in linked list
        last = self.head
        cur = self.head.next
        while cur is not None:
            if node.deadline < cur.deadline:
                node.next = cur
                last.next = node
                return False

            last = cur
            cur = cur.next

        # This node has the oldest deadline, append to linked list
        last.next = node
        return False

    def stop(self):
        """
        Stop the background thread and call cancel
        on all pending work items.
        """
        with self._condition:
            # Kill background thread
            self.alive = False
            self._condition.notify_all()

            # Call cancel on everything in queue
            node = self.head
            while node is not None:
                try:
                    node.work.cancel()
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                node = node.next

            # Clear queue
            self.head = None

    def _run(self):
        """Background thread that processes scheduled work."""
        while self.alive:
            try:
                work = None
                with self._condition:
                    # If no work ready to go, then wait for next deadline
                    now = time.time_ns()
                    if self.head is None or self.head.deadline > now:
                        if self.head is not None:
                            to_sleep_ns = self.head.deadline - now
                            # Convert nanoseconds to seconds for wait()
                            to_sleep_sec = to_sleep_ns / 1_000_000_000.0
                            self._condition.wait(timeout=to_sleep_sec)
                        else:
                            # No work, wait indefinitely until notified
                            self._condition.wait()
                        continue

                    # Dequeue the next work item while holding lock
                    work = self.head.work
                    self.head = self.head.next

                # Work callback - outside of lock
                if work is not None:
                    try:
                        work.work()
                    except Exception as e:
                        if self.alive:
                            import traceback
                            traceback.print_exc()
            except Exception as e:
                if self.alive:
                    import traceback
                    traceback.print_exc()


class _Node:
    """Node in the linked list of scheduled work."""

    def __init__(self):
        self.deadline = 0  # time.time_ns() deadline
        self.work = None   # Work item to execute
        self.next = None   # Next node in linked list

    def __str__(self):
        ms = (self.deadline - time.time_ns()) // 1_000_000
        return f"Deadline: {ms}ms  Work: {self.work}"


class ScheduledWork:
    """
    Work item that enqueues a future to an actor when deadline hits.
    Implements the Work interface expected by Scheduler.
    """

    def __init__(self, actor, future):
        self.actor = actor
        self.future = future

    def __str__(self):
        return f"ScheduledWork msg={self.future.msg}"

    def work(self):
        """Called when deadline hits - enqueue the future to the actor."""
        if not self.future.is_cancelled():
            self.actor._enqueue_later(self.future)

    def cancel(self):
        """Called when scheduler is stopped - cancel the future."""
        self.future.cancel()
