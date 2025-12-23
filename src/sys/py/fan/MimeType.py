#
# MimeType - MIME content type for Fantom
#
from fan.sys.Obj import Obj


class MimeType(Obj):
    """
    MimeType represents a MIME content type.
    """

    # Cache of parsed MIME types (normalized key -> instance)
    _cache = {}

    def __new__(cls, mediaType, subType=None, params=None, _original_str=None):
        """
        Create a MimeType. Uses cache for identity semantics.
        Can be called as:
        - MimeType("text/plain")
        - MimeType("text/plain; charset=utf-8")
        - MimeType("text", "plain")
        - MimeType("text", "plain", params_map)
        """
        if subType is None:
            # Single string argument - use fromStr for caching
            return cls.fromStr(mediaType)
        else:
            # Explicit mediaType/subType - create new instance
            instance = object.__new__(cls)
            return instance

    def __init__(self, mediaType, subType=None, params=None, _original_str=None):
        """Initialize MimeType instance"""
        # Skip init if already initialized (from cache)
        if hasattr(self, '_mediaType'):
            return

        if subType is None:
            # Single string argument - should have been handled by __new__
            # This path shouldn't be hit, but handle it anyway
            parsed = MimeType._parse(mediaType)
            if parsed is None:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid MIME type: {mediaType}")
            self._mediaType = parsed._mediaType
            self._subType = parsed._subType
            self._params = parsed._params
            self._originalStr = parsed._originalStr
        else:
            # Explicit mediaType/subType
            self._mediaType = mediaType.lower()
            self._subType = subType.lower()
            self._originalStr = _original_str

            # Store params as case-insensitive Map
            from fan.sys.Map import Map
            self._params = Map()
            self._params._caseInsensitive = True
            self._params._ro = True
            if params:
                if isinstance(params, dict):
                    for k, v in params.items():
                        self._params[k] = v
                elif hasattr(params, 'items'):
                    for k, v in params.items():
                        self._params[k] = v

    @staticmethod
    def _parse(s):
        """Internal parsing method - returns MimeType or None"""
        if not s or "/" not in s:
            return None

        try:
            # Split on first semicolon to separate type from params
            semi_idx = s.find(";")
            if semi_idx >= 0:
                main = s[:semi_idx].strip()
                param_str = s[semi_idx + 1:]
            else:
                main = s.strip()
                param_str = ""

            if "/" not in main:
                return None

            slash_idx = main.find("/")
            mediaType = main[:slash_idx].strip().lower()
            subType = main[slash_idx + 1:].strip().lower()

            if not mediaType or not subType:
                return None

            # Parse parameters - always creates a typed Str:Str map
            params = MimeType.parseParams(param_str) if param_str else MimeType._makeEmptyParams()

            mt = object.__new__(MimeType)
            mt._mediaType = mediaType
            mt._subType = subType
            mt._originalStr = s

            # Use the params directly (already properly typed)
            mt._params = params
            mt._params._ro = True

            return mt
        except Exception:
            return None

    @staticmethod
    def _makeEmptyParams():
        """Create an empty, properly typed Str:Str params map"""
        from fan.sys.Map import Map
        from fan.sys.Type import Type, MapType
        result = Map()
        result._caseInsensitive = True
        result._ro = True
        strType = Type.find("sys::Str")
        result._keyType = strType
        result._valueType = strType
        result._mapType = MapType(strType, strType)
        return result

    @staticmethod
    def fromStr(s, checked=True):
        """Parse a MimeType from string like 'text/plain; charset=utf-8'"""
        if s is None:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr("MimeType.fromStr: null string")
            return None

        # Cache under exact original string to preserve toStr() behavior
        if s in MimeType._cache:
            return MimeType._cache[s]

        mt = MimeType._parse(s)
        if mt is None:
            if checked:
                from fan.sys.Err import ParseErr
                raise ParseErr(f"Invalid MIME type: {s}")
            return None

        # Cache under exact original string
        MimeType._cache[s] = mt
        return mt

    @staticmethod
    def _normalizeKey(s):
        """Normalize a MIME type string for cache key"""
        # Parse and reconstruct for normalization
        semi_idx = s.find(";")
        if semi_idx >= 0:
            main = s[:semi_idx].strip().lower()
            param_str = s[semi_idx + 1:]
            # Parse params and sort them
            params = MimeType.parseParams(param_str)
            if params and len(params) > 0:
                # Sort params by lowercase key
                sorted_params = sorted(params.items(), key=lambda x: x[0].lower())
                param_parts = [f"{k.lower()}={v}" for k, v in sorted_params]
                return f"{main}; {'; '.join(param_parts)}"
            return main
        else:
            return s.strip().lower()

    @staticmethod
    def parseParams(s):
        """
        Parse parameter string into case-insensitive Map.
        Handles: "a=b; c=d", "name=\"quoted\"", escaped quotes, empty values
        """
        from fan.sys.Map import Map
        from fan.sys.Type import Type, MapType
        result = Map()
        result._caseInsensitive = True
        # Set Str:Str type for proper equality checks
        strType = Type.find("sys::Str")
        result._keyType = strType
        result._valueType = strType
        result._mapType = MapType(strType, strType)

        if not s or not s.strip():
            return result

        s = s.strip()
        i = 0
        n = len(s)

        while i < n:
            # Skip whitespace and semicolons
            while i < n and (s[i] == ' ' or s[i] == ';' or s[i] == '\t'):
                i += 1
            if i >= n:
                break

            # Read parameter name
            name_start = i
            while i < n and s[i] != '=' and s[i] != ';' and s[i] != ' ':
                i += 1
            name = s[name_start:i]

            if not name:
                i += 1
                continue

            # Skip whitespace before =
            while i < n and s[i] == ' ':
                i += 1

            # Check for =
            if i >= n or s[i] == ';':
                # No value - param with empty value
                result[name] = ""
                continue

            if s[i] != '=':
                # No = sign found - param with empty value
                result[name] = ""
                continue

            i += 1  # Skip =

            # Skip whitespace after =
            while i < n and s[i] == ' ':
                i += 1

            # Read value
            if i >= n or s[i] == ';':
                # Empty value
                result[name] = ""
                continue

            if s[i] == '"':
                # Quoted value
                i += 1  # Skip opening quote
                val_parts = []
                while i < n:
                    if s[i] == '\\' and i + 1 < n:
                        # Escaped character
                        val_parts.append(s[i + 1])
                        i += 2
                    elif s[i] == '"':
                        i += 1  # Skip closing quote
                        break
                    else:
                        val_parts.append(s[i])
                        i += 1
                result[name] = ''.join(val_parts)
            else:
                # Unquoted value - read until ; or end
                # Include everything up to semicolon, including spaces and =
                val_start = i
                while i < n and s[i] != ';':
                    i += 1
                result[name] = s[val_start:i].strip()

        return result

    @staticmethod
    def forExt(ext):
        """Get MIME type for file extension"""
        if ext is None:
            return None
        ext = ext.lower()

        # Extension to MIME type mapping
        ext_map = {
            # Text types (with charset)
            "txt": "text/plain; charset=utf-8",
            "html": "text/html; charset=utf-8",
            "htm": "text/html; charset=utf-8",
            "css": "text/css; charset=utf-8",
            "xml": "text/xml; charset=utf-8",
            "fan": "text/plain; charset=utf-8",
            # Application types
            "js": "application/javascript",
            "json": "application/json",
            "pdf": "application/pdf",
            "zip": "application/zip",
            # Image types
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "ico": "image/x-icon",
            # Audio/Video
            "mp3": "audio/mpeg",
            "mp4": "video/mp4",
            "wav": "audio/wav",
            # Directory
            "": "x-directory/normal",
        }

        mime_str = ext_map.get(ext)
        if mime_str:
            return MimeType.fromStr(mime_str)
        return None

    def mediaType(self):
        """Get media type (e.g., 'text')"""
        return self._mediaType

    def subType(self):
        """Get sub type (e.g., 'plain')"""
        return self._subType

    def params(self):
        """Get parameters as case-insensitive read-only Map"""
        return self._params

    def charset(self):
        """Get charset parameter as Charset object, or UTF-8 for text types"""
        cs = self._params.get("charset") if self._params else None
        if cs:
            # Import Charset and look up by name
            try:
                from fan.sys.Charset import Charset
                return Charset.forName(cs)
            except:
                pass
        # Default UTF-8 for text types
        if self._mediaType == "text":
            try:
                from fan.sys.Charset import Charset
                return Charset.utf8()
            except:
                pass
        return None

    def noParams(self):
        """Return MimeType without parameters"""
        if not self._params or len(self._params) == 0:
            return self
        # Return cached version without params
        key = f"{self._mediaType}/{self._subType}"
        return MimeType.fromStr(key)

    def isText(self):
        """Return true if this is a text type"""
        if self._mediaType == "text":
            return True
        # application/json is also considered text
        if self._mediaType == "application" and self._subType == "json":
            return True
        return False

    def toStr(self):
        """String representation"""
        if self._originalStr:
            return self._originalStr
        s = f"{self._mediaType}/{self._subType}"
        if self._params:
            for k, v in self._params.items():
                s += f"; {k}={v}"
        return s

    def __str__(self):
        return self.toStr()

    def __repr__(self):
        return f"MimeType({self.toStr()!r})"

    def equals(self, other):
        """Test equality - case insensitive for type, case sensitive for param values"""
        if other is None:
            return False
        if self is other:
            return True
        if not isinstance(other, MimeType):
            return False
        if self._mediaType != other._mediaType:
            return False
        if self._subType != other._subType:
            return False
        # Compare params
        self_params = self._params if self._params else {}
        other_params = other._params if other._params else {}
        if len(self_params) != len(other_params):
            return False
        for k, v in self_params.items():
            # Case-insensitive key lookup
            other_v = other_params.get(k)
            if other_v is None:
                other_v = other_params.get(k.lower())
            if v != other_v:
                return False
        return True

    def __eq__(self, other):
        return self.equals(other)

    def __ne__(self, other):
        return not self.equals(other)

    def hash_(self):
        """Hash code"""
        h = hash(self._mediaType) ^ hash(self._subType)
        if self._params:
            for k, v in self._params.items():
                h ^= hash(k.lower()) ^ hash(v)
        return h

    def __hash__(self):
        return self.hash_()

    def typeof(self):
        """Return Type for MimeType"""
        from fan.sys.Type import Type
        return Type.find("sys::MimeType")


# Predefined MIME types - use fromStr for caching
MimeType.textPlain = MimeType.fromStr("text/plain; charset=utf-8")
MimeType.textHtml = MimeType.fromStr("text/html; charset=utf-8")
MimeType.textXml = MimeType.fromStr("text/xml; charset=utf-8")
MimeType.imageGif = MimeType.fromStr("image/gif")
MimeType.imagePng = MimeType.fromStr("image/png")
MimeType.imageJpeg = MimeType.fromStr("image/jpeg")
