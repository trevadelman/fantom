#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Env(Obj):
    """Env stub for bootstrap - returns 'py' runtime"""

    _instance = None
    _creating = False  # Guard against recursive creation

    def __init__(self, parent=None):
        """Initialize Env with optional parent.

        In Fantom, Env uses a parent chain pattern where child envs
        delegate to their parent. PathEnv extends Env and passes
        Env.cur() as its parent.
        """
        super().__init__()
        self._parent = parent

    @staticmethod
    def cur():
        if Env._instance is None:
            # Guard against recursive calls during PathEnv creation
            # (PathEnv.__init__ calls super().__init__(Env.cur()))
            if Env._creating:
                # Return a base Env during PathEnv construction
                return Env.__new__(Env)

            # Check for fan.props to determine if we should use PathEnv
            # This matches the Java pattern where PathEnv is used when fan.props exists
            fan_props = Env._find_fan_props_file()
            if fan_props:
                # Lazy import to avoid circular dependency
                try:
                    from fan.util.PathEnv import PathEnv
                    Env._creating = True
                    try:
                        Env._instance = PathEnv.make_props(fan_props)
                    finally:
                        Env._creating = False
                except ImportError:
                    # PathEnv not available (e.g., util pod not transpiled yet)
                    Env._instance = Env()
            else:
                Env._instance = Env()
        return Env._instance

    @staticmethod
    def _find_fan_props_file():
        """Find fan.props file walking up from current directory.

        Returns File object if found, None otherwise.
        """
        from pathlib import Path
        import os

        try:
            from .File import File

            current = Path(os.getcwd())
            while current != current.parent:
                fan_props = current / "fan.props"
                if fan_props.exists():
                    return File.os(str(fan_props))
                current = current.parent
        except Exception:
            pass
        return None

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
        result = List.from_literal(args_list, "sys::Str")
        return result.to_immutable()

    def id_hash(self, obj):
        """Get identity hash code for object.

        Returns the same value for the lifetime of the object.
        """
        if obj is None:
            return 0
        return id(obj)

    def path(self):
        """Get search path for files.

        Returns list of directories to search for files.
        Base Env returns [workDir, homeDir]. PathEnv overrides this
        to include paths from fan.props.
        """
        from .List import List

        # Default path is workDir then homeDir
        work = self.work_dir()
        home = self.home_dir()
        # workDir and homeDir might be the same
        if work == home:
            result = List.from_literal([work], "sys::File")
        else:
            result = List.from_literal([work, home], "sys::File")
        return result.to_immutable()

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

    def is_browser(self):
        """Return if running in a browser environment. Always False for Python."""
        return False

    def host(self):
        import socket
        return socket.gethostname()

    def user(self):
        import os
        return os.environ.get("USER", "unknown")

    def home_dir(self):
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

    def work_dir(self):
        """Get current working directory as File."""
        import os
        from .File import File
        return File.os(os.getcwd() + os.sep)

    def temp_dir(self):
        """Get temp directory as File."""
        import os
        import tempfile
        from .File import File
        return File.os(tempfile.gettempdir() + os.sep)

    def vars_(self):
        """Return environment variables as a Map[Str,Str].

        Returns an immutable, case-insensitive Map containing environment variables.
        Includes os.name, os.version, user.name, user.home for Java compatibility.
        """
        import os
        import platform
        from .Map import Map

        # Create a case-insensitive map with proper type signature
        env_map = Map.make_with_type("sys::Str", "sys::Str")
        env_map.caseInsensitive = True

        # Add Python environment variables
        for key, value in os.environ.items():
            env_map.set_(key, value)

        # Add Java-compatible system properties that tests expect
        # os.name - OS name
        sys_name = platform.system()
        if sys_name == 'Darwin':
            os_name = 'Mac OS X'
        elif sys_name == 'Windows':
            os_name = 'Windows'
        else:
            os_name = sys_name
        env_map.set_("os.name", os_name)

        # os.version - OS version
        env_map.set_("os.version", platform.release())

        # user.name - Current user
        env_map.set_("user.name", os.environ.get("USER", os.environ.get("USERNAME", "unknown")))

        # user.home - User home directory
        env_map.set_("user.home", os.path.expanduser("~"))

        return env_map.to_immutable()

    def find_file(self, uri, checked=True):
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
            uri = Uri.from_str(uri)

        # Must be relative URI
        if uri.is_abs():
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

    def find_all_files(self, uri):
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
            uri = Uri.from_str(uri)

        # Must be relative URI
        if uri.is_abs():
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

        return List.from_literal(result, "sys::File")

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
            max_age_secs = maxAge.to_millis() / 1000.0 if hasattr(maxAge, 'to_millis') else float(maxAge) / 1e9
            if now - cached_time < max_age_secs:
                return cached_props

        # Build file path: etc/{pod}/{uri}
        etc_dir = self.work_dir().plus(f"etc/{pod_name}/", False)
        props_file = etc_dir.plus(uri, False)

        # Load props - create properly typed empty map if file not found
        props = Map.make_with_type("sys::Str", "sys::Str")
        if props_file.exists():
            loaded = props_file.read_props()
            for k, v in loaded.items():
                props.set_(k, v)

        # Make immutable and cache
        result = props.to_immutable()
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
        etc_file = self.work_dir().plus(f"etc/{pod_name}/config.props", False)

        if etc_file.exists():
            props = etc_file.read_props()
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
        etc_locale = self.work_dir().plus(f"etc/{pod_name}/locale/", False)
        if country:
            files_to_check.append(etc_locale.plus(f"{lang}-{country}.props", False))
        files_to_check.append(etc_locale.plus(f"{lang}.props", False))

        # Check pod's bundled locale files (fan/src/{pod}/locale/)
        home = self.home_dir()
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
                    props = props_file.read_props()
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

    #################################################################
    # Pod Index System
    #################################################################

    def _load_index(self):
        """Load index.props from all pods and build index cache.

        The index maps keys to a dict of {pod_name: [values]}.
        """
        if hasattr(self, '_indexCache'):
            return

        import zipfile
        from pathlib import Path

        self._indexCache = {}  # key -> {pod_name -> [values]}
        self._indexKeysCache = None

        # Find all pod files in lib/fan/
        home = self.home_dir()
        lib_fan = home._path / "lib" / "fan"
        if not lib_fan.exists():
            return

        # Find path to generated Python modules
        # Look for fan/gen/py/fan/{pod}/ directories
        gen_py_path = None
        for parent in [home._path, home._path.parent]:
            candidate = parent / "gen" / "py" / "fan"
            if candidate.exists():
                gen_py_path = candidate
                break

        pod_count = 0
        for pod_path in lib_fan.glob("*.pod"):
            pod_name = pod_path.stem
            pod_count += 1

            # Only include pods that have Python modules available
            # This filters out Java-only pods like testNative
            if gen_py_path:
                pod_py_dir = gen_py_path / pod_name
                if not pod_py_dir.exists():
                    continue  # Skip pods without Python code

            try:
                with zipfile.ZipFile(pod_path, 'r') as zf:
                    if 'index.props' in zf.namelist():
                        content = zf.read('index.props').decode('utf-8')
                        for line in content.strip().split('\n'):
                            line = line.strip()
                            if not line or line.startswith('#') or line.startswith('//'):
                                continue
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                if key not in self._indexCache:
                                    self._indexCache[key] = {}
                                if pod_name not in self._indexCache[key]:
                                    self._indexCache[key][pod_name] = []
                                self._indexCache[key][pod_name].append(value)
            except Exception as e:
                continue

    def index_keys(self):
        """Get all index keys as an immutable Str list.

        Returns:
            Immutable list of all unique index keys across all pods
        """
        from .List import List

        self._load_index()

        if self._indexKeysCache is None:
            keys = sorted(self._indexCache.keys())
            self._indexKeysCache = List.from_literal(keys, "sys::Str").to_immutable()

        return self._indexKeysCache

    def index(self, key):
        """Get all values for an index key across all pods.

        Args:
            key: The index key to lookup

        Returns:
            Immutable list of all values for this key (may be empty)
        """
        from .List import List

        self._load_index()

        # Check cache
        if not hasattr(self, '_indexResultCache'):
            self._indexResultCache = {}
        if key in self._indexResultCache:
            return self._indexResultCache[key]

        values = []
        if key in self._indexCache:
            for pod_name, pod_values in self._indexCache[key].items():
                values.extend(pod_values)

        result = List.from_literal(values, "sys::Str").to_immutable()
        self._indexResultCache[key] = result
        return result

    def index_pod_names(self, key):
        """Get names of all pods that have the given index key.

        Args:
            key: The index key to lookup

        Returns:
            Immutable list of pod names that have this key
        """
        from .List import List

        self._load_index()

        # Check cache
        if not hasattr(self, '_indexPodNamesCache'):
            self._indexPodNamesCache = {}
        if key in self._indexPodNamesCache:
            return self._indexPodNamesCache[key]

        pod_names = []
        if key in self._indexCache:
            pod_names = sorted(self._indexCache[key].keys())

        result = List.from_literal(pod_names, "sys::Str").to_immutable()
        self._indexPodNamesCache[key] = result
        return result

    def index_by_pod_name(self, key):
        """Get values for an index key grouped by pod name.

        Args:
            key: The index key to lookup

        Returns:
            Immutable map of pod name to list of values
        """
        from .List import List
        from .Map import Map

        self._load_index()

        # Check cache
        if not hasattr(self, '_indexByPodNameCache'):
            self._indexByPodNameCache = {}
        if key in self._indexByPodNameCache:
            return self._indexByPodNameCache[key]

        result = Map.make_with_type("sys::Str", "sys::Str[]")
        if key in self._indexCache:
            for pod_name, pod_values in self._indexCache[key].items():
                values_list = List.from_literal(pod_values, "sys::Str").to_immutable()
                result.set_(pod_name, values_list)

        result = result.to_immutable()
        self._indexByPodNameCache[key] = result
        return result

    #################################################################
    # Standard I/O
    #################################################################

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

    def write_chars(self, s, off=0, length=None):
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

    def print_line(self, obj=None):
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

    def write_chars(self, s, off=0, length=None):
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

    def print_line(self, obj=None):
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

    def read_line(self, max_chars=None):
        import sys
        line = sys.stdin.readline()
        if not line:
            return None
        # Remove trailing newline
        return line.rstrip('\n\r')

    def read_all_str(self):
        import sys
        return sys.stdin.read()

    def close(self):
        return True
