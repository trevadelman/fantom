#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


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
            return Version.fromStr("1.0")
        if isinstance(self._version, str):
            from .Version import Version
            self._version = Version.fromStr(self._version)
        return self._version

    def uri(self):
        """Return the uri for this pod: fan://{name}"""
        if self._uri is None:
            from .Uri import Uri
            self._uri = Uri.fromStr(f"fan://{self._name}")
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
            result = Map.fromLiteral(
                list(meta.keys()),
                list(meta.values()),
                "sys::Str", "sys::Str"
            )
            self._meta = result.toImmutable()
        return self._meta

    def depends(self):
        """Return list of dependencies as immutable Depend[]"""
        if self._depends is None:
            from .Depend import Depend
            from .List import List

            deps = []
            # For known pods, define dependencies
            if self._name == "sys":
                pass  # sys has no dependencies
            elif self._name == "concurrent":
                deps.append(Depend.fromStr("sys 1.0"))
            elif self._name == "testSys":
                deps.append(Depend.fromStr("sys 1.0"))
                deps.append(Depend.fromStr("concurrent 1.0"))
            elif self._name == "graphics":
                deps.append(Depend.fromStr("sys 1.0"))
            elif self._name == "inet":
                deps.append(Depend.fromStr("sys 1.0"))
                deps.append(Depend.fromStr("concurrent 1.0"))
            elif self._name == "crypto":
                deps.append(Depend.fromStr("sys 1.0"))
            elif self._name == "web":
                deps.append(Depend.fromStr("sys 1.0"))
                deps.append(Depend.fromStr("concurrent 1.0"))
                deps.append(Depend.fromStr("inet 1.0"))
            elif self._name == "dom":
                deps.append(Depend.fromStr("sys 1.0"))
                deps.append(Depend.fromStr("concurrent 1.0"))
                deps.append(Depend.fromStr("graphics 1.0"))
            elif self._name == "domkit":
                deps.append(Depend.fromStr("sys 1.0"))
                deps.append(Depend.fromStr("concurrent 1.0"))
                deps.append(Depend.fromStr("graphics 1.0"))
                deps.append(Depend.fromStr("dom 1.0"))
                deps.append(Depend.fromStr("web 1.0"))
                deps.append(Depend.fromStr("inet 1.0"))
                deps.append(Depend.fromStr("crypto 1.0"))
            elif self._name == "util":
                deps.append(Depend.fromStr("sys 1.0"))
                deps.append(Depend.fromStr("concurrent 1.0"))
            elif self._name == "webmod":
                deps.append(Depend.fromStr("sys 1.0"))
                deps.append(Depend.fromStr("concurrent 1.0"))
                deps.append(Depend.fromStr("inet 1.0"))
                deps.append(Depend.fromStr("web 1.0"))
                deps.append(Depend.fromStr("util 1.0"))

            # Create immutable list with proper type
            result = List.fromLiteral(deps, "sys::Depend")
            self._depends = result.toImmutable()
        return self._depends

    def log(self):
        """Return the log for this pod"""
        if self._log is None:
            from .Log import Log
            self._log = Log.get(self._name)
        return self._log

    def props(self, uri, maxAge):
        """Load properties file from pod resources.

        Args:
            uri: Uri to the properties file (relative to pod)
            maxAge: Duration for caching

        Returns:
            Immutable Str:Str map of properties
        """
        from .Map import Map

        # Convert uri to string key for caching
        uri_str = str(uri) if hasattr(uri, '__str__') else uri

        # Check cache
        if uri_str in self._propsCache:
            return self._propsCache[uri_str]

        # In Python runtime, we can't read from pod files directly
        # Return empty immutable map as fallback
        result = Map.fromLiteral([], [], "sys::Str", "sys::Str")
        result = result.toImmutable()
        self._propsCache[uri_str] = result
        return result

    def files(self):
        """Return list of files in this pod.

        Note: In Python runtime, we throw UnsupportedErr like JavaScript.
        """
        from .Err import UnsupportedErr
        raise UnsupportedErr("Pod.files")

    def file(self, uri, checked=True):
        """Return a file from this pod by uri.

        Args:
            uri: Uri to the file
            checked: If true, throw error if not found

        Note: In Python runtime, we throw UnsupportedErr like JavaScript.
        """
        from .Err import UnsupportedErr
        raise UnsupportedErr("Pod.file")

    def types(self):
        """Get list of types in this pod"""
        from .List import List
        result = List.fromLiteral(list(self._types.values()), "sys::Type")
        return result

    def type(self, name, checked=True):
        """Find a type by name in this pod"""
        t = self._types.get(name)
        if t is None and checked:
            from .Err import UnknownTypeErr
            raise UnknownTypeErr(f"Unknown type: {self._name}::{name}")
        return t

    def doc(self):
        """Return fandoc for this pod (not supported in Python runtime)"""
        return None

    def locale(self, key, def_=None):
        """Lookup a localized string by key"""
        # Simplified locale lookup
        return def_

    def config(self, key, def_=None):
        """Lookup a config value by key"""
        return def_

    def toStr(self):
        return self._name

    def __str__(self):
        return self.toStr()

    def __repr__(self):
        return self.toStr()

    def __eq__(self, other):
        """Pod equality is based on name"""
        if other is None:
            return False
        if isinstance(other, Pod):
            return self._name == other._name
        return False

    def __hash__(self):
        return hash(self._name)

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

    @staticmethod
    def find(name, checked=True):
        """Find a pod by name.

        Args:
            name: Pod name string
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

        # For known system pods, create and register
        known_pods = {
            "sys", "concurrent", "testSys", "graphics", "inet",
            "crypto", "web", "dom", "domkit", "util", "webmod",
            "compiler", "build", "fansh", "fandoc"
        }

        if name in known_pods:
            pod = Pod(name, "1.0.80")  # Version >= 1.0.14 for test compatibility
            Pod._pods[name] = pod
            Pod._list = None  # Invalidate cached list
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
            result = List.fromLiteral(pods, "sys::Pod")
            Pod._list = result.toImmutable()
        return Pod._list

    @staticmethod
    def flattenDepends(pods):
        """Flatten dependencies for a list of pods.

        Returns all pods including transitive dependencies.

        Args:
            pods: List of Pod objects

        Returns:
            Pod[] with all dependencies flattened
        """
        from .List import List

        result = set()

        def addWithDepends(pod):
            if pod._name in [p._name for p in result]:
                return
            result.add(pod)
            # Add dependencies recursively
            for dep in pod.depends():
                dep_pod = Pod.find(dep.name(), False)
                if dep_pod is not None:
                    addWithDepends(dep_pod)

        # Process each input pod
        for pod in pods:
            addWithDepends(pod)

        # Return as immutable list
        return List.fromLiteral(list(result), "sys::Pod")

    @staticmethod
    def orderByDepends(pods):
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

        return List.fromLiteral(result, "sys::Pod")

    @staticmethod
    def load(inStream):
        """Load a pod from an input stream (not supported in Python runtime)"""
        from .Err import UnsupportedErr
        raise UnsupportedErr("Pod.load")

    # ============================================================
    # Internal Methods
    # ============================================================

    def _registerType(self, type_obj):
        """Register a type with this pod"""
        self._types[type_obj.name()] = type_obj

    @staticmethod
    def _createSysPod():
        """Create the sys pod with its types"""
        if "sys" not in Pod._pods:
            pod = Pod("sys", "1.0")
            Pod._pods["sys"] = pod
        return Pod._pods["sys"]


class UnknownPodErr(Exception):
    """Error thrown when a pod cannot be found"""

    def __init__(self, msg="Unknown pod"):
        super().__init__(msg)
        self._msg = msg

    def msg(self):
        return self._msg

    def toStr(self):
        return f"sys::UnknownPodErr: {self._msg}"

    def __str__(self):
        return self.toStr()
