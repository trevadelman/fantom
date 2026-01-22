#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

# Fantom sys pod - Python implementation
import sys as _python_sys
import builtins as _builtins
from types import ModuleType as _ModuleType

# =============================================================================
# Import Caching Optimization
# =============================================================================
# The transpiler generates __import__('fan.pod.Type', fromlist=['Type']).Type
# for same-pod type references to avoid circular imports. During xeto namespace
# creation, this results in 3.6 million __import__ calls, taking ~13 seconds.
# By caching __import__ results, we reduce this to ~6 seconds (52% faster).
# Cache only needs ~250 entries for unique module/fromlist combinations.
#
# IMPORTANT: Cache is stored in builtins so it survives module clearing/reloading.

# Only install cache once (check if already installed)
if not hasattr(_builtins, '_fan_import_cache'):
    _builtins._fan_import_cache = {}
    _builtins._fan_original_import = _builtins.__import__

    def _cached_import(name, globals=None, locals=None, fromlist=(), level=0):
        """Cached __import__ for fan modules with fromlist.

        Only caches calls that match the transpiler pattern:
        __import__('fan.pod.Type', fromlist=['Type'])
        """
        # Only cache fan modules with explicit fromlist (transpiler pattern)
        if fromlist and name.startswith('fan.'):
            cache_key = (name, tuple(fromlist) if fromlist else None)
            cached = _builtins._fan_import_cache.get(cache_key)
            if cached is not None:
                return cached
            result = _builtins._fan_original_import(name, globals, locals, fromlist, level)
            _builtins._fan_import_cache[cache_key] = result
            return result
        return _builtins._fan_original_import(name, globals, locals, fromlist, level)

    _builtins.__import__ = _cached_import

# Expose cache for diagnostics
_import_cache = _builtins._fan_import_cache


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
