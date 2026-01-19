#
# LogRec - Log record for Fantom
#
from fan.sys.Obj import Obj


class LogRec(Obj):
    """
    LogRec represents a single log record.
    """

    @staticmethod
    def make(time, level, log_name, message, err=None):
        """Factory method to create a log record"""
        return LogRec(time, level, log_name, message, err)

    def __init__(self, time, level, log_name, message, err=None):
        super().__init__()
        self._time = time
        self._level = level
        self._log_name = log_name
        self._msg = message
        self._err = err

    def time(self, _val_=None):
        if _val_ is None:
            return self._time
        else:
            self._time = _val_

    def level(self, _val_=None):
        if _val_ is None:
            return self._level
        else:
            self._level = _val_

    def log_name(self, _val_=None):
        if _val_ is None:
            return self._log_name
        else:
            self._log_name = _val_

    def msg(self, _val_=None):
        if _val_ is None:
            return self._msg
        else:
            self._msg = _val_

    def err(self, _val_=None):
        if _val_ is None:
            return self._err
        else:
            self._err = _val_

    def to_str(self):
        return f"[{self._level.name()}] [{self._log_name}] {self._msg}"

    def print_(self, out=None):
        """Print log record to output stream"""
        if out is None:
            from fan.sys.Env import Env
            out = Env.cur().out()
        out.print_line(self.to_str())
        if self._err is not None:
            self._err.trace(out)
