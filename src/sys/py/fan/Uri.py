#
# Uri - URI handling for Fantom
#
from urllib.parse import urlparse, quote, unquote, urlencode, parse_qs
from fan.sys.Obj import Obj

class Uri(Obj):
    """
    Uri represents a Uniform Resource Identifier.
    """

    # Cache of parsed URIs
    _cache = {}

    # Section constants (as class attributes for direct access)
    _sectionPath = 1
    _sectionQuery = 2
    _sectionFrag = 3

    @staticmethod
    def section_path():
        """Return Int constant for path section"""
        return 1

    @staticmethod
    def section_query():
        """Return Int constant for query section"""
        return 2

    @staticmethod
    def section_frag():
        """Return Int constant for fragment section"""
        return 3

    def __init__(self, scheme=None, userInfo=None, host=None, port=None,
                 pathStr="", queryStr=None, frag=None):
        self._scheme = scheme
        self._userInfo = userInfo
        self._host = host
        self._port = port
        self._pathStr = pathStr
        self._queryStr = queryStr
        self._frag = frag
        self._pathSegs = None  # Lazy parsed

    @staticmethod
    def from_str(s, checked=True):
        """Parse a URI from string"""
        if s in Uri._cache:
            return Uri._cache[s]

        try:
            # Preprocess: convert backslash escapes to percent encoding for urlparse
            # Fantom uses \# \? etc. but urlparse doesn't understand this
            preprocessed, had_escapes = Uri._preprocess_backslash_escapes(s)
            parsed = urlparse(preprocessed)
            # Parse userInfo and host from netloc - preserve host case
            userInfo = None
            host = None
            netloc = parsed.netloc

            if netloc:
                # Extract userInfo@host:port
                at_idx = netloc.find('@')
                if at_idx >= 0:
                    userInfo = netloc[:at_idx]
                    host_port = netloc[at_idx + 1:]
                else:
                    host_port = netloc

                # Extract host (preserve case) and port
                if host_port:
                    if host_port.startswith('['):
                        # IPv6 [host]:port
                        bracket_idx = host_port.find(']')
                        if bracket_idx >= 0:
                            host = host_port[:bracket_idx + 1]  # Include brackets
                            # Check for port after ]
                            rest = host_port[bracket_idx + 1:]
                            # port is parsed by urlparse
                        else:
                            host = host_port
                    elif ':' in host_port:
                        # Regular host:port
                        colon_idx = host_port.rfind(':')
                        host = host_port[:colon_idx]
                    else:
                        host = host_port

            # Get scheme (normalize to lowercase)
            scheme = parsed.scheme.lower() if parsed.scheme else None

            # Get port
            port = parsed.port

            # Normalize pathStr - restore backslash escapes from percent encoding
            path = parsed.path
            if had_escapes:
                path = Uri._restore_backslash_escapes(path)

            # Apply scheme normalization
            path, port = Uri._normalize_scheme(scheme, path, port)

            # If host but no path, use "/"
            if host and (not path or path == ""):
                path = "/"

            # Normalize path following JS logic:
            # - "." removed only if path.size > 1 OR host != null
            # - ".." removed only if preceded by non-".." segment
            path = Uri._normalize_path_with_host(path, host)

            uri = Uri(
                scheme=scheme,
                userInfo=userInfo,
                host=host,
                port=port,
                pathStr=path,
                queryStr=parsed.query or None,
                frag=parsed.fragment or None
            )
            Uri._cache[s] = uri
            return uri
        except Exception as e:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid URI: {s}")
            return None

    @staticmethod
    def decode(s, checked=True):
        """Decode a URI, unescaping percent-encoded characters"""
        return Uri.from_str(unquote(s), checked)

    @staticmethod
    def encode(s, section=None):
        """Encode string for use in URI path/query"""
        if section is None:
            section = 1  # sectionPath
        # Different safe characters for different sections
        if section == 1:  # path
            return quote(s, safe="")
        elif section == 2:  # query
            return quote(s, safe="")
        elif section == 3:  # frag
            return quote(s, safe="")
        return quote(s, safe="")

    @staticmethod
    def escape_token(s, section=None):
        """Escape a URI token using backslash escaping for special chars"""
        if section is None:
            section = 1  # sectionPath
        result = []
        # Special chars that need escaping per section
        path_special = '/#?'
        query_special = '#&='
        frag_special = ''
        if section == 1:  # path
            special = path_special
        elif section == 2:  # query
            special = query_special
        else:
            special = frag_special
        for c in s:
            if c == '\\' or c in special:
                result.append('\\')
            result.append(c)
        return ''.join(result)

    @staticmethod
    def encode_token(s, section=None):
        """Percent-encode a URI token"""
        if section is None:
            section = 1  # sectionPath
        # Different safe characters for different sections
        if section == 1:  # path
            return quote(s, safe="")
        elif section == 2:  # query - don't encode /
            return quote(s, safe="/")
        else:  # frag
            return quote(s, safe="")

    @staticmethod
    def unescape_token(s):
        """Unescape a URI token (remove backslash escapes)"""
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                result.append(s[i + 1])
                i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result)

    @staticmethod
    def decode_token(s, section=None):
        """Decode a percent-encoded URI token and apply backslash escaping"""
        # First percent-decode, then apply backslash escaping
        decoded = unquote(s)
        return Uri.escape_token(decoded, section)

    @staticmethod
    def encode_query(map):
        """Encode map as query string using Fantom-style encoding.

        - Spaces become +
        - Special query chars (&, ;, =, #) are percent-encoded
        - Backslash is percent-encoded
        - Other unreserved chars pass through
        """
        parts = []
        # Handle both Map objects and dicts
        if hasattr(map, 'keys'):
            keys = map.keys()
            for i in range(keys.size if hasattr(keys, 'size') else len(keys)):
                key = keys.get(i) if hasattr(keys, 'get') else keys[i]
                val = map.get(key) if hasattr(map, 'get') else map[key]
                parts.append(Uri._percent_encode_query(key) + "=" + Uri._percent_encode_query(val))
        else:
            for k, v in map.items():
                parts.append(Uri._percent_encode_query(k) + "=" + Uri._percent_encode_query(v))
        return "&".join(parts)

    @staticmethod
    def _percent_encode_query(s):
        """Percent-encode a query key or value.

        For encode_query - uses percent-encoding (not backslash escaping).
        """
        if s is None:
            return ""
        result = []
        for c in s:
            code = ord(c)
            # Unreserved chars pass through (except space -> +)
            if c == ' ':
                result.append('+')
            elif code < 128 and (c.isalnum() or c in '-._~'):
                result.append(c)
            # Allow some sub-delimiters that are safe in query values
            elif c in "!$'()*+,/:@":
                result.append(c)
            else:
                # Percent-encode everything else
                result.append(Uri._percent_encode_char(c))
        return ''.join(result)

    @staticmethod
    def _percent_encode_char(c):
        """Percent-encode a single character."""
        encoded = c.encode('utf-8')
        return ''.join(f'%{b:02X}' for b in encoded)

    @staticmethod
    def decode_query(s):
        """Decode query string to map.

        Handles Fantom's query string format:
        - + decodes to space
        - & and ; are delimiters
        - params with no value get value "true"
        - backslash escapes like \& \= \; \# are respected
        """
        from fan.sys.Map import Map
        if not s:
            return Map.make_with_type("sys::Str", "sys::Str")

        result = {}

        # Parse query string manually to handle Fantom's format
        start = 0
        eq_pos = -1
        i = 0
        prev = ''
        escaped = False

        while i <= len(s):
            ch = s[i] if i < len(s) else '\0'  # null terminator for final segment

            # Check for backslash escape
            if prev == '\\' and ch != '\\':
                prev = ch
                i += 1
                escaped = True
                continue

            # Check for delimiter (& or ;) or end of string
            if (ch == '&' or ch == ';' or ch == '\0') and prev != '\\':
                if start < i:
                    Uri._add_query_param(result, s, start, eq_pos, i, escaped)
                    escaped = False
                start = i + 1
                eq_pos = -1
            elif ch == '=' and eq_pos < 0 and prev != '\\':
                eq_pos = i

            prev = ch if ch != '\\' or prev == '\\' else '\\'
            if prev == '\\' and ch == '\\':
                prev = ''  # Reset double backslash
            i += 1

        return Map.from_dict(result)

    @staticmethod
    def _add_query_param(result, q, start, eq_pos, end, escaped):
        """Add a query parameter to the result dict."""
        if start == eq_pos:
            # key with no value: "key" or "=value" (eq at start means empty key)
            key = Uri._to_query_str(q, start, end, escaped)
            val = "true"
        elif eq_pos < 0:
            # No = found, so this is just a key with value "true"
            key = Uri._to_query_str(q, start, end, escaped)
            val = "true"
        else:
            key = Uri._to_query_str(q, start, eq_pos, escaped)
            val = Uri._to_query_str(q, eq_pos + 1, end, escaped)

        # Handle duplicate keys by joining with comma
        if key in result:
            result[key] = result[key] + "," + val
        else:
            result[key] = val

    @staticmethod
    def _to_query_str(q, start, end, escaped):
        """Convert a query string segment, handling + as space, percent-decoding, and backslash escapes."""
        # First percent-decode the segment, then handle + and backslash escapes
        segment = q[start:end]

        # Percent-decode
        result = []
        i = 0
        while i < len(segment):
            c = segment[i]
            if c == '%' and i + 2 < len(segment):
                # Percent-encoded byte
                try:
                    hex_val = int(segment[i+1:i+3], 16)
                    result.append(chr(hex_val))
                    i += 3
                    continue
                except ValueError:
                    pass  # Not valid hex, treat as literal
            elif c == '+':
                result.append(' ')
                i += 1
                continue
            result.append(c)
            i += 1

        decoded = ''.join(result)

        if not escaped:
            return decoded

        # Handle backslash escapes
        result = []
        prev = ''
        for c in decoded:
            if c == '\\':
                if prev == '\\':
                    result.append('\\')
                    prev = ''
                else:
                    prev = c
            else:
                result.append(c)
                prev = c
        return ''.join(result)

    @staticmethod
    def def_val():
        """Default empty URI"""
        return Uri()

    @staticmethod
    def _make_from_path_str(pathStr):
        """Create a Uri directly from a path string, preserving backslash escaping.

        This bypasses urlparse which doesn't understand Fantom's backslash escaping.
        Used by File.os() to create URIs from OS paths.
        """
        # Don't use urlparse - it would misinterpret # as fragment, etc.
        # Just create the Uri directly with the path string
        uri = Uri(pathStr=pathStr)
        return uri

    @staticmethod
    def _preprocess_backslash_escapes(s):
        """Convert Fantom backslash escapes to percent encoding for urlparse.

        Fantom uses \\# \\? etc. to escape special chars. Python's urlparse
        doesn't understand this, so we convert to percent encoding first,
        then convert back when storing the path.

        Returns: (preprocessed_string, had_escapes)
        """
        # Check if string has any backslash escapes
        if '\\' not in s:
            return s, False

        result = []
        had_escapes = False
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                next_char = s[i + 1]
                # Check if this is escaping a special URI character
                if next_char in '#?':
                    # Convert \# to %23, \? to %3F
                    result.append(f'%{ord(next_char):02X}')
                    had_escapes = True
                    i += 2
                    continue
            result.append(s[i])
            i += 1
        return ''.join(result), had_escapes

    @staticmethod
    def _restore_backslash_escapes(path):
        """Convert percent-encoded special chars back to backslash escapes.

        After urlparse processes the path, we need to convert %23 back to \# etc.
        """
        # Map of percent-encoded -> backslash-escaped
        replacements = [
            ('%23', '\\#'),
            ('%3F', '\\?'),
            ('%3f', '\\?'),  # lowercase version
        ]
        for encoded, escaped in replacements:
            path = path.replace(encoded, escaped)
        return path

    def is_abs(self):
        """Return true if this is an absolute URI"""
        return self._scheme is not None

    def is_rel(self):
        """Return true if this is a relative URI"""
        return self._scheme is None

    def is_dir(self):
        """Return true if path ends with /"""
        return self._pathStr.endswith("/")

    def scheme(self):
        """Get URI scheme (e.g., 'http', 'file')"""
        return self._scheme

    def user_info(self):
        """Get user info portion"""
        return self._userInfo

    def host(self):
        """Get host portion"""
        return self._host

    def get(self):
        """Resolve this URI to the object it references.

        For fan:// URIs with empty path, returns the Pod.
        Otherwise returns a File.
        """
        if self._scheme == "fan":
            # fan://podName -> return the Pod
            path = self.path()
            if path is None or len(path) == 0:
                from .Pod import Pod
                return Pod.find(self._host)
        # Default: return as File (use checkSlash=False to auto-normalize)
        from .File import File
        return File.make(self, checkSlash=False)

    def port(self):
        """Get port number or null"""
        return self._port

    def auth(self):
        """Get authority portion (userInfo@host:port)"""
        if self._host is None:
            return None
        s = ""
        if self._userInfo:
            s += self._userInfo + "@"
        s += self._host
        if self._port is not None:
            s += ":" + str(self._port)
        return s

    def path_str(self):
        """Get path as string"""
        return self._pathStr

    def path(self):
        """Get path segments as list (immutable)"""
        from fan.sys.List import List
        if self._pathSegs is None:
            segs = [s for s in self._pathStr.split("/") if s]
            self._pathSegs = segs
        lst = List.from_list(self._pathSegs)
        return lst.to_immutable() if hasattr(lst, 'to_immutable') else lst

    def name(self):
        """Get the last segment of the path"""
        path = self.path()
        if path.size == 0:
            return ""
        return path.get(path.size - 1)

    def basename(self):
        """Get name without extension"""
        n = self.name()
        dot = n.rfind(".")
        # Handle special cases like JS does
        if dot < 2:
            if dot < 0:
                return n
            if n == ".":
                return n
            if n == "..":
                return n
        return n[:dot] if dot > 0 else n

    def ext(self):
        """Get file extension or null"""
        n = self.name()
        dot = n.rfind(".")
        # Handle special cases like JS does
        if dot < 2:
            if dot < 0:
                return None
            if n == ".":
                return None
            if n == "..":
                return None
        return n[dot+1:] if dot > 0 else None

    def query_str(self):
        """Get query string"""
        return self._queryStr

    def query(self):
        """Get query parameters as map (Str:Str type, immutable)"""
        from fan.sys.Map import Map
        if self._queryStr is None:
            # Return empty Str:Str map (immutable)
            m = Map.make_with_type("sys::Str", "sys::Str")
            return m.to_immutable() if hasattr(m, 'to_immutable') else m
        m = Uri.decode_query(self._queryStr)
        return m.to_immutable() if hasattr(m, 'to_immutable') else m

    def frag(self):
        """Get fragment portion"""
        return self._frag

    def parent(self):
        """Get parent URI"""
        path = self.path()
        pathSize = path.size

        # If no path, no parent
        if pathSize == 0:
            return None

        # If just a simple filename (not a dir and path is relative), then no parent
        if pathSize == 1 and not self.is_path_abs() and not self.is_dir():
            return None

        # Use getRange to get parent
        from fan.sys.Range import Range
        return self.get_range(Range.make(0, -2, False))

    def plus(self, other):
        """Resolve a relative URI against this URI per RFC 3986 section 5.2.2"""
        if isinstance(other, str):
            other = Uri.from_str(other)

        r = other
        base = self

        # if r is more or equal as absolute as base, return r
        if r._scheme is not None:
            return r
        if r._host is not None and base._scheme is None:
            return r
        if r.is_path_abs() and base._host is None:
            return r

        # RFC 3986 (5.2.2) Transform References
        if r._host is not None:
            # r has authority - use r's auth and path
            t_scheme = base._scheme
            t_userInfo = r._userInfo
            t_host = r._host
            t_port = r._port
            t_pathStr = Uri._normalize_path(r._pathStr)
            t_path_segs = None  # will be recomputed
            t_queryStr = r._queryStr
            t_frag = r._frag
        else:
            if r._pathStr is None or r._pathStr == "":
                # Empty path - use base path
                t_pathStr = base._pathStr
                if r._queryStr is not None:
                    t_queryStr = r._queryStr
                else:
                    t_queryStr = base._queryStr
            else:
                if r._pathStr.startswith("/"):
                    # r has absolute path
                    t_pathStr = Uri._normalize_path(r._pathStr)
                else:
                    # Merge paths
                    t_pathStr = Uri._merge_paths(base, r)
                t_queryStr = r._queryStr
            t_userInfo = base._userInfo
            t_host = base._host
            t_port = base._port
            t_scheme = base._scheme
            t_frag = r._frag

        # Normalize for well-known schemes
        t_pathStr, t_port = Uri._normalize_scheme(t_scheme, t_pathStr, t_port)

        return Uri(
            scheme=t_scheme,
            userInfo=t_userInfo,
            host=t_host,
            port=t_port,
            pathStr=t_pathStr,
            queryStr=t_queryStr,
            frag=t_frag
        )

    @staticmethod
    def _merge_paths(base, r):
        """Merge base and relative paths per RFC 3986"""
        baseIsAbs = base.is_path_abs()
        baseIsDir = base.is_dir()
        rIsDir = r.is_dir()
        rPath = r.path()

        # Compute the target path
        if base._pathStr is None or len(base._pathStr) == 0 or base.path().size == 0:
            tPath = list(rPath)
        else:
            tPath = list(base.path())
            if not baseIsDir:
                # Remove last segment from base (the "file" part)
                if tPath:
                    tPath.pop()

            # Process each segment from r
            dotLast = False
            for i in range(rPath.size):
                rSeg = rPath.get(i)
                if rSeg == ".":
                    dotLast = True
                    continue
                if rSeg == "..":
                    if tPath:
                        tPath.pop()
                    dotLast = True
                    continue
                tPath.append(rSeg)
                dotLast = False

        # Build path string
        result = ""
        if baseIsAbs:
            result = "/"
        for i, seg in enumerate(tPath):
            if i > 0:
                result += "/"
            result += seg

        # Determine if result should be directory
        finalIsDir = rIsDir
        if not finalIsDir and r._pathStr:
            # Check if r ended with . or ..
            if r._pathStr.endswith("/.") or r._pathStr.endswith("/..") or r._pathStr == "." or r._pathStr == "..":
                finalIsDir = True

        if finalIsDir and result and not result.endswith("/"):
            result += "/"

        return Uri._normalize_path(result)

    @staticmethod
    def _normalize_path_with_host(pathStr, host):
        """Normalize path following JS logic:
        - "." removed only if path.size > 1 OR host != null
        - ".." removed only if preceded by non-".." segment
        """
        if not pathStr:
            return pathStr

        isAbs = pathStr.startswith("/")
        isDir = pathStr.endswith("/")

        # Split into segments
        segments = [s for s in pathStr.split("/") if s]
        result = list(segments)  # Work on a copy
        modified = False
        dotLast = False

        i = 0
        while i < len(result):
            seg = result[i]
            # Remove "." only if path.size > 1 OR host != null
            if seg == "." and (len(result) > 1 or host is not None):
                result.pop(i)
                modified = True
                dotLast = True
                # Don't increment i since we removed element
            # Remove ".." only if preceded by non-".." segment
            elif seg == ".." and i > 0 and result[i-1] != "..":
                result.pop(i)      # Remove ..
                result.pop(i-1)    # Remove preceding segment
                modified = True
                i -= 1  # Adjust index
                dotLast = True
            else:
                dotLast = False
                i += 1

        if not modified:
            return pathStr

        # Determine isDir for result
        if dotLast:
            isDir = True
        if len(result) == 0 or (result and result[-1] == ".."):
            isDir = False

        # Build result string
        if not result:
            if isAbs:
                return "/"
            return ""

        path = "/".join(result)
        if isAbs:
            path = "/" + path
        if isDir:
            path += "/"

        return path

    @staticmethod
    def _normalize_path(pathStr):
        """Remove . and .. segments from path (without host context - used for merge)"""
        if not pathStr:
            return pathStr

        isAbs = pathStr.startswith("/")
        isDir = pathStr.endswith("/")

        # Split into segments
        segments = [s for s in pathStr.split("/") if s]
        result = []

        for seg in segments:
            if seg == ".":
                # Skip . segments but remember we had one
                isDir = True
                continue
            elif seg == "..":
                if result and result[-1] != "..":
                    result.pop()
                    isDir = True
                elif not isAbs:
                    result.append("..")
                    isDir = False
                # If abs path and nothing to pop, just skip
                continue
            else:
                result.append(seg)
                isDir = False

        # Check if original ended with / or . or ..
        if pathStr.endswith("/") or pathStr.endswith("/.") or pathStr.endswith("/.."):
            isDir = True

        # Build result
        if not result:
            if isAbs:
                return "/"
            return ""

        path = "/".join(result)
        if isAbs:
            path = "/" + path
        if isDir:
            path += "/"

        return path

    @staticmethod
    def _normalize_scheme(scheme, pathStr, port):
        """Normalize for well-known schemes"""
        if scheme is None:
            return pathStr, port

        # Default ports
        if scheme == "http" and port == 80:
            port = None
        elif scheme == "https" and port == 443:
            port = None
        elif scheme == "ftp" and port == 21:
            port = None

        # Ensure path for schemes with authority
        if scheme in ("http", "https", "ftp"):
            if pathStr is None or pathStr == "":
                pathStr = "/"

        return pathStr, port

    def plus_slash(self):
        """Ensure URI ends with /"""
        if self._pathStr.endswith("/"):
            return self
        return Uri(
            scheme=self._scheme,
            userInfo=self._userInfo,
            host=self._host,
            port=self._port,
            pathStr=self._pathStr + "/",
            queryStr=self._queryStr,
            frag=self._frag
        )

    def rel_to(self, base):
        """Get relative URI from base.
        If authorities differ, return self unchanged.
        Otherwise compute relative path with .. backups as needed.
        """
        if isinstance(base, str):
            base = Uri.from_str(base)

        # If schemes differ, return self
        if self._scheme != base._scheme:
            return self

        # If userInfo differs, return self
        if self._userInfo != base._userInfo:
            return self

        # If hosts differ, return self
        if self._host != base._host:
            return self

        # If ports differ, return self
        if self._port != base._port:
            return self

        # Same authority - compute relative path
        selfPath = self.path()
        basePath = base.path()

        # Find divergence point
        d = 0
        minLen = min(selfPath.size, basePath.size)
        while d < minLen:
            if selfPath.get(d) != basePath.get(d):
                break
            d += 1

        # If divergence is at root (no commonality)
        if d == 0:
            # `/a/b/c`.rel_to(`/`) should be `a/b/c`
            if basePath.size == 0 and self._pathStr.startswith("/"):
                return Uri(pathStr=self._pathStr[1:], queryStr=self._queryStr, frag=self._frag)
            else:
                return Uri(pathStr=self._pathStr, queryStr=self._queryStr, frag=self._frag)

        # If paths are exactly the same
        if d == selfPath.size and d == basePath.size:
            return Uri(pathStr="", queryStr=self._queryStr, frag=self._frag)

        # Create sub-path at divergence point
        tPath = []

        # Insert .. backups if needed
        backup = basePath.size - d
        if not base.is_dir():
            backup -= 1
        for _ in range(backup):
            tPath.append("..")

        # Add remaining segments from self
        for i in range(d, selfPath.size):
            tPath.append(selfPath.get(i))

        # Build path string
        pathStr = "/".join(tPath)
        if self.is_dir() and pathStr and not pathStr.endswith("/"):
            pathStr += "/"

        return Uri(pathStr=pathStr, queryStr=self._queryStr, frag=self._frag)

    def rel_to_auth(self):
        """Get URI relative to authority (remove scheme and authority)"""
        # Return self if already no authority
        if (self._scheme is None and self._userInfo is None and
            self._host is None and self._port is None):
            return self
        return Uri(
            pathStr=self._pathStr,
            queryStr=self._queryStr,
            frag=self._frag
        )

    def is_path_abs(self):
        """Return true if path starts with /"""
        return self._pathStr.startswith("/")

    def is_path_rel(self):
        """Return true if path doesn't start with /"""
        return not self._pathStr.startswith("/")

    def is_path_only(self):
        """Return true if this URI only has a path component"""
        return (self._scheme is None and
                self._host is None and
                self._queryStr is None and
                self._frag is None)

    @staticmethod
    def is_name(name):
        """Return true if the name is a valid URI path segment name.
        Valid names contain only unreserved characters: A-Z, a-z, 0-9, -._~
        and cannot be empty, "." or ".."
        """
        if not name or name == "." or name == "..":
            return False
        for c in name:
            # Only allow unreserved characters: A-Z, a-z, 0-9, -._~
            if not (c.isalnum() or c in '-._~'):
                return False
            # Also reject non-ASCII even if isalnum says true
            if ord(c) > 127:
                return False
        return True

    @staticmethod
    def check_name(name):
        """Throw NameErr if name is not valid"""
        if not Uri.is_name(name):
            from fan.sys.Err import NameErr
            raise NameErr.make(f"Invalid Uri name: {name}")

    def __len__(self):
        """Return number of path segments for slicing support"""
        return len(self.path())

    def path_only(self):
        """Get URI with only the path component"""
        # Return self if already path-only
        if (self._scheme is None and self._userInfo is None and
            self._host is None and self._port is None and
            self._queryStr is None and self._frag is None):
            return self
        return Uri(pathStr=self._pathStr)

    def plus_name(self, name, asDir=False):
        """Append a name to path, replacing last segment if not a directory"""
        segs = list(self.path())
        isDir = self.is_dir() or len(segs) == 0

        if isDir:
            # Append to existing path
            segs.append(name)
        else:
            # Replace last segment
            if segs:
                segs[-1] = name
            else:
                segs.append(name)

        # Build new path string
        pathStr = ""
        if self.is_abs() or self.is_path_abs():
            pathStr = "/"
        pathStr += "/".join(segs)
        if asDir:
            pathStr += "/"

        return Uri(
            scheme=self._scheme,
            userInfo=self._userInfo,
            host=self._host,
            port=self._port,
            pathStr=pathStr
        )

    def plus_query(self, query):
        """Add or merge query parameters.

        Uses Fantom-style query encoding with backslash escapes for special chars.
        """
        if query is None or (hasattr(query, 'is_empty') and query.is_empty()):
            return self

        # Merge with existing query if present
        from fan.sys.Map import Map
        if self._queryStr:
            merged = self.query().dup()
            merged.set_all(query)
        else:
            merged = query if isinstance(query, Map) else Map.from_dict(dict(query))

        # Build query string with Fantom-style encoding
        parts = []
        keys = merged.keys()
        for i in range(keys.size):
            key = keys.get(i)
            val = merged.get(key)
            parts.append(Uri._encode_query_part(key) + "=" + Uri._encode_query_part(val))

        new_query = "&".join(parts)

        return Uri(
            scheme=self._scheme,
            userInfo=self._userInfo,
            host=self._host,
            port=self._port,
            pathStr=self._pathStr,
            queryStr=new_query,
            frag=self._frag
        )

    @staticmethod
    def _encode_query_part(s):
        """Encode a query key or value using Fantom-style encoding.

        - &, ;, = are backslash-escaped
        - # is percent-encoded (since it starts fragment)
        - \\ is backslash-escaped
        """
        if s is None:
            return ""
        result = []
        for c in s:
            # Backslash-escape query delimiters (but not #)
            if c in '&;=\\':
                result.append('\\')
                result.append(c)
            elif c == '#':
                # # must be percent-encoded, not backslash-escaped
                result.append('%23')
            else:
                result.append(c)
        return ''.join(result)

    def to_code(self):
        """Get URI as Fantom source code literal.
        Must escape $ and ` characters with backslash for Fantom code.
        """
        s = self.to_str()
        # Escape $ and ` with backslash for Fantom literal syntax
        result = []
        for c in s:
            if c == '$' or c == '`':
                result.append('\\')
            result.append(c)
        return "`" + ''.join(result) + "`"

    def literal_encode(self, out):
        """Encode for serialization.

        URI literals are written as backtick-quoted strings: `http://example.com`
        """
        out.w_str_literal(self.to_str(), '`')

    def mime_type(self):
        """Get MIME type based on file extension or directory type"""
        from fan.sys.MimeType import MimeType
        # Directories have special mime type
        if self.is_dir():
            return MimeType.from_str("x-directory/normal")
        ext = self.ext()
        if ext is None:
            return None
        return MimeType.for_ext(ext)

    def to_file(self):
        """Convert this URI to a File.

        Returns:
            File object for this URI
        """
        from .File import File
        return File.make(self)

    def to_str(self):
        """String representation"""
        s = ""
        if self._scheme:
            s += self._scheme + ":"
        if self._host:
            s += "//"
            if self._userInfo:
                s += self._userInfo + "@"
            s += self._host
            if self._port is not None:
                s += ":" + str(self._port)
        s += self._pathStr
        if self._queryStr:
            s += "?" + self._queryStr
        if self._frag:
            s += "#" + self._frag
        return s

    def to_locale(self):
        """Locale string representation - same as toStr for URIs"""
        return self.to_str()

    def encode_(self):
        """Encode URI with percent-encoding"""
        return quote(self.to_str(), safe=":/?#[]@!$&'()*+,;=")

    def encode(self):
        """Instance encode method - encode this URI's string representation"""
        return quote(self.to_str(), safe=":/?#[]@!$&'()*+,;=")

    def equals(self, other):
        """Test equality"""
        if not isinstance(other, Uri):
            return False
        return self.to_str() == other.to_str()

    def hash_(self):
        """Hash code"""
        return hash(self.to_str())

    def compare(self, other):
        """Compare URIs by string representation"""
        if other is None:
            return 1
        a = self.to_str()
        b = other.to_str() if isinstance(other, Uri) else str(other)
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    # Python operator overloads
    def __add__(self, other):
        """Python + operator: Uri + Uri or Uri + str -> Uri"""
        return self.plus(other)

    def __eq__(self, other):
        """Python == operator"""
        if not isinstance(other, Uri):
            return False
        return self.equals(other)

    def __hash__(self):
        """Python hash()"""
        return self.hash_()

    def __lt__(self, other):
        """Python < operator"""
        return self.compare(other) < 0

    def __le__(self, other):
        """Python <= operator"""
        return self.compare(other) <= 0

    def __gt__(self, other):
        """Python > operator"""
        return self.compare(other) > 0

    def __ge__(self, other):
        """Python >= operator"""
        return self.compare(other) >= 0

    def __str__(self):
        """Python str()"""
        return self.to_str()

    def __repr__(self):
        """Python repr()"""
        return f"Uri({self.to_str()!r})"

    def __getitem__(self, key):
        """Python [] operator for slicing (getRange)"""
        if isinstance(key, slice):
            # Convert Python slice to Fantom Range
            from fan.sys.Range import Range
            start = key.start if key.start is not None else 0
            stop = key.stop if key.stop is not None else len(self.path())
            r = Range.make(start, stop - 1, False)
            return self.get_range(r)
        else:
            # Single index - return path segment
            return self.path().get(key)

    def get_range_to_path_abs(self, r):
        """Get a subset of path segments, forcing absolute path"""
        return self.get_range(r, forcePathAbs=True)

    def get_range(self, r, forcePathAbs=False):
        """Get a subset of path segments as new Uri"""
        segs = self.path()
        try:
            segs_size = len(segs)
        except:
            segs_size = segs.size

        # Handle negative indices using Fantom Range semantics (like JS __start/__end)
        start_val = r.start()
        end_val = r.end()

        # Handle negative indices
        if start_val < 0:
            start_val = segs_size + start_val
        if end_val < 0:
            end_val = segs_size + end_val

        # Handle exclusive ranges (like JS __end)
        if r.exclusive():
            end_val -= 1

        # Clamp to valid range
        start_val = max(0, start_val)
        end_val = min(segs_size - 1, end_val)

        n = end_val - start_val + 1
        if n < 0:
            from fan.sys.Err import IndexErr
            raise IndexErr.make(str(r))

        head = (start_val == 0)
        tail = (end_val == segs_size - 1)

        # If same as original and not forcing path abs, return self
        if head and tail and (not forcePathAbs or self.is_path_abs()):
            return self

        # Build new path from segments
        new_segs = []
        for i in range(start_val, end_val + 1):
            if i < segs_size:
                new_segs.append(segs.get(i))

        # Build path string
        new_path = ""
        if (head and self.is_path_abs()) or forcePathAbs:
            new_path = "/"
        for i, seg in enumerate(new_segs):
            if i > 0:
                new_path += "/"
            new_path += seg

        # Add trailing slash if needed
        if len(new_segs) > 0 and (not tail or self.is_dir()):
            new_path += "/"

        # Head includes scheme/auth, tail includes query/frag
        return Uri(
            scheme=self._scheme if head else None,
            userInfo=self._userInfo if head else None,
            host=self._host if head else None,
            port=self._port if head else None,
            pathStr=new_path,
            queryStr=self._queryStr if tail else None,
            frag=self._frag if tail else None
        )


class UriScheme(Obj):
    """
    UriScheme handles scheme-specific URI operations.
    """

    _schemes = {}

    def __init__(self, name):
        self._name = name

    @staticmethod
    def find(name, checked=True):
        """Find scheme handler by name"""
        if name in UriScheme._schemes:
            return UriScheme._schemes[name]
        scheme = UriScheme(name)
        UriScheme._schemes[name] = scheme
        return scheme

    def name(self):
        """Get scheme name"""
        return self._name

    def to_str(self):
        return self._name


# Register common schemes
UriScheme._schemes["http"] = UriScheme("http")
UriScheme._schemes["https"] = UriScheme("https")
UriScheme._schemes["file"] = UriScheme("file")
UriScheme._schemes["fan"] = UriScheme("fan")
