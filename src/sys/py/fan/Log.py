#
# Log - Logging support for Fantom
#
import logging
from fan.sys.Obj import Obj
from fan.sys.LogLevel import LogLevel
from fan.sys.LogRec import LogRec


class Log(Obj):
    """
    Log provides logging functionality.
    """

    _logs = {}
    _handlers = None  # Initialized in _init_handlers below
    _handlers_initialized = False

    @staticmethod
    def _init_handlers():
        """Initialize default handlers if not done yet - matches JS default handler."""
        if not Log._handlers_initialized:
            # Default console handler - matches JS: (rec) => { rec.print(); }
            # Must wrap in Func so Type.of() returns sys::Func not sys::function
            from fan.sys.Func import Func
            from fan.sys.Param import Param
            from fan.sys.Type import Type
            console_handler = Func.make_closure(
                {'returns': 'sys::Void', 'params': [{'name': 'rec', 'type': 'sys::LogRec'}], 'immutable': 'always'},
                lambda rec: rec.print_()
            )
            Log._handlers = [console_handler]
            Log._handlers_initialized = True

    def __init__(self, name, register=True):
        """Create a new log. If register=True, adds to global registry."""
        # Validate name
        if not Log._is_valid_name(name):
            from fan.sys.Err import NameErr
            raise NameErr(f"Invalid log name: {name}")

        # Check for duplicate registration
        if register and name in Log._logs:
            from fan.sys.Err import ArgErr
            raise ArgErr(f"Log already registered: {name}")

        self._name = name
        self._level = LogLevel.info()
        self._pyLogger = logging.getLogger(name)

        if register:
            Log._logs[name] = self

    @staticmethod
    def _is_valid_name(name):
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
        if not Log._is_valid_name(name):
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
        return List.from_literal(list(Log._logs.values()), "sys::Log")

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

    def is_enabled(self, level):
        """Check if level is enabled"""
        return level._ordinal >= self._level._ordinal

    def is_debug(self):
        return self._level._ordinal <= LogLevel.debug()._ordinal

    def is_info(self):
        return self._level._ordinal <= LogLevel.info()._ordinal

    def is_warn(self):
        return self._level._ordinal <= LogLevel.warn()._ordinal

    def is_err(self):
        return self._level._ordinal <= LogLevel.err()._ordinal

    def debug(self, msg, err=None):
        """Log debug message"""
        if self.is_enabled(LogLevel.debug()):
            self._log(LogLevel.debug(), msg, err)

    def info(self, msg, err=None):
        """Log info message"""
        if self.is_enabled(LogLevel.info()):
            self._log(LogLevel.info(), msg, err)

    def warn(self, msg, err=None):
        """Log warning message"""
        if self.is_enabled(LogLevel.warn()):
            self._log(LogLevel.warn(), msg, err)

    def err(self, msg, err=None):
        """Log error message"""
        if self.is_enabled(LogLevel.err()):
            self._log(LogLevel.err(), msg, err)

    def _log(self, level, msg, err):
        """Internal log method - creates LogRec and calls log()"""
        from fan.sys.DateTime import DateTime
        time = DateTime.now()
        rec = LogRec(time, level, self._name, msg, err)
        # Call the overrideable log method
        self.log(rec)

    def log(self, rec):
        """Log a record - can be overridden by subclasses"""
        # Ensure handlers are initialized
        Log._init_handlers()
        # Call global handlers
        for handler in Log._handlers:
            try:
                handler(rec)
            except:
                pass

        # Map to Python logging level by ordinal
        level = rec._level
        py_level_map = {
            0: logging.DEBUG,   # debug ordinal
            1: logging.INFO,    # info ordinal
            2: logging.WARNING, # warn ordinal
            3: logging.ERROR    # err ordinal
        }
        py_level = py_level_map.get(level._ordinal, logging.INFO)

        self._pyLogger.log(py_level, rec._msg)
        if rec._err:
            self._pyLogger.exception(rec._err)

    def to_str(self):
        return self._name

    @staticmethod
    def handlers():
        """Get global log handlers"""
        Log._init_handlers()
        from fan.sys.List import List
        return List.from_literal(list(Log._handlers), "|sys::LogRec->sys::Void|")

    @staticmethod
    def add_handler(handler):
        """Add a global log handler"""
        # Check immutability
        from fan.sys.ObjUtil import ObjUtil
        if not ObjUtil.is_immutable(handler):
            from fan.sys.Err import NotImmutableErr
            raise NotImmutableErr("Handler must be immutable")
        Log._handlers.append(handler)

    @staticmethod
    def remove_handler(handler):
        """Remove a global log handler"""
        if handler in Log._handlers:
            Log._handlers.remove(handler)
