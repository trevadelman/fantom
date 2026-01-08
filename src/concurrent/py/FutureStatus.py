#
# concurrent::FutureStatus
# State of a Future's asynchronous computation
#

from fan.sys.Obj import Obj


class FutureStatus(Obj):
    """
    State of a Future's asynchronous computation.

    Values:
    - pending: computation has not completed
    - ok: completed successfully
    - err: completed with error
    - cancelled: was cancelled
    """

    # Class-level storage for singleton instances
    _vals = {}

    def __init__(self, name, ordinal):
        super().__init__()
        self._name = name
        self._ordinal = ordinal

    def name(self):
        return self._name

    def ordinal(self):
        return self._ordinal

    def to_str(self):
        return self._name

    def __str__(self):
        return self._name

    def __repr__(self):
        return f"FutureStatus.{self._name}"

    def __eq__(self, other):
        if isinstance(other, FutureStatus):
            return self._ordinal == other._ordinal
        return False

    def __hash__(self):
        return hash(self._ordinal)

    # Helper methods matching Fantom API

    def is_pending(self):
        """Return if pending state"""
        return self._ordinal == 0

    def is_complete(self):
        """Return if in any completed state: ok, err, or cancelled"""
        return self._ordinal != 0

    def is_ok(self):
        """Return if the ok state"""
        return self._ordinal == 1

    def is_err(self):
        """Return if the err state"""
        return self._ordinal == 2

    def is_cancelled(self):
        """Return if the cancelled state"""
        return self._ordinal == 3

    # Static factory methods matching Fantom enum pattern
    @staticmethod
    def pending():
        """Return pending status singleton"""
        return FutureStatus._vals["pending"]

    @staticmethod
    def ok():
        """Return ok status singleton"""
        return FutureStatus._vals["ok"]

    @staticmethod
    def err():
        """Return err status singleton"""
        return FutureStatus._vals["err"]

    @staticmethod
    def cancelled():
        """Return cancelled status singleton"""
        return FutureStatus._vals["cancelled"]

    @staticmethod
    def vals():
        """Return all enum values"""
        return [
            FutureStatus._vals["pending"],
            FutureStatus._vals["ok"],
            FutureStatus._vals["err"],
            FutureStatus._vals["cancelled"],
        ]


# Create singleton instances after class is defined
FutureStatus._vals["pending"] = FutureStatus("pending", 0)
FutureStatus._vals["ok"] = FutureStatus("ok", 1)
FutureStatus._vals["err"] = FutureStatus("err", 2)
FutureStatus._vals["cancelled"] = FutureStatus("cancelled", 3)
