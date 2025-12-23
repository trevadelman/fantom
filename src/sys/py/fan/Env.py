#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Env(Obj):
    """Env stub for bootstrap - returns 'py' runtime"""

    _instance = None

    @staticmethod
    def cur():
        if Env._instance is None:
            Env._instance = Env()
        return Env._instance

    def runtime(self):
        return "py"

    def args(self):
        """Get command line arguments as immutable Str list.

        Returns args passed to program (excluding script name).
        """
        import sys
        from .List import List
        # sys.argv[0] is script name, sys.argv[1:] are args
        args_list = sys.argv[1:] if len(sys.argv) > 1 else []
        result = List.fromLiteral(args_list, "sys::Str")
        return result.toImmutable()

    def idHash(self, obj):
        """Get identity hash code for object.

        Returns the same value for the lifetime of the object.
        """
        if obj is None:
            return 0
        return id(obj)

    def path(self):
        """Get search path for files.

        Returns list of directories to search for files.
        The first is workDir, last is homeDir.
        """
        from .List import List
        # Default path is workDir then homeDir
        work = self.workDir()
        home = self.homeDir()
        # workDir and homeDir might be the same
        if work == home:
            result = List.fromLiteral([work], "sys::File")
        else:
            result = List.fromLiteral([work, home], "sys::File")
        return result.toImmutable()

    def os(self):
        """Get operating system name.

        Normalized to Fantom values: win32, macosx, linux, aix, solaris, hpux, qnx
        """
        import platform
        sys_name = platform.system().lower()
        # Map Python platform names to Fantom names
        os_map = {
            'darwin': 'macosx',
            'windows': 'win32',
            'linux': 'linux',
            'aix': 'aix',
            'sunos': 'solaris',
            'hp-ux': 'hpux',
            'qnx': 'qnx',
        }
        return os_map.get(sys_name, sys_name)

    def arch(self):
        """Get CPU architecture.

        Normalized to Fantom values: x86, x86_64, ppc, sparc, ia64, ia64_32, aarch64
        """
        import platform
        machine = platform.machine().lower()
        # Map Python machine names to Fantom names
        arch_map = {
            'x86_64': 'x86_64',
            'amd64': 'x86_64',
            'x86': 'x86',
            'i386': 'x86',
            'i686': 'x86',
            'arm64': 'aarch64',
            'aarch64': 'aarch64',
            'ppc': 'ppc',
            'ppc64': 'ppc',
            'sparc': 'sparc',
            'sparc64': 'sparc',
            'ia64': 'ia64',
        }
        return arch_map.get(machine, machine)

    def platform(self):
        """Get platform string as os-arch."""
        return f"{self.os()}-{self.arch()}"

    def host(self):
        import socket
        return socket.gethostname()

    def user(self):
        import os
        return os.environ.get("USER", "unknown")

    def homeDir(self):
        """Get Fantom installation home directory as File.

        This is the root directory containing bin/, lib/, etc/ subdirectories.
        Looks for FAN_HOME env var, then tries to find it relative to runtime.
        """
        import os
        from pathlib import Path
        from .File import File

        # Check FAN_HOME environment variable first
        fan_home = os.environ.get("FAN_HOME")
        if fan_home:
            return File.os(fan_home + os.sep)

        # Try to find fan/ directory relative to this module
        # This file is at: fan/src/sys/py/fan/Env.py (hand-written)
        # or at: fan/gen/py/fan/sys/Env.py (generated)
        # In either case, we want to find the fan/ root directory
        module_dir = Path(__file__).resolve().parent

        # Walk up looking for a directory with lib/fan/ subdirectory
        current = module_dir
        for _ in range(10):  # Limit search depth
            lib_fan = current / "lib" / "fan"
            if lib_fan.exists() and lib_fan.is_dir():
                return File.os(str(current) + os.sep)
            if current.parent == current:  # Reached root
                break
            current = current.parent

        # Final fallback: use current working directory
        return File.os(os.getcwd() + os.sep)

    def workDir(self):
        """Get current working directory as File."""
        import os
        from .File import File
        return File.os(os.getcwd() + os.sep)

    def tempDir(self):
        """Get temp directory as File."""
        import os
        import tempfile
        from .File import File
        return File.os(tempfile.gettempdir() + os.sep)

    def vars(self):
        """Return environment variables as a Map[Str,Str].

        Returns an immutable, case-insensitive Map containing environment variables.
        Includes os.name, os.version, user.name, user.home for Java compatibility.
        """
        import os
        import platform
        from .Map import Map

        # Create a case-insensitive map with proper type signature
        env_map = Map.makeWithType("sys::Str", "sys::Str")
        env_map.caseInsensitive = True

        # Add Python environment variables
        for key, value in os.environ.items():
            env_map.set(key, value)

        # Add Java-compatible system properties that tests expect
        # os.name - OS name
        sys_name = platform.system()
        if sys_name == 'Darwin':
            os_name = 'Mac OS X'
        elif sys_name == 'Windows':
            os_name = 'Windows'
        else:
            os_name = sys_name
        env_map.set("os.name", os_name)

        # os.version - OS version
        env_map.set("os.version", platform.release())

        # user.name - Current user
        env_map.set("user.name", os.environ.get("USER", os.environ.get("USERNAME", "unknown")))

        # user.home - User home directory
        env_map.set("user.home", os.path.expanduser("~"))

        return env_map.toImmutable()

    def findFile(self, uri, checked=True):
        """Find a file in the environment path.

        Searches workDir then homeDir for the given URI.

        Args:
            uri: Relative URI to search for
            checked: If true, throw UnresolvedErr if not found

        Returns:
            File if found, None if not found and checked=False
        """
        from .Uri import Uri
        from .Err import ArgErr, UnresolvedErr

        # Convert to Uri if string
        if isinstance(uri, str):
            uri = Uri.fromStr(uri)

        # Must be relative URI
        if uri.isAbs():
            raise ArgErr.make(f"Uri must be relative: {uri}")

        # Search path directories
        for dir_file in self.path():
            try:
                candidate = dir_file.plus(uri, False)  # checkSlash=False
                if candidate.exists():
                    return candidate
            except:
                continue

        # Not found
        if checked:
            raise UnresolvedErr.make(f"File not found in path: {uri}")
        return None

    def findAllFiles(self, uri):
        """Find all files matching URI in the environment path.

        Args:
            uri: Relative URI to search for

        Returns:
            List of matching Files (may be empty)
        """
        from .Uri import Uri
        from .List import List
        from .Err import ArgErr

        # Convert to Uri if string
        if isinstance(uri, str):
            uri = Uri.fromStr(uri)

        # Must be relative URI
        if uri.isAbs():
            raise ArgErr.make(f"Uri must be relative: {uri}")

        result = []
        # Search all path directories
        for dir_file in self.path():
            try:
                candidate = dir_file.plus(uri, False)  # checkSlash=False
                if candidate.exists():
                    result.append(candidate)
            except:
                continue

        return List.fromLiteral(result, "sys::File")

    def props(self, pod, uri, maxAge):
        """Load props file with caching.

        Args:
            pod: Pod to load props for
            uri: Uri of props file relative to etc/{pod}/
            maxAge: Maximum cache age (Duration)

        Returns:
            Immutable Map[Str,Str] of properties
        """
        from .Map import Map
        from .Duration import Duration
        import time

        # Initialize cache if needed
        if not hasattr(self, '_propsCache'):
            self._propsCache = {}

        # Build cache key
        pod_name = pod.name() if hasattr(pod, 'name') else str(pod)
        cache_key = f"{pod_name}:{uri}"

        # Check cache
        now = time.time()
        if cache_key in self._propsCache:
            cached_time, cached_props = self._propsCache[cache_key]
            max_age_secs = maxAge.toMillis() / 1000.0 if hasattr(maxAge, 'toMillis') else float(maxAge) / 1e9
            if now - cached_time < max_age_secs:
                return cached_props

        # Build file path: etc/{pod}/{uri}
        etc_dir = self.workDir().plus(f"etc/{pod_name}/", False)
        props_file = etc_dir.plus(uri, False)

        # Load props - create properly typed empty map if file not found
        props = Map.makeWithType("sys::Str", "sys::Str")
        if props_file.exists():
            loaded = props_file.readProps()
            for k, v in loaded.items():
                props.set(k, v)

        # Make immutable and cache
        result = props.toImmutable()
        self._propsCache[cache_key] = (now, result)

        return result

    def config(self, pod, key, defVal=None):
        """Get pod configuration value.

        Args:
            pod: Pod to get config for
            key: Config key
            defVal: Default value if not found

        Returns:
            Config value or default
        """
        # Load from etc/{pod}/config.props
        pod_name = pod.name() if hasattr(pod, 'name') else str(pod)
        etc_file = self.workDir().plus(f"etc/{pod_name}/config.props", False)

        if etc_file.exists():
            props = etc_file.readProps()
            val = props.get(key, None)
            if val is not None:
                return val

        return defVal

    # Sentinel value to detect "no default provided"
    _LOCALE_NO_DEFAULT = object()

    def locale(self, pod, key, defVal=_LOCALE_NO_DEFAULT, locale=None):
        """Get localized string.

        Args:
            pod: Pod to get locale for
            key: Locale key
            defVal: Default value if not found. If not provided, returns pod::key pattern
            locale: Locale to use (default: Locale.cur)

        Returns:
            Localized string, default, or pod::key pattern
        """
        from .Locale import Locale
        from .File import File

        # Get locale
        if locale is None:
            locale = Locale.cur()

        pod_name = pod.name() if hasattr(pod, 'name') else str(pod)

        lang = locale.lang()
        country = locale.country() if hasattr(locale, 'country') else None

        # Build list of files to check, in order of precedence:
        # 1. etc/{pod}/locale/{lang}-{country}.props (overrides)
        # 2. etc/{pod}/locale/{lang}.props (overrides)
        # 3. Pod's bundled locale/{lang}-{country}.props
        # 4. Pod's bundled locale/{lang}.props
        # 5. Fallback to English
        files_to_check = []

        # Check etc/{pod}/locale/ first (overrides)
        etc_locale = self.workDir().plus(f"etc/{pod_name}/locale/", False)
        if country:
            files_to_check.append(etc_locale.plus(f"{lang}-{country}.props", False))
        files_to_check.append(etc_locale.plus(f"{lang}.props", False))

        # Check pod's bundled locale files (fan/src/{pod}/locale/)
        home = self.homeDir()
        pod_locale = home.plus(f"src/{pod_name}/locale/", False)
        if country:
            files_to_check.append(pod_locale.plus(f"{lang}-{country}.props", False))
        files_to_check.append(pod_locale.plus(f"{lang}.props", False))

        # Fallback to English from both locations
        files_to_check.append(etc_locale.plus("en.props", False))
        files_to_check.append(pod_locale.plus("en.props", False))

        # Check each file
        for props_file in files_to_check:
            try:
                if props_file.exists():
                    props = props_file.readProps()
                    val = props.get(key, None)
                    if val is not None:
                        return val
            except:
                continue

        # Key not found - return based on whether defVal was provided
        if defVal is not Env._LOCALE_NO_DEFAULT:
            # defVal was explicitly provided (including None)
            return defVal
        # No defVal provided - return pod::key pattern
        return f"{pod_name}::{key}"

    def out(self):
        """Get standard output stream as OutStream."""
        if not hasattr(self, '_out'):
            self._out = SysOutStream()
        return self._out

    def err(self):
        """Get standard error stream as OutStream."""
        if not hasattr(self, '_err'):
            self._err = SysErrStream()
        return self._err

    def in_(self):
        """Get standard input stream as InStream."""
        if not hasattr(self, '_in'):
            self._in = SysInStream()
        return self._in


class SysOutStream:
    """OutStream wrapper for sys.stdout."""

    def write(self, b):
        import sys
        sys.stdout.buffer.write(bytes([b & 0xFF]))
        return self

    def writeChars(self, s, off=0, length=None):
        import sys
        if length is None:
            sys.stdout.write(str(s)[off:])
        else:
            sys.stdout.write(str(s)[off:off+length])
        return self

    def print_(self, obj):
        import sys
        sys.stdout.write(str(obj) if obj is not None else "")
        return self

    print = print_

    def printLine(self, obj=None):
        import sys
        if obj is not None:
            sys.stdout.write(str(obj))
        sys.stdout.write("\n")
        return self

    def flush(self):
        import sys
        sys.stdout.flush()
        return self

    def close(self):
        return True


class SysErrStream:
    """OutStream wrapper for sys.stderr."""

    def write(self, b):
        import sys
        sys.stderr.buffer.write(bytes([b & 0xFF]))
        return self

    def writeChars(self, s, off=0, length=None):
        import sys
        if length is None:
            sys.stderr.write(str(s)[off:])
        else:
            sys.stderr.write(str(s)[off:off+length])
        return self

    def print_(self, obj):
        import sys
        sys.stderr.write(str(obj) if obj is not None else "")
        return self

    print = print_

    def printLine(self, obj=None):
        import sys
        if obj is not None:
            sys.stderr.write(str(obj))
        sys.stderr.write("\n")
        return self

    def flush(self):
        import sys
        sys.stderr.flush()
        return self

    def close(self):
        return True


class SysInStream:
    """InStream wrapper for sys.stdin."""

    def read(self):
        import sys
        b = sys.stdin.buffer.read(1)
        if not b:
            return None
        return b[0]

    def readLine(self, max_chars=None):
        import sys
        line = sys.stdin.readline()
        if not line:
            return None
        # Remove trailing newline
        return line.rstrip('\n\r')

    def readAllStr(self):
        import sys
        return sys.stdin.read()

    def close(self):
        return True
