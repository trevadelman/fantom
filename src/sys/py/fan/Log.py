#
# Log - Logging support for Fantom
#
import logging
from fan.sys.Obj import Obj

class LogLevel(Obj):
    """
    LogLevel represents the severity of a log message.
    """

    _levels = {}
    _vals_list = None

    def __init__(self, name, ordinal):
        self._name = name
        self._ordinal = ordinal

    @staticmethod
    def fromStr(name, checked=True):
        """Parse LogLevel from string"""
        name_lower = name.lower()
        if name_lower in LogLevel._levels:
            return LogLevel._levels[name_lower]
        if checked:
            from fan.sys.Err import ParseErr
            raise ParseErr(f"Unknown log level: {name}")
        return None

    @staticmethod
    def vals():
        """Get all log level values"""
        if LogLevel._vals_list is None:
            from fan.sys.List import List
            vals = List.fromLiteral(
                [LogLevel._debug, LogLevel._info, LogLevel._warn, LogLevel._err, LogLevel._silent],
                "sys::LogLevel"
            )
            LogLevel._vals_list = List.toImmutable(vals)
        return LogLevel._vals_list

    @staticmethod
    def debug():
        """Get debug level"""
        return LogLevel._debug

    @staticmethod
    def info():
        """Get info level"""
        return LogLevel._info

    @staticmethod
    def warn():
        """Get warn level"""
        return LogLevel._warn

    @staticmethod
    def err():
        """Get err level"""
        return LogLevel._err

    @staticmethod
    def silent():
        """Get silent level"""
        return LogLevel._silent

    def name(self):
        """Get level name"""
        return self._name

    def ordinal(self):
        """Get numeric ordinal"""
        return self._ordinal

    def toStr(self):
        return self._name

    def __lt__(self, other):
        return self._ordinal < other._ordinal

    def __le__(self, other):
        return self._ordinal <= other._ordinal

    def __gt__(self, other):
        return self._ordinal > other._ordinal

    def __ge__(self, other):
        return self._ordinal >= other._ordinal

    def __eq__(self, other):
        if not isinstance(other, LogLevel):
            return False
        return self._ordinal == other._ordinal

    def __hash__(self):
        return hash(self._ordinal)

    def hash(self):
        """Override Obj.hash() - return ordinal-based hash"""
        return hash(self._ordinal)


# Define log levels - stored in private class attributes
LogLevel._debug = LogLevel("debug", 0)
LogLevel._info = LogLevel("info", 1)
LogLevel._warn = LogLevel("warn", 2)
LogLevel._err = LogLevel("err", 3)
LogLevel._silent = LogLevel("silent", 4)

LogLevel._levels["debug"] = LogLevel._debug
LogLevel._levels["info"] = LogLevel._info
LogLevel._levels["warn"] = LogLevel._warn
LogLevel._levels["err"] = LogLevel._err
LogLevel._levels["silent"] = LogLevel._silent


class LogRec(Obj):
    """
    LogRec represents a single log record.
    """

    def __init__(self, time, level, logName, msg, err=None):
        self._time = time
        self._level = level
        self._logName = logName
        self._msg = msg
        self._err = err

    def time(self):
        return self._time

    def level(self):
        return self._level

    def logName(self):
        return self._logName

    def msg(self):
        return self._msg

    def err(self):
        return self._err

    def toStr(self):
        return f"[{self._level.name()}] {self._logName}: {self._msg}"


class Log(Obj):
    """
    Log provides logging functionality.
    """

    _logs = {}
    _handlers = []  # Global handlers (static)

    def __init__(self, name, register=True):
        """Create a new log. If register=True, adds to global registry."""
        # Validate name
        if not Log._isValidName(name):
            from fan.sys.Err import NameErr
            raise NameErr(f"Invalid log name: {name}")

        # Check for duplicate registration
        if register and name in Log._logs:
            from fan.sys.Err import ArgErr
            raise ArgErr(f"Log already registered: {name}")

        self._name = name
        self._level = LogLevel._info
        self._pyLogger = logging.getLogger(name)

        if register:
            Log._logs[name] = self

    @staticmethod
    def _isValidName(name):
        """Validate log name - must be valid identifier characters"""
        if not name:
            return False
        for c in name:
            if not (c.isalnum() or c == '.' or c == '_'):
                return False
        if name.startswith('@'):
            return False
        return True

    @staticmethod
    def make(name, register=True):
        """Create a new log"""
        return Log(name, register)

    @staticmethod
    def get(name):
        """Get or create a log by name"""
        # Validate name
        if not Log._isValidName(name):
            from fan.sys.Err import NameErr
            raise NameErr(f"Invalid log name: {name}")

        if name in Log._logs:
            return Log._logs[name]
        log = Log(name, True)
        return log

    @staticmethod
    def find(name, checked=True):
        """Find a log by name"""
        if name in Log._logs:
            return Log._logs[name]
        if checked:
            from fan.sys.Err import Err
            raise Err(f"Unknown log: {name}")
        return None

    @staticmethod
    def list_():
        """List all logs"""
        from fan.sys.List import List
        return List.fromLiteral(list(Log._logs.values()), "sys::Log")

    def name(self):
        """Get log name"""
        return self._name

    def level(self, value=None):
        """Get or set log level - called as log.level() or log.level(newLevel)"""
        if value is None:
            return self._level
        else:
            self._level = value
            return None

    def isEnabled(self, level):
        """Check if level is enabled"""
        return level._ordinal >= self._level._ordinal

    def isDebug(self):
        return self._level._ordinal <= LogLevel._debug._ordinal

    def isInfo(self):
        return self._level._ordinal <= LogLevel._info._ordinal

    def isWarn(self):
        return self._level._ordinal <= LogLevel._warn._ordinal

    def isErr(self):
        return self._level._ordinal <= LogLevel._err._ordinal

    def debug(self, msg, err=None):
        """Log debug message"""
        if self.isEnabled(LogLevel._debug):
            self._log(LogLevel._debug, msg, err)

    def info(self, msg, err=None):
        """Log info message"""
        if self.isEnabled(LogLevel._info):
            self._log(LogLevel._info, msg, err)

    def warn(self, msg, err=None):
        """Log warning message"""
        if self.isEnabled(LogLevel._warn):
            self._log(LogLevel._warn, msg, err)

    def err(self, msg, err=None):
        """Log error message"""
        if self.isEnabled(LogLevel._err):
            self._log(LogLevel._err, msg, err)

    def _log(self, level, msg, err):
        """Internal log method - creates LogRec and calls log()"""
        from fan.sys.DateTime import DateTime
        time = DateTime.now()
        rec = LogRec(time, level, self._name, msg, err)
        # Call the overrideable log method
        self.log(rec)

    def log(self, rec):
        """Log a record - can be overridden by subclasses"""
        # Call global handlers
        for handler in Log._handlers:
            try:
                handler(rec)
            except:
                pass

        # Map to Python logging level
        level = rec._level
        py_level = {
            LogLevel._debug: logging.DEBUG,
            LogLevel._info: logging.INFO,
            LogLevel._warn: logging.WARNING,
            LogLevel._err: logging.ERROR
        }.get(level, logging.INFO)

        self._pyLogger.log(py_level, rec._msg)
        if rec._err:
            self._pyLogger.exception(rec._err)

    def toStr(self):
        return self._name

    @staticmethod
    def handlers():
        """Get global log handlers"""
        from fan.sys.List import List
        return List.fromLiteral(list(Log._handlers), "|sys::LogRec->sys::Void|")

    @staticmethod
    def addHandler(handler):
        """Add a global log handler"""
        # Check immutability
        from fan.sys.ObjUtil import ObjUtil
        if not ObjUtil.isImmutable(handler):
            from fan.sys.Err import NotImmutableErr
            raise NotImmutableErr("Handler must be immutable")
        Log._handlers.append(handler)

    @staticmethod
    def removeHandler(handler):
        """Remove a global log handler"""
        if handler in Log._handlers:
            Log._handlers.remove(handler)
