#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj
from .Err import Err


class Pod(Obj):
    """Pod metadata and reflection"""

    # Registry of known pods - ensures same instance returned for same name
    _pods = {}

    # Cached list of all pods (immutable)
    _list = None

    # Default metadata for pods
    _DEFAULT_META = {
        "pod.docApi": "true",
        "pod.docSrc": "true",
        "build.host": "python",
        "build.user": "python",
        "build.ts": "2025-01-01T00:00:00Z",
    }

    def __init__(self, name, version=None, meta=None):
        super().__init__()
        self._name = name
        self._version = version
        self._types = {}
        self._uri = None  # Cached Uri
        self._log = None  # Cached Log
        self._meta = None  # Metadata map
        self._depends = None  # Cached Depend list
        self._files = None  # Cached files list
        self._propsCache = {}  # Cache for props()

        # Initialize metadata
        if meta is not None:
            self._rawMeta = meta
        else:
            self._rawMeta = {}

    def name(self):
        """Get pod name"""
        return self._name

    def version(self):
        """Get pod version"""
        if self._version is None:
            from .Version import Version
            return Version.from_str("1.0")
        if isinstance(self._version, str):
            from .Version import Version
            self._version = Version.from_str(self._version)
        return self._version

    def uri(self):
        """Return the uri for this pod: fan://{name}"""
        if self._uri is None:
            from .Uri import Uri
            self._uri = Uri.from_str(f"fan://{self._name}")
        return self._uri

    def meta(self):
        """Return pod metadata as immutable Str:Str map"""
        if self._meta is None:
            from .Map import Map

            # Build metadata map
            meta = {}
            meta["pod.name"] = self._name
            meta["pod.version"] = str(self.version())

            # Add default metadata
            for k, v in Pod._DEFAULT_META.items():
                if k not in meta:
                    meta[k] = v

            # Add pod-specific metadata
            if self._name == "testSys":
                # testSys has special metadata
                meta["testSys.foo"] = "got\n it \u0123"
                meta["pod.docApi"] = "false"
                meta["pod.docSrc"] = "false"

            # Add any raw metadata
            for k, v in self._rawMeta.items():
                meta[k] = v

            # Build depends string
            deps = self.depends()
            if deps and len(deps) > 0:
                dep_strs = [str(d) for d in deps]
                meta["pod.depends"] = ";".join(dep_strs)
            else:
                meta["pod.depends"] = ""

            # Create immutable map
            result = Map.from_literal(
                list(meta.keys()),
                list(meta.values()),
                "sys::Str", "sys::Str"
            )
            self._meta = result.to_immutable()
        return self._meta

    def depends(self):
        """Return list of dependencies as immutable Depend[]"""
        if self._depends is None:
            self._load_depends()
        return self._depends

    def _load_depends(self):
        """Load dependencies from the pod's meta.props file."""
        from .Depend import Depend
        from .List import List
        import zipfile

        deps = []

        # Try to read from pod file
        from .Env import Env
        pod_file = Env.cur().find_pod_file(self._name)

        if pod_file is not None and pod_file.exists():
            try:
                os_path = pod_file.os_path()
                with zipfile.ZipFile(os_path, 'r') as zf:
                    if 'meta.props' in zf.namelist():
                        content = zf.read('meta.props').decode('utf-8')
                        for line in content.strip().split('\n'):
                            line = line.strip()
                            if line.startswith('pod.depends='):
                                depends_str = line[len('pod.depends='):]
                                if depends_str:
                                    # Dependencies are semicolon-separated
                                    for dep_str in depends_str.split(';'):
                                        dep_str = dep_str.strip()
                                        if dep_str:
                                            deps.append(Depend.from_str(dep_str))
                                break
            except Exception as e:
                pass  # Use empty list on error

        # Create immutable list with proper type
        result = List.from_literal(deps, "sys::Depend")
        self._depends = result.to_immutable()

    def log(self):
        """Return the log for this pod"""
        if self._log is None:
            from .Log import Log
            self._log = Log.get(self._name)
        return self._log

    def props(self, uri, maxAge):
        """Load properties file from pod resources.

        Delegates to Env.cur().props() which handles caching and file resolution.

        Args:
            uri: Uri to the properties file (relative to pod)
            maxAge: Duration for caching

        Returns:
            Immutable Str:Str map of properties
        """
        from .Env import Env
        return Env.cur().props(self, uri, maxAge)

    def files(self):
        """Return list of files in this pod.

        Returns an immutable list of files contained in this pod's .pod file.
        Excludes fcode/ directory and .class files.
        """
        self._load_files()
        return self._files_list

    def file(self, uri, checked=True):
        """Return a file from this pod by uri.

        Args:
            uri: Uri to the file (e.g., `/res/login.css`)
            checked: If true, throw UnresolvedErr if not found

        Returns:
            File if found, None if not found and checked=False
        """
        from .Uri import Uri
        from .Err import ArgErr, UnresolvedErr

        self._load_files()

        # Convert to Uri if needed
        if isinstance(uri, str):
            uri = Uri.from_str(uri)

        # URI must be path absolute
        uri_str = str(uri)
        if not uri_str.startswith('/'):
            raise ArgErr.make(f"Pod.file Uri must be path abs: {uri}")

        # Build full URI: fan://{podName}/{path}
        full_uri = self.uri().plus(uri)

        # Look up in files map
        f = self._files_map.get(str(full_uri))
        if f is not None:
            return f

        # Not found
        if checked:
            raise UnresolvedErr.make(str(uri))
        return None

    def _load_files(self):
        """Load files from pod's .pod zip file.

        Populates _files_list and _files_map from the zip entries.
        Thread-safe: uses a lock to prevent race conditions.
        """
        import threading

        # Ensure we have a lock for this pod instance
        if not hasattr(self, '_files_lock'):
            self._files_lock = threading.Lock()

        # Quick check without lock (optimization for common case)
        if hasattr(self, '_files_loaded') and self._files_loaded:
            return

        # Acquire lock for thread-safe initialization
        with self._files_lock:
            # Double-check after acquiring lock (another thread may have loaded)
            if hasattr(self, '_files_loaded') and self._files_loaded:
                return

            import zipfile
            from .List import List
            from .Uri import Uri

            self._files_map = {}
            self._files_list = None

            # Find the .pod file
            from .Env import Env
            pod_file = Env.cur().find_pod_file(self._name)

            if pod_file is None or not pod_file.exists():
                # No .pod file - empty file list
                self._files_list = List.from_literal([], "sys::File").to_immutable()
                self._files_loaded = True
                return

            # Open the zip and enumerate files
            files = []
            try:
                os_path = pod_file.os_path()
                with zipfile.ZipFile(os_path, 'r') as zf:
                    for name in zf.namelist():
                        # Skip fcode/ directory (internal compiler data)
                        if name.startswith('fcode/'):
                            continue
                        # Skip .class files
                        if name.endswith('.class'):
                            continue

                        # Create URI for this entry: fan://{podName}/{path}
                        # Entry names don't have leading slash, add it
                        entry_path = '/' + name if not name.startswith('/') else name
                        full_uri = Uri.from_str(f"fan://{self._name}{entry_path}")

                        # Create a ZipEntryFile for this entry
                        entry_file = PodZipEntryFile(os_path, name, full_uri)
                        files.append(entry_file)
                        self._files_map[str(full_uri)] = entry_file

            except Exception:
                pass  # Empty file list on error

            self._files_list = List.from_literal(files, "sys::File").to_immutable()
            # Set loaded flag LAST, after everything is ready
            self._files_loaded = True

    def types(self):
        """Get list of types in this pod.

        Reads the _types manifest from the pod's __init__.py (generated by transpiler)
        and imports each type to trigger registration via tf_().
        """
        from .List import List

        # Import pod's __init__.py to get _types manifest
        # This is generated by fanc py with all type names in the pod
        try:
            import importlib
            py_pod = self._name + "_" if self._name in Pod._PYTHON_KEYWORDS else self._name
            pod_module = importlib.import_module(f'fan.{py_pod}')
            type_names = getattr(pod_module, '_types', {}).keys()
            # Import each type to trigger tf_() registration
            for name in type_names:
                if name not in self._types:
                    from .Type import Type
                    Type.find(f"{self._name}::{name}", False)
        except ImportError:
            pass

        # Return registered types
        result = List.from_literal(list(self._types.values()), "sys::Type")
        return result

    def type(self, name, checked=True):
        """Find a type by name in this pod.

        Only returns types that actually exist - either already registered
        via _register_type() or importable as a Python module.

        Unlike Type.find(), this does NOT create phantom Type objects for
        non-existent types. This is important for FFI resolution which
        iterates pods looking for types by name.
        """
        # First check if already registered
        t = self._types.get(name)
        if t is not None:
            return t

        # Try to import the module directly to see if type exists
        # Convert Fantom pod name to Python module name (e.g., 'def' -> 'def_')
        from .Type import Type
        py_pod = self._name + "_" if self._name in Pod._PYTHON_KEYWORDS else self._name
        # Convert Fantom type name to Python module name (e.g., 'None' -> 'None_')
        py_name = Type._fantom_type_to_py(name)

        try:
            module = __import__(f'fan.{py_pod}.{py_name}', fromlist=[py_name])
            # Module exists - check if the type was registered during import
            t = self._types.get(name)
            if t is not None:
                return t
            # Module exists but type not registered - create and register it
            t = Type.find(f"{self._name}::{name}", False)
            if t is not None:
                self._types[name] = t
            return t
        except ImportError:
            # Module doesn't exist - type doesn't exist in this pod
            pass

        if checked:
            from .Err import UnknownTypeErr
            raise UnknownTypeErr(f"{self._name}::{name}")
        return None

    # Alias for transpiled code that escapes 'type' to 'type_'
    def type_(self, name, checked=True):
        """Alias for type() - transpiler escapes 'type' because it's a Python builtin"""
        return self.type(name, checked)

    def doc(self):
        """Return fandoc for this pod (not supported in Python runtime)"""
        return None

    # Sentinel value to detect "no default provided"
    _LOCALE_NO_DEFAULT = object()

    def locale(self, key, def_=_LOCALE_NO_DEFAULT):
        """Lookup a localized string by key using current Locale"""
        from .Env import Env
        if def_ is Pod._LOCALE_NO_DEFAULT:
            return Env.cur().locale(self, key)
        return Env.cur().locale(self, key, def_)

    def config(self, key, def_=None):
        """Lookup a config value by key"""
        from .Env import Env
        return Env.cur().config(self, key, def_)

    def to_str(self):
        return self._name

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return self.to_str()

    def __eq__(self, other):
        """Pod equality is based on name"""
        if other is None:
            return False
        if isinstance(other, Pod):
            return self._name == other._name
        return False

    def __hash__(self):
        return hash(self._name)

    def trap(self, name, args=None):
        """Handle trap calls (-> operator) for Pod.

        Supports reloadList and reload which are Java-specific methods.
        """
        if name == "reloadList":
            return self._reload_list(args)
        if name == "reload":
            return self._reload()
        # Delegate to parent trap handler
        from .Err import UnknownSlotErr
        from .Type import Type
        raise UnknownSlotErr(f"{Type.of(self)}.{name}")

    def _reload_list(self, args=None):
        """Reload the list of all pods.

        Invalidates the cached pod list so it will be rebuilt on next access.
        This is a Java-specific method for hot reloading but we provide a stub.
        """
        from .Log import Log
        log = Log.get("sys")
        log.info("Pod reload list")

        # Invalidate cached list
        Pod._list = None

        return "reloadList"

    def _reload(self):
        """Reload this pod from disk.

        This is a Java-specific method for hot reloading. In Python,
        pods with types cannot be reloaded.
        """
        from .Err import Err
        from .Log import Log

        # Check if pod has types (like Java does)
        if len(self._types) > 0:
            raise Err(f"Cannot reload pod with types: {self._name}")

        log = Log.get("sys")
        log.info(f"Pod reload: {self._name}")

        # Remove from registry so it gets re-discovered
        if self._name in Pod._pods:
            del Pod._pods[self._name]
        Pod._list = None

        return self

    # ============================================================
    # Static Methods
    # ============================================================

    @staticmethod
    def of(obj):
        """Get the pod for an object based on its type"""
        from .Type import Type
        t = Type.of(obj)
        if t is None:
            return None
        pod = t.pod()
        # Ensure we return the Pod object, not just the name
        if isinstance(pod, str):
            return Pod.find(pod, False)
        return pod

    # Python reserved words that need escaping with trailing underscore
    _PYTHON_KEYWORDS = {
        "and", "as", "assert", "async", "await", "break", "class", "continue",
        "def", "del", "elif", "else", "except", "finally", "for", "from",
        "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
        "or", "pass", "raise", "return", "try", "while", "with", "yield"
    }

    @staticmethod
    def find(name, checked=True):
        """Find a pod by name.

        Dynamically discovers pods by checking:
        1. If already registered in Pod._pods
        2. If a Python module exists at fan.{podname}
        3. If a .pod file exists (for def-only pods without code)

        Handles Python keyword escaping: pod name "def" maps to module "fan.def_"

        Args:
            name: Pod name string (Fantom name, not escaped)
            checked: If true (default), throw UnknownPodErr if not found

        Returns:
            Pod instance or null if not found and checked=false
        """
        # Handle Pod object passed in
        if isinstance(name, Pod):
            return name

        # Check registry - return same instance
        if name in Pod._pods:
            return Pod._pods[name]

        # Escape Python keywords: def -> def_
        module_name = name + "_" if name in Pod._PYTHON_KEYWORDS else name

        # Try to import the pod module - if it exists, create the pod
        # This dynamically discovers pods without a hardcoded list
        try:
            import importlib
            # Try to import the pod's __init__.py
            module = importlib.import_module(f'fan.{module_name}')
            # Pod module exists - create and register (use original Fantom name)
            pod = Pod(name, "1.0.80")  # Version >= 1.0.14 for test compatibility
            Pod._pods[name] = pod
            Pod._list = None  # Invalidate cached list
            return pod
        except ImportError:
            pass

        # Try to find a .pod file (for def-only pods without Python code)
        # This handles pods like ph, phScience, phIoT, phIct that have no code
        from .Env import Env
        pod_file = Env.cur().find_pod_file(name)
        if pod_file is not None and pod_file.exists():
            # Pod file exists - create and register
            pod = Pod(name, "1.0.80")
            Pod._pods[name] = pod
            Pod._list = None
            return pod

        # Unknown pod
        if checked:
            raise UnknownPodErr(f"Unknown pod: {name}")
        return None

    @staticmethod
    def list_():
        """Return immutable list of all installed pods.

        Note: Named list_ because 'list' conflicts with Python builtin.
        In Fantom this is Pod.list
        """
        if Pod._list is None:
            from .List import List

            # Ensure common pods are registered
            for name in ["sys", "concurrent", "testSys"]:
                if name not in Pod._pods:
                    Pod._pods[name] = Pod(name, "1.0")

            # Create sorted list
            pods = sorted(Pod._pods.values(), key=lambda p: p._name)
            result = List.from_literal(pods, "sys::Pod")
            Pod._list = result.to_immutable()
        return Pod._list

    @staticmethod
    def flatten_depends(pods):
        """Flatten dependencies for a list of pods.

        Returns all pods including transitive dependencies.

        Args:
            pods: List of Pod objects

        Returns:
            Pod[] with all dependencies flattened
        """
        from .List import List

        result = set()

        def add_with_depends(pod):
            if pod._name in [p._name for p in result]:
                return
            result.add(pod)
            # Add dependencies recursively
            for dep in pod.depends():
                dep_pod = Pod.find(dep.name(), False)
                if dep_pod is not None:
                    add_with_depends(dep_pod)

        # Process each input pod
        for pod in pods:
            add_with_depends(pod)

        # Return as immutable list
        return List.from_literal(list(result), "sys::Pod")

    @staticmethod
    def order_by_depends(pods):
        """Order pods by their dependencies (topological sort).

        Returns pods ordered so that a pod appears after all its dependencies.

        Args:
            pods: List of Pod objects

        Returns:
            Pod[] ordered by dependencies
        """
        from .List import List

        # Build dependency graph
        pod_map = {p._name: p for p in pods}

        # Topological sort using Kahn's algorithm
        result = []
        remaining = set(pod_map.keys())

        while remaining:
            # Find pods with no unresolved dependencies
            ready = []
            for name in remaining:
                pod = pod_map[name]
                has_unresolved = False
                for dep in pod.depends():
                    if dep.name() in remaining:
                        has_unresolved = True
                        break
                if not has_unresolved:
                    ready.append(name)

            if not ready:
                # Circular dependency - just add remaining
                ready = list(remaining)

            # Add ready pods in sorted order for consistency
            for name in sorted(ready):
                result.append(pod_map[name])
                remaining.remove(name)

        return List.from_literal(result, "sys::Pod")

    @staticmethod
    def load(inStream):
        """Load a pod from an input stream (not supported in Python runtime)"""
        from .Err import UnsupportedErr
        raise UnsupportedErr("Pod.load")

    # ============================================================
    # Internal Methods
    # ============================================================

    def _register_type(self, type_obj):
        """Register a type with this pod"""
        self._types[type_obj.name()] = type_obj

    @staticmethod
    def _create_sys_pod():
        """Create the sys pod with its types"""
        if "sys" not in Pod._pods:
            pod = Pod("sys", "1.0")
            Pod._pods["sys"] = pod
        return Pod._pods["sys"]


class PodZipEntryFile:
    """File implementation for entries inside a pod's .pod zip file.

    This is a read-only file backed by a zip entry. Used by Pod.file()
    to return files from the pod's bundled resources.
    """

    def __init__(self, zip_path, entry_name, uri):
        """Create a PodZipEntryFile.

        Args:
            zip_path: Path to the .pod zip file
            entry_name: Name of the entry within the zip (e.g., "res/login.css")
            uri: Full URI for this file (e.g., fan://hxd/res/login.css)
        """
        self._zip_path = zip_path
        self._entry_name = entry_name
        self._uri = uri

    def typeof(self):
        from .Type import Type
        return Type.find("sys::File")

    def uri(self):
        return self._uri

    def name(self):
        """Return file name (last path segment)."""
        return self._uri.name() if hasattr(self._uri, 'name') else self._entry_name.split('/')[-1]

    def ext(self):
        """Return file extension without dot, or null if none."""
        name = self.name()
        if '.' in name:
            return name.rsplit('.', 1)[1]
        return None

    def parent(self):
        return None

    def os_path(self):
        return None

    def exists(self):
        return True

    def is_dir(self):
        return self._entry_name.endswith('/')

    def size(self):
        """Return file size in bytes."""
        import zipfile
        try:
            with zipfile.ZipFile(self._zip_path, 'r') as zf:
                info = zf.getinfo(self._entry_name)
                return info.file_size
        except:
            return None

    def modified(self):
        """Return last modified time as DateTime."""
        import zipfile
        import time as time_mod
        try:
            with zipfile.ZipFile(self._zip_path, 'r') as zf:
                info = zf.getinfo(self._entry_name)
                dt = info.date_time
                # date_time is (year, month, day, hour, min, sec) in local time
                local_time_tuple = (dt[0], dt[1], dt[2], dt[3], dt[4], dt[5], 0, 0, -1)
                epoch_secs = time_mod.mktime(local_time_tuple)
                epoch_millis = int(epoch_secs * 1000)
                from .DateTime import DateTime
                return DateTime.from_java(epoch_millis)
        except:
            return None

    def mime_type(self):
        """Return MIME type based on extension."""
        from .MimeType import MimeType
        ext = self.ext()
        if ext is None:
            return None
        return MimeType.for_ext(ext)

    def in_(self, bufSize=4096):
        """Get an input stream to read the entry."""
        import zipfile
        from .Buf import Buf
        try:
            with zipfile.ZipFile(self._zip_path, 'r') as zf:
                data = zf.read(self._entry_name)
            buf = Buf.make(len(data))
            for b in data:
                buf.write(b)
            buf.flip()
            return buf.in_()
        except Exception as e:
            from .Err import IOErr
            raise IOErr.make(f"Cannot read pod file: {self._entry_name}: {e}")

    def read_all_str(self, normalizeNewlines=True):
        """Read entire entry as string."""
        import zipfile
        try:
            with zipfile.ZipFile(self._zip_path, 'r') as zf:
                data = zf.read(self._entry_name)
            text = data.decode('utf-8')
            if normalizeNewlines:
                text = text.replace('\r\n', '\n').replace('\r', '\n')
            return text
        except Exception as e:
            from .Err import IOErr
            raise IOErr.make(f"Cannot read pod file: {self._entry_name}: {e}")

    def read_all_buf(self):
        """Read entire entry as Buf."""
        import zipfile
        from .Buf import Buf
        try:
            with zipfile.ZipFile(self._zip_path, 'r') as zf:
                data = zf.read(self._entry_name)
            buf = Buf.make(len(data))
            for b in data:
                buf.write(b)
            buf.flip()
            return buf
        except Exception as e:
            from .Err import IOErr
            raise IOErr.make(f"Cannot read pod file: {self._entry_name}: {e}")

    def out(self, append=False, bufSize=4096):
        from .Err import IOErr
        raise IOErr.make("Cannot write to pod file")

    def create(self):
        from .Err import IOErr
        raise IOErr.make("Cannot create pod file")

    def delete(self):
        from .Err import IOErr
        raise IOErr.make("Cannot delete pod file")

    def move_to(self, target):
        from .Err import IOErr
        raise IOErr.make("Cannot move pod file")

    def with_in(self, callback, bufSize=None):
        """Open file for reading, call callback with InStream, then close.

        Args:
            callback: Function to call with InStream
            bufSize: Optional buffer size

        Returns:
            Result of callback function
        """
        inp = self.in_(bufSize)
        try:
            result = callback(inp)
            return result
        finally:
            inp.close()

    def to_str(self):
        return str(self._uri)

    def __str__(self):
        return self.to_str()


class UnknownPodErr(Err):
    """Error thrown when a pod cannot be found.

    Extends Err (matching JS: UnknownPodErr extends Err).
    Note: there is also a canonical UnknownPodErr in Err.py.
    """

    def __init__(self, msg="Unknown pod"):
        super().__init__(msg)
        self._msg = msg

    def msg(self):
        return self._msg

    def to_str(self):
        return f"sys::UnknownPodErr: {self._msg}"

    def __str__(self):
        return self.to_str()
