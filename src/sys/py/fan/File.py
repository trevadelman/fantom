#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

import os
import stat
import tempfile
import shutil
from pathlib import Path
from fan.sys.Obj import Obj


class File(Obj):
    """File - Fantom file system abstraction.

    This implementation wraps Python's pathlib.Path to provide
    Fantom-compatible file system operations.
    """

    @staticmethod
    def sep():
        """File separator for current OS."""
        return os.sep

    @staticmethod
    def path_sep():
        """Path separator for current OS."""
        return os.pathsep

    def __init__(self, uri):
        """Create File from Uri or string."""
        from .Uri import Uri

        # Store the URI
        if isinstance(uri, str):
            self._uri = Uri.from_str(uri)
        elif isinstance(uri, Uri):
            self._uri = uri
        else:
            self._uri = uri

        # Resolve to actual path
        self._path = self._uri_to_path(self._uri)

    @staticmethod
    def make(uri, checkSlash=True):
        """Create a File from a Uri.

        Args:
            uri: The Uri representing the file path
            checkSlash: If true, verify directory URIs end with slash

        Returns:
            New File instance
        """
        from .Uri import Uri
        from .Err import IOErr, ArgErr

        # Handle Uri or string
        if isinstance(uri, str):
            uri = Uri.from_str(uri)

        # On non-Windows systems, reject Windows-style drive letter paths
        # The scheme "c" looks like Windows drive c:, reject single-letter schemes
        if os.name != 'nt':
            scheme = uri.scheme() if hasattr(uri, 'scheme') else None
            if scheme is not None and len(scheme) == 1 and scheme.isalpha():
                raise ArgErr.make(f"Invalid Uri path: {uri}")

        # Create file
        f = File(uri)

        # Only validate slash consistency if file exists
        # Non-existing paths are allowed to have any URI form
        if f._path.exists():
            is_dir = f._path.is_dir()
            uri_is_dir = f._uri.is_dir()
            if is_dir and not checkSlash and not uri_is_dir:
                # Auto-correct URI to have trailing slash (per JS behavior)
                f._uri = uri.plus_slash()
            elif is_dir and checkSlash and not uri_is_dir:
                raise IOErr.make(f"Directory URI must end with slash: {uri}")
            elif not is_dir and uri_is_dir:
                raise IOErr.make(f"File URI must not end with slash: {uri}")

        return f

    @staticmethod
    def os(osPath):
        """Create a File from an OS-specific path string.

        Args:
            osPath: The OS-specific path (e.g., "C:\\foo\\bar" on Windows)

        Returns:
            New File instance with file:// scheme for absolute paths
        """
        from .Uri import Uri
        path = Path(osPath)
        # Convert to URI format - preserve relative vs absolute
        uri_str = path.as_posix()

        # Backslash-escape special URI characters in path
        # Fantom URIs use backslash escaping (e.g., `file \#2`) not percent encoding
        uri_str = File._escape_path_for_uri(uri_str)

        # For absolute paths, create file:// URI with scheme
        if path.is_absolute():
            # Ensure leading / for path portion
            if not uri_str.startswith('/'):
                uri_str = '/' + uri_str
            # Add trailing / for directories
            if path.exists() and path.is_dir() and not uri_str.endswith('/'):
                uri_str += '/'
            # Return with file:// scheme
            return File(Uri.from_str(f"file://{uri_str}"))

        # For relative paths, no scheme
        if path.exists() and path.is_dir() and not uri_str.endswith('/'):
            uri_str += '/'

        # Create Uri directly to avoid urlparse misinterpreting special chars
        return File(Uri._make_from_path_str(uri_str))

    @staticmethod
    def _escape_path_for_uri(path_str):
        """Escape special URI characters in path using backslash.

        Fantom URIs use backslash escaping for # ? etc.
        """
        result = []
        special_chars = '#?'
        for c in path_str:
            if c in special_chars:
                result.append('\\')
            result.append(c)
        return ''.join(result)

    @staticmethod
    def os_roots():
        """Return list of OS root directories."""
        from .List import List as FanList
        if os.name == 'nt':
            # Windows: return drive letters
            import string
            roots = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    roots.append(File.os(drive))
            return FanList.from_literal(roots, "sys::File")
        else:
            # Unix: just root
            return FanList.from_literal([File.os("/")], "sys::File")

    @staticmethod
    def create_temp(prefix="fan", suffix=".tmp", dir=None):
        """Create a temporary file.

        Args:
            prefix: Prefix for temp file name
            suffix: Suffix for temp file name
            dir: Directory to create temp file in (default: system temp)

        Returns:
            New File instance for the temp file
        """
        from .Err import IOErr

        dir_path = None
        if dir is not None:
            if isinstance(dir, File):
                if not dir.is_dir():
                    raise IOErr.make(f"Not a directory: {dir}")
                dir_path = str(dir._path)
            else:
                dir_path = str(dir)

        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir_path)
        os.close(fd)
        return File.os(path)

    def _uri_to_path(self, uri):
        """Convert Uri to pathlib.Path."""
        from .Uri import Uri
        if uri is None:
            return Path('.')

        # Get path string from URI
        path_str = uri.path_str() if hasattr(uri, 'path_str') else str(uri)

        # Handle file:// scheme
        if hasattr(uri, 'scheme') and uri.scheme() == 'file':
            path_str = uri.path_str()

        # Unescape backslash-escaped special characters for OS path
        path_str = File._unescape_path_from_uri(path_str)

        # Remove leading slash for relative paths on Unix
        # Keep it for absolute paths
        if path_str.startswith('/') and len(path_str) > 1:
            # On Windows, /C:/path -> C:/path
            if len(path_str) > 2 and path_str[2] == ':':
                path_str = path_str[1:]

        return Path(path_str.rstrip('/') if path_str != '/' else '/')

    @staticmethod
    def _unescape_path_from_uri(path_str):
        """Unescape backslash-escaped characters in URI path for OS path.

        Converts URI path like 'file \#2' to OS path 'file #2'.
        """
        result = []
        i = 0
        while i < len(path_str):
            if path_str[i] == '\\' and i + 1 < len(path_str):
                # Skip the backslash, take the next character
                result.append(path_str[i + 1])
                i += 2
            else:
                result.append(path_str[i])
                i += 1
        return ''.join(result)

    #########################################################################
    # Identity
    #########################################################################

    def typeof(self):
        from .Type import Type
        return Type.find("sys::File")

    def uri(self):
        """Return the URI for this file."""
        return self._uri

    def to_str(self):
        """Return string representation (same as uri.toStr)."""
        return str(self._uri)

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return f"File({self._uri})"

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, File):
            return self._uri == other._uri
        return False

    def equals(self, other):
        return self.__eq__(other)

    def __hash__(self):
        return hash(self._uri)

    def hash_(self):
        return self.__hash__()

    #########################################################################
    # Path Info
    #########################################################################

    def name(self):
        """Return file name (last path segment)."""
        return self._uri.name() if hasattr(self._uri, 'name') else self._path.name

    def basename(self):
        """Return file name without extension."""
        return self._uri.basename() if hasattr(self._uri, 'basename') else self._path.stem

    def ext(self):
        """Return file extension without dot, or null if none."""
        ext = self._uri.ext() if hasattr(self._uri, 'ext') else None
        if ext is None:
            suffix = self._path.suffix
            ext = suffix[1:] if suffix else None
        return ext

    def mime_type(self):
        """Return MIME type based on extension."""
        from .MimeType import MimeType
        ext = self.ext()
        if ext is None:
            return None
        return MimeType.for_ext(ext)

    def is_dir(self):
        """Return true if this represents a directory."""
        if hasattr(self._uri, 'is_dir'):
            return self._uri.is_dir()
        return self._path.is_dir() if self._path.exists() else str(self._path).endswith('/')

    def path(self):
        """Return path segments as a list."""
        return self._uri.path() if hasattr(self._uri, 'path') else list(self._path.parts)

    def path_str(self):
        """Return path as string."""
        return self._uri.path_str() if hasattr(self._uri, 'path_str') else str(self._path)

    def os_path(self):
        """Return OS-specific path string.

        For relative URIs, returns relative OS path.
        For absolute URIs, returns absolute OS path.
        """
        # Return path as stored - don't force absolute
        return str(self._path)

    def parent(self):
        """Return parent directory as File, or null if root."""
        parent_uri = self._uri.parent() if hasattr(self._uri, 'parent') else None
        if parent_uri is None:
            return None
        return File(parent_uri)

    def normalize(self):
        """Return normalized absolute path.

        Makes the path absolute but does NOT resolve symlinks.
        This ensures /var stays as /var (not /private/var on macOS).
        """
        from .Uri import Uri
        # Use absolute() without resolve() to keep symlinks intact
        abs_path = self._path.absolute()
        uri_str = abs_path.as_posix()
        if abs_path.is_dir() and not uri_str.endswith('/'):
            uri_str += '/'
        if not uri_str.startswith('/'):
            uri_str = '/' + uri_str
        return File(Uri.from_str(f"file://{uri_str}"))

    #########################################################################
    # Access Info
    #########################################################################

    def exists(self):
        """Return true if file exists."""
        return self._path.exists()

    def size(self):
        """Return file size in bytes, or null for directories."""
        if not self._path.exists():
            return None
        if self._path.is_dir():
            return None
        return self._path.stat().st_size

    def is_empty(self):
        """Return true if file/directory is empty."""
        if not self._path.exists():
            return True
        if self._path.is_dir():
            return len(list(self._path.iterdir())) == 0
        return self._path.stat().st_size == 0

    def modified(self, val=None):
        """Get or set last modified time as DateTime."""
        from .DateTime import DateTime
        import os
        if val is not None:
            # Set modified time
            mtime = val.to_java() / 1000.0  # Convert from Java millis to Unix seconds
            atime = self._path.stat().st_atime if self._path.exists() else mtime
            os.utime(str(self._path), (atime, mtime))
            return
        # Get modified time
        if not self._path.exists():
            return None
        mtime = self._path.stat().st_mtime
        return DateTime.from_posix(int(mtime))

    def store(self):
        """Return the storage device for this file."""
        from .FileStore import LocalFileStore
        return LocalFileStore(str(self._path))

    #########################################################################
    # Listing
    #########################################################################

    def list_(self, pattern=None):
        """List files in directory."""
        from .List import List as FanList

        if not self._path.exists() or not self._path.is_dir():
            return FanList.from_literal([], "sys::File")

        result = []
        for child in self._path.iterdir():
            f = File.os(str(child))
            if pattern is None or self._matches_pattern(child.name, pattern):
                result.append(f)
        return FanList.from_literal(result, "sys::File")

    def list_files(self, pattern=None):
        """List files (not directories) in directory."""
        from .List import List as FanList

        if not self._path.exists() or not self._path.is_dir():
            return FanList.from_literal([], "sys::File")

        result = []
        for child in self._path.iterdir():
            if child.is_file():
                if pattern is None or self._matches_pattern(child.name, pattern):
                    result.append(File.os(str(child)))
        return FanList.from_literal(result, "sys::File")

    def list_dirs(self, pattern=None):
        """List directories in directory."""
        from .List import List as FanList

        if not self._path.exists() or not self._path.is_dir():
            return FanList.from_literal([], "sys::File")

        result = []
        for child in self._path.iterdir():
            if child.is_dir():
                if pattern is None or self._matches_pattern(child.name, pattern):
                    result.append(File.os(str(child)))
        return FanList.from_literal(result, "sys::File")

    def _matches_pattern(self, name, pattern):
        """Check if name matches a Regex pattern."""
        if pattern is None:
            return True
        if hasattr(pattern, 'matches'):
            return pattern.matches(name)
        return True

    def walk(self, callback):
        """Walk directory tree, calling callback for each file."""
        if not self._path.exists():
            return
        callback(self)
        if self._path.is_dir():
            for child in self._path.rglob('*'):
                callback(File.os(str(child)))

    #########################################################################
    # Operators
    #########################################################################

    def plus(self, uri, checkSlash=True):
        """Resolve a relative URI against this file."""
        from .Uri import Uri
        from .Err import IOErr

        if isinstance(uri, str):
            uri = Uri.from_str(uri)

        # Resolve URI
        resolved = self._uri.plus(uri) if hasattr(self._uri, 'plus') else None
        if resolved is None:
            # Simple path concatenation
            new_path = self._path / str(uri)
            resolved = Uri.from_str(new_path.as_posix())

        return File.make(resolved, checkSlash)

    def __add__(self, other):
        return self.plus(other)

    #########################################################################
    # File Management
    #########################################################################

    def create(self):
        """Create this file/directory if it doesn't exist."""
        if self.is_dir():
            self._path.mkdir(parents=True, exist_ok=True)
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch()
        return self

    def create_file(self, name):
        """Create a child file in this directory."""
        from .Uri import Uri
        child_path = self._path / name
        child_path.touch()
        return File.os(str(child_path))

    def create_dir(self, name):
        """Create a child directory in this directory."""
        from .Uri import Uri
        child_path = self._path / name
        child_path.mkdir(parents=True, exist_ok=True)
        return File.os(str(child_path))

    def delete(self):
        """Delete this file/directory."""
        if not self._path.exists():
            return
        if self._path.is_dir():
            shutil.rmtree(str(self._path))
        else:
            self._path.unlink()

    def delete_on_exit(self):
        """Mark file for deletion when process exits."""
        import atexit
        atexit.register(lambda: self._path.unlink(missing_ok=True) if self._path.exists() else None)
        return self

    def move_to(self, dest):
        """Move this file to destination."""
        from .Err import ArgErr, IOErr

        if isinstance(dest, File):
            dest_path = dest._path
            dest_is_dir = dest.is_dir()  # Use URI-based check
        else:
            dest_path = Path(str(dest))
            dest_is_dir = str(dest_path).endswith('/') or (dest_path.exists() and dest_path.is_dir())

        # Validate: source directory must go to directory destination
        if self._path.is_dir() and not dest_is_dir:
            raise ArgErr.make(f"Directory destination must end with slash: {dest}")
        # Validate: source file must not go to directory path (unless dest exists as dir)
        if self._path.is_file() and dest_is_dir and not dest_path.exists():
            raise ArgErr.make(f"File destination must not end with slash: {dest}")

        shutil.move(str(self._path), str(dest_path))
        return File.os(str(dest_path))

    def move_into(self, dest):
        """Move this file into destination directory."""
        from .Uri import Uri
        from .Err import ArgErr

        # Validate: destination must be a directory
        if isinstance(dest, File):
            if not dest.is_dir():
                raise ArgErr.make(f"moveInto requires dir dest: {dest}")
            new_path = dest._path / self._path.name
        else:
            dest_path = Path(str(dest))
            if not str(dest).endswith('/') and not (dest_path.exists() and dest_path.is_dir()):
                raise ArgErr.make(f"moveInto requires dir dest: {dest}")
            new_path = dest_path / self._path.name

        # Preserve directory nature - add trailing slash if source is directory
        path_str = new_path.as_posix()
        if self._path.is_dir() and not path_str.endswith('/'):
            path_str += '/'
        if new_path.is_absolute() and not path_str.startswith('/'):
            path_str = '/' + path_str
        return self.move_to(File(Uri.from_str(path_str)))

    def copy_to(self, dest, options=None):
        """Copy this file/directory to destination.

        Options:
            exclude: Regex or Func to exclude files
            overwrite: Bool or Func to control overwrite behavior

        Returns the destination File (same object that was passed in).
        """
        from .Err import ArgErr

        # Ensure dest is a File object
        if not isinstance(dest, File):
            dest = File.os(str(dest))

        # Validate - dir must copy to dir, file must copy to file
        if self.is_dir() != dest.is_dir():
            if self.is_dir():
                raise ArgErr.make(f"copyTo must be dir `{dest}`")
            else:
                raise ArgErr.make(f"copyTo must not be dir `{dest}`")

        # Extract options
        exclude = None
        overwrite = None
        if options is not None:
            exclude = options.get("exclude")
            overwrite = options.get("overwrite")

        # Perform recursive copy
        self._do_copy_to(dest, exclude, overwrite)
        return dest

    def _do_copy_to(self, to, exclude, overwrite):
        """Internal recursive copy implementation."""
        from .Err import IOErr

        # Check exclude - Regex or Func
        if exclude is not None:
            # Check if it's a Regex (has matches method)
            if hasattr(exclude, 'matches'):
                if exclude.matches(str(self.uri())):
                    return
            # Check if it's a callable (Func) - may have .call() method for Fantom Func
            elif hasattr(exclude, 'call'):
                if exclude.call(self):
                    return
            elif callable(exclude):
                if exclude(self):
                    return

        # Check for overwrite policy
        if to.exists():
            if isinstance(overwrite, bool):
                if not overwrite:
                    return
            # Check if it's a Fantom Func with .call() method
            elif hasattr(overwrite, 'call'):
                if not overwrite.call(to, self):
                    return
            elif callable(overwrite):
                if not overwrite(to, self):
                    return
            elif overwrite is None:
                raise IOErr.make(f"No overwrite policy for `{to}`")

        # Copy directory
        if self.is_dir():
            to.create()
            kids = self.list_()
            # Use size property or len() depending on List implementation
            size = kids.size if isinstance(kids.size, int) else kids.size()
            for i in range(size):
                kid = kids.get(i)
                kid._do_copy_to(to._plus_name_of(kid), exclude, overwrite)
        # Copy file contents
        else:
            self._do_copy_file(to)

    def _do_copy_file(self, to):
        """Copy file contents to destination."""
        # Ensure parent directory exists
        to._path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(self._path), str(to._path))

    def _plus_name_of(self, x):
        """Get this + name of x (with trailing slash if x is dir)."""
        from .Uri import Uri
        name = x.name()
        if x.is_dir():
            name += "/"
        return self.plus(Uri.from_str(name))

    def copy_into(self, dest, options=None):
        """Copy this file into destination directory.

        Args:
            dest: Directory to copy into
            options: Copy options (exclude, overwrite)

        Creates a File with the correct dir/file URI based on source.
        """
        from .Err import ArgErr

        if not dest.is_dir():
            raise ArgErr.make(f"Not a dir: `{dest}`")

        return self.copy_to(dest._plus_name_of(self), options)

    def rename(self, newName):
        """Rename this file."""
        new_path = self._path.parent / newName
        self._path.rename(new_path)
        return File.os(str(new_path))

    #########################################################################
    # I/O
    #########################################################################

    def open_(self, mode="rw"):
        """Open file for random access, return Buf.

        Args:
            mode: "r" for read, "w" for write, "rw" for read/write

        Returns:
            Buf for random access to file contents
        """
        from .Buf import Buf

        if not self._path.exists():
            # Create empty file if it doesn't exist
            self._path.touch()

        # Read existing content
        data = self._path.read_bytes()
        buf = Buf(data)

        # Store reference to file for sync operations
        buf._file = self
        buf._mode = mode

        return buf

    def in_(self, bufSize=None):
        """Open file for reading, return InStream."""
        from .Buf import Buf
        data = self._path.read_bytes() if self._path.exists() else b''
        buf = Buf(data)
        return SysInStream(buf)

    def out(self, append=False, bufSize=None):
        """Open file for writing, return OutStream."""
        from .Buf import Buf
        from .Err import IOErr

        # Create parent directories if needed
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Create the file immediately if it doesn't exist (like JavaScript impl)
        # This ensures f.size() returns 0 right after f.out()
        if not self._path.exists():
            self._path.touch()

        # Create a Buf that will write to file on close
        if append and self._path.exists():
            data = self._path.read_bytes()
            buf = Buf(data)
            buf.seek(buf.size())  # Position at end for append
        else:
            buf = Buf()

        # Store reference for writing on close
        buf._file = self
        buf._mode = "w"

        return FileOutStream(buf, self._path, append)

    def read_all_str(self, normalizeNewlines=True):
        """Read entire file as string.

        Args:
            normalizeNewlines: If True, normalize \r\n and \r to \n.
                               If False, preserve raw content exactly.
        """
        if normalizeNewlines:
            # read_text() normalizes \r\n to \n, then we normalize lone \r
            content = self._path.read_text()
            content = content.replace('\r\n', '\n').replace('\r', '\n')
        else:
            # Use read_bytes() to preserve raw content including \r
            content = self._path.read_bytes().decode('utf-8')
        return content

    def read_all_lines(self):
        """Read file as list of lines."""
        from .List import List as FanList
        content = self.read_all_str()
        lines = content.split('\n')
        # Remove trailing empty string from final newline
        if lines and lines[-1] == '':
            lines = lines[:-1]
        return FanList.from_literal(lines, "sys::Str")

    def read_all_buf(self):
        """Read entire file into buffer."""
        from .Buf import Buf
        data = self._path.read_bytes()
        return Buf.from_bytes(data)

    def each_line(self, callback):
        """Iterate over each line in file."""
        for line in self.read_all_lines():
            callback(line)

    def write_props(self, props):
        """Write a properties file format.

        Args:
            props: Map or dict of key/value pairs

        Returns:
            This File for chaining
        """
        # Ensure parent directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Write props file (UTF-8 encoded)
        with open(self._path, 'w', encoding='utf-8') as f:
            # Handle both Map and dict
            if hasattr(props, 'each'):
                # Fantom Map.each callback is |V val, K key| - note: value first!
                def write_kv(val, key):
                    f.write(f"{key}={val}\n")
                props.each(write_kv)
            else:
                # Python dict or Map with items()
                items = props.items() if hasattr(props, 'items') else props
                for key, val in items:
                    f.write(f"{key}={val}\n")
        return self

    def read_props(self):
        """Read a properties file and return as Map."""
        from .Map import Map

        props = Map()
        if not self._path.exists():
            return props

        with open(self._path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith('//'):
                    continue
                # Find = separator
                eq = line.find('=')
                if eq > 0:
                    key = line[:eq].strip()
                    val = line[eq+1:].strip()
                    props.set_(key, val)
        return props

    def read_obj(self, options=None):
        """Read a serialized object from this file.

        Args:
            options: Optional decode options map

        Returns:
            Deserialized object
        """
        from fanx.ObjDecoder import ObjDecoder
        return ObjDecoder(self.in_(), options).read_obj()

    def write_obj(self, obj, options=None):
        """Write a serialized object to this file.

        Args:
            obj: Object to serialize
            options: Optional Map with encoding options

        Returns:
            This File for chaining
        """
        out = self.out()
        try:
            from fanx.ObjEncoder import ObjEncoder
            ObjEncoder(out, options).write_obj(obj)
        finally:
            out.close()
        return self

    def with_out(self, callback, append=False, bufSize=None):
        """Open file for writing, call callback with OutStream, then close.

        Args:
            callback: Function to call with OutStream
            append: If true, append to existing file
            bufSize: Optional buffer size

        Returns:
            Result of callback function
        """
        out = self.out(append, bufSize)
        try:
            result = callback(out)
            return result
        finally:
            out.close()

    def with_in(self, callback, bufSize=None):
        """Open file for reading, call callback with InStream, then close.

        Args:
            callback: Function to call with InStream
            bufSize: Optional buffer size

        Returns:
            Result of callback function
        """
        from .Err import IOErr

        # File must exist to read from it
        if not self._path.exists():
            raise IOErr.make(f"File not found: {self._uri}")

        inp = self.in_(bufSize)
        try:
            result = callback(inp)
            return result
        finally:
            inp.close()

    #########################################################################
    # Trap (dynamic invoke)
    #########################################################################

    def trap(self, name, args=None):
        """Dynamic method invocation."""
        from .Type import _camel_to_snake

        if args is None:
            args = []

        # Handle special names that map to Python-escaped methods
        special_map = {'list': 'list_', 'in': 'in_', 'open': 'open_'}
        method_name = special_map.get(name)

        # If not special, try snake_case conversion
        if method_name is None:
            method_name = _camel_to_snake(name)

        # Try converted name first, then original
        for n in (method_name, name):
            method = getattr(self, n, None)
            if method is not None and callable(method):
                return method(*args)
            # Try property access
            if hasattr(self, n):
                return getattr(self, n)

        from .Err import UnknownSlotErr
        raise UnknownSlotErr.make(f"sys::File.{name}")


class SysOutStream(Obj):
    """SysOutStream - file-backed output stream.

    This is returned by File.out() and reports type sys::SysOutStream
    with base type sys::OutStream.
    """

    def __init__(self, buf, path, append=False):
        self._buf = buf
        self._path = path
        self._append = append

    def typeof(self):
        from .Type import Type
        return Type.find("sys::SysOutStream")

    def write(self, b):
        self._buf.write(b)
        return self

    def write_buf(self, other, n=None):
        self._buf.write_buf(other, n)
        return self

    def write_i2(self, x):
        self._buf.write_i2(x)
        return self

    def write_i4(self, x):
        self._buf.write_i4(x)
        return self

    def write_i8(self, x):
        self._buf.write_i8(x)
        return self

    def write_f4(self, x):
        self._buf.write_f4(x)
        return self

    def write_f8(self, x):
        self._buf.write_f8(x)
        return self

    def write_bool(self, x):
        self._buf.write_bool(x)
        return self

    def write_decimal(self, x):
        self._buf.write_decimal(x)
        return self

    def write_utf(self, s):
        self._buf.write_utf(s)
        return self

    def write_char(self, c):
        self._buf.write_char(c)
        return self

    def write_chars(self, s, off=0, length=None):
        self._buf.write_chars(s, off, length)
        return self

    def print_(self, obj):
        self._buf.print_(obj)
        return self

    print = print_

    def print_line(self, obj=None):
        self._buf.print_line(obj)
        return self

    def flush(self):
        self.sync()
        return self

    def sync(self):
        """Write buffer content to file."""
        data = self._buf._get_data()
        self._path.write_bytes(data)
        return self

    def close(self):
        """Close and write to file."""
        self.sync()
        return True

    def charset(self, val=None):
        return self._buf.charset(val)

    def endian(self, val=None):
        return self._buf.endian(val)


class SysInStream(Obj):
    """SysInStream - file-backed input stream.

    This is returned by File.in_() and reports type sys::SysInStream
    with base type sys::InStream.
    """

    def __init__(self, buf):
        self._buf = buf

    def typeof(self):
        from .Type import Type
        return Type.find("sys::SysInStream")

    def avail(self):
        return self._buf.remaining()

    def read(self):
        return self._buf.read()

    def read_buf(self, other, n):
        return self._buf.read_buf(other, n)

    def unread(self, n):
        self._buf.unread(n)
        return self

    def read_all_buf(self):
        return self._buf.read_all_buf()

    def read_buf_fully(self, buf, n):
        return self._buf.read_buf_fully(buf, n)

    def peek(self):
        return self._buf.peek()

    def read_u1(self):
        return self._buf.read_u1()

    def read_s1(self):
        return self._buf.read_s1()

    def read_u2(self):
        return self._buf.read_u2()

    def read_s2(self):
        return self._buf.read_s2()

    def read_u4(self):
        return self._buf.read_u4()

    def read_s4(self):
        return self._buf.read_s4()

    def read_s8(self):
        return self._buf.read_s8()

    def read_f4(self):
        return self._buf.read_f4()

    def read_f8(self):
        return self._buf.read_f8()

    def read_bool(self):
        return self._buf.read_bool()

    def read_utf(self):
        return self._buf.read_utf()

    def read_char(self):
        return self._buf.read_char()

    def r_char(self):
        """Read character as int code point for Tokenizer compatibility."""
        c = self.read_char()
        return c if c is not None else None

    def unread_char(self, c):
        self._buf.unread_char(c)
        return self

    def peek_char(self):
        return self._buf.peek_char()

    def read_chars(self, n):
        return self._buf.read_chars(n)

    def read_line(self, max_chars=None):
        return self._buf.read_line(max_chars)

    def read_all_str(self, normalize=True):
        return self._buf.read_all_str(normalize)

    def read_all_lines(self):
        return self._buf.read_all_lines()

    def each_line(self, f):
        self._buf.each_line(f)

    def skip(self, n):
        """Skip n bytes."""
        skipped = 0
        for _ in range(int(n)):
            b = self._buf.read()
            if b is None:
                break
            skipped += 1
        return skipped

    def pipe(self, out, n=None, close=True):
        """Pipe data from this InStream to an OutStream."""
        from .Err import IOErr
        try:
            total = 0
            if n is None:
                while True:
                    b = self._buf.read()
                    if b is None:
                        break
                    out.write(b)
                    total += 1
            else:
                for _ in range(int(n)):
                    b = self._buf.read()
                    if b is None:
                        raise IOErr.make("Unexpected end of stream")
                    out.write(b)
                    total += 1
            return total
        finally:
            if close:
                self.close()

    def read_str_token(self, max_chars=None, func=None):
        """Read string token until whitespace or func returns true."""
        from .Int import Int
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""
        c = self._buf.read_char()
        if c is None:
            return None
        chars = []
        while True:
            if func is None:
                terminate = Int.is_space(c)
            else:
                terminate = func.call(c)
            if terminate:
                self._buf.unread_char(c)
                break
            chars.append(chr(c))
            if len(chars) >= max_len:
                break
            c = self._buf.read_char()
            if c is None:
                break
        return ''.join(chars)

    def read_null_terminated_str(self, max_chars=None):
        """Read string until null byte or max chars."""
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""
        c = self._buf.read_char()
        if c is None:
            return None
        chars = []
        while True:
            if c == 0:
                break
            chars.append(chr(c))
            if len(chars) >= max_len:
                break
            c = self._buf.read_char()
            if c is None:
                break
        return ''.join(chars)

    def read_decimal(self):
        """Read decimal as string (Fantom serialization)."""
        s = self._buf.read_utf()
        from .Decimal import Decimal
        return Decimal.from_str(s)

    def charset(self, val=None):
        return self._buf.charset(val)

    def endian(self, val=None):
        return self._buf.endian(val)

    def close(self):
        return True


# Backward compatibility alias
FileOutStream = SysOutStream
