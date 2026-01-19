#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

# Fantom sys pod - Python implementation
import sys as _python_sys
from types import ModuleType as _ModuleType


class _SysModule(_ModuleType):
    """Custom module class that intercepts attribute access to fix submodule shadowing.

    When Python imports a submodule like fan.sys.Log, it automatically adds
    the module as an attribute: fan.sys.Log = <module 'fan.sys.Log'>.
    This shadows the intended class access.

    This custom module class intercepts __getattribute__ to detect when
    a module is being returned and instead returns the class from that module.
    """

    def __getattribute__(self, name):
        # Get the attribute normally first
        try:
            val = super().__getattribute__(name)
        except AttributeError:
            # Not found - trigger lazy loading via __getattr__
            raise

        # Check if it's a fan.sys submodule that shadows a class
        if isinstance(val, _ModuleType) and hasattr(val, '__name__'):
            mod_name = val.__name__
            if mod_name.startswith('fan.sys.') and not mod_name.startswith('fan.sys._'):
                type_name = mod_name.split('.')[-1]
                if name == type_name:
                    # Try to get the class from the module
                    cls = getattr(val, type_name, None)
                    if cls is not None and isinstance(cls, type):
                        # Cache the class for future access
                        object.__setattr__(self, name, cls)
                        return cls
        return val


# Replace this module's class with our custom class
_python_sys.modules[__name__].__class__ = _SysModule


# Base types
from .Obj import Obj
from .ObjUtil import ObjUtil

# Primitive types
from .Bool import Bool
from .Num import Num
from .Int import Int
from .Float import Float
from .Str import Str

# Collections
from .Range import Range
from .Map import Map
from .List import List

# Date/Time
from .Duration import Duration
from .Locale import Locale

# Reflection
from .Type import Type
from .Pod import Pod
from .Slot import Slot
from .Method import Method
from .Field import Field
from .Func import Func

# Environment
from .Env import Env

# IO
from .Zip import Zip

# Testing
from .Test import Test

# Errors
from .Err import Err, ParseErr, NullErr, CastErr

# Unsafe wrapper for reassignable variables
from .Unsafe import Unsafe, make
from .OutStream import OutStream


def __getattr__(name):
    """Lazy load sys types that aren't explicitly imported above.

    When accessing sys.Log.get(), Python will:
    1. Look for 'Log' in this module's __dict__
    2. If not found, call __getattr__('Log')
    3. We import fan.sys.Log and return the Log class

    This is needed because the transpiler generates sys.TypeName.method()
    for all sys pod types, but not all are explicitly imported above.
    """
    import importlib

    try:
        # Import the module fan.sys.{name}
        module = importlib.import_module(f"fan.sys.{name}")
        # Get the class from the module (class has same name as module)
        cls = getattr(module, name)
        # Cache it in this module's namespace for future access
        globals()[name] = cls
        return cls
    except (ImportError, AttributeError):
        raise AttributeError(f"module 'fan.sys' has no attribute '{name}'")
