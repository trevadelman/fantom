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
    def pathSep():
        """Path separator for current OS."""
        return os.pathsep

    def __init__(self, uri):
        """Create File from Uri or string."""
        from .Uri import Uri

        # Store the URI
        if isinstance(uri, str):
            self._uri = Uri.fromStr(uri)
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
            uri = Uri.fromStr(uri)

        # Create file
        f = File(uri)

        # Check slash consistency with actual file type
        if f._path.exists():
            is_dir = f._path.is_dir()
            uri_is_dir = f._uri.isDir()
            if is_dir and not checkSlash and not uri_is_dir:
                # Auto-correct URI to have trailing slash (per JS behavior)
                f._uri = uri.plusSlash()
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
        uri_str = File._escapePathForUri(uri_str)

        # For absolute paths, create file:// URI with scheme
        if path.is_absolute():
            # Ensure leading / for path portion
            if not uri_str.startswith('/'):
                uri_str = '/' + uri_str
            # Add trailing / for directories
            if path.exists() and path.is_dir() and not uri_str.endswith('/'):
                uri_str += '/'
            # Return with file:// scheme
            return File(Uri.fromStr(f"file://{uri_str}"))

        # For relative paths, no scheme
        if path.exists() and path.is_dir() and not uri_str.endswith('/'):
            uri_str += '/'

        # Create Uri directly to avoid urlparse misinterpreting special chars
        return File(Uri._makeFromPathStr(uri_str))

    @staticmethod
    def _escapePathForUri(path_str):
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
    def osRoots():
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
            return FanList.fromLiteral(roots, "sys::File")
        else:
            # Unix: just root
            return FanList.fromLiteral([File.os("/")], "sys::File")

    @staticmethod
    def createTemp(prefix="fan", suffix=".tmp", dir=None):
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
                if not dir.isDir():
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
        path_str = uri.pathStr() if hasattr(uri, 'pathStr') else str(uri)

        # Handle file:// scheme
        if hasattr(uri, 'scheme') and uri.scheme() == 'file':
            path_str = uri.pathStr()

        # Unescape backslash-escaped special characters for OS path
        path_str = File._unescapePathFromUri(path_str)

        # Remove leading slash for relative paths on Unix
        # Keep it for absolute paths
        if path_str.startswith('/') and len(path_str) > 1:
            # On Windows, /C:/path -> C:/path
            if len(path_str) > 2 and path_str[2] == ':':
                path_str = path_str[1:]

        return Path(path_str.rstrip('/') if path_str != '/' else '/')

    @staticmethod
    def _unescapePathFromUri(path_str):
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

    def toStr(self):
        """Return string representation (same as uri.toStr)."""
        return str(self._uri)

    def __str__(self):
        return self.toStr()

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

    def mimeType(self):
        """Return MIME type based on extension."""
        from .MimeType import MimeType
        ext = self.ext()
        if ext is None:
            return None
        return MimeType.forExt(ext)

    def isDir(self):
        """Return true if this represents a directory."""
        if hasattr(self._uri, 'isDir'):
            return self._uri.isDir()
        return self._path.is_dir() if self._path.exists() else str(self._path).endswith('/')

    def path(self):
        """Return path segments as a list."""
        return self._uri.path() if hasattr(self._uri, 'path') else list(self._path.parts)

    def pathStr(self):
        """Return path as string."""
        return self._uri.pathStr() if hasattr(self._uri, 'pathStr') else str(self._path)

    def osPath(self):
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
        return File(Uri.fromStr(f"file://{uri_str}"))

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

    def isEmpty(self):
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
            mtime = val.toJava() / 1000.0  # Convert from Java millis to Unix seconds
            atime = self._path.stat().st_atime if self._path.exists() else mtime
            os.utime(str(self._path), (atime, mtime))
            return
        # Get modified time
        if not self._path.exists():
            return None
        mtime = self._path.stat().st_mtime
        return DateTime.fromPosix(int(mtime))

    #########################################################################
    # Listing
    #########################################################################

    def list(self, pattern=None):
        """List files in directory."""
        from .List import List as FanList

        if not self._path.exists() or not self._path.is_dir():
            return FanList.fromLiteral([], "sys::File")

        result = []
        for child in self._path.iterdir():
            f = File.os(str(child))
            if pattern is None or self._matches_pattern(child.name, pattern):
                result.append(f)
        return FanList.fromLiteral(result, "sys::File")

    # Alias for transpiled code (list is reserved in Python contexts)
    list_ = list

    def listFiles(self, pattern=None):
        """List files (not directories) in directory."""
        from .List import List as FanList

        if not self._path.exists() or not self._path.is_dir():
            return FanList.fromLiteral([], "sys::File")

        result = []
        for child in self._path.iterdir():
            if child.is_file():
                if pattern is None or self._matches_pattern(child.name, pattern):
                    result.append(File.os(str(child)))
        return FanList.fromLiteral(result, "sys::File")

    def listDirs(self, pattern=None):
        """List directories in directory."""
        from .List import List as FanList

        if not self._path.exists() or not self._path.is_dir():
            return FanList.fromLiteral([], "sys::File")

        result = []
        for child in self._path.iterdir():
            if child.is_dir():
                if pattern is None or self._matches_pattern(child.name, pattern):
                    result.append(File.os(str(child)))
        return FanList.fromLiteral(result, "sys::File")

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
            uri = Uri.fromStr(uri)

        # Resolve URI
        resolved = self._uri.plus(uri) if hasattr(self._uri, 'plus') else None
        if resolved is None:
            # Simple path concatenation
            new_path = self._path / str(uri)
            resolved = Uri.fromStr(new_path.as_posix())

        return File.make(resolved, checkSlash)

    def __add__(self, other):
        return self.plus(other)

    #########################################################################
    # File Management
    #########################################################################

    def create(self):
        """Create this file/directory if it doesn't exist."""
        if self.isDir():
            self._path.mkdir(parents=True, exist_ok=True)
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.touch()
        return self

    def createFile(self, name):
        """Create a child file in this directory."""
        from .Uri import Uri
        child_path = self._path / name
        child_path.touch()
        return File.os(str(child_path))

    def createDir(self, name):
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

    def deleteOnExit(self):
        """Mark file for deletion when process exits."""
        import atexit
        atexit.register(lambda: self._path.unlink(missing_ok=True) if self._path.exists() else None)
        return self

    def moveTo(self, dest):
        """Move this file to destination."""
        from .Err import ArgErr, IOErr

        if isinstance(dest, File):
            dest_path = dest._path
            dest_is_dir = dest.isDir()  # Use URI-based check
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

    def moveInto(self, dest):
        """Move this file into destination directory."""
        from .Uri import Uri
        if isinstance(dest, File):
            new_path = dest._path / self._path.name
        else:
            new_path = Path(str(dest)) / self._path.name
        # Preserve directory nature - add trailing slash if source is directory
        path_str = new_path.as_posix()
        if self._path.is_dir() and not path_str.endswith('/'):
            path_str += '/'
        if new_path.is_absolute() and not path_str.startswith('/'):
            path_str = '/' + path_str
        return self.moveTo(File(Uri.fromStr(path_str)))

    def copyTo(self, dest, options=None):
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
        if self.isDir() != dest.isDir():
            if self.isDir():
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
        self._doCopyTo(dest, exclude, overwrite)
        return dest

    def _doCopyTo(self, to, exclude, overwrite):
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
        if self.isDir():
            to.create()
            kids = self.list()
            # Use size property or len() depending on List implementation
            size = kids.size if isinstance(kids.size, int) else kids.size()
            for i in range(size):
                kid = kids.get(i)
                kid._doCopyTo(to._plusNameOf(kid), exclude, overwrite)
        # Copy file contents
        else:
            self._doCopyFile(to)

    def _doCopyFile(self, to):
        """Copy file contents to destination."""
        # Ensure parent directory exists
        to._path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(self._path), str(to._path))

    def _plusNameOf(self, x):
        """Get this + name of x (with trailing slash if x is dir)."""
        from .Uri import Uri
        name = x.name()
        if x.isDir():
            name += "/"
        return self.plus(Uri.fromStr(name))

    def copyInto(self, dest, options=None):
        """Copy this file into destination directory.

        Args:
            dest: Directory to copy into
            options: Copy options (exclude, overwrite)

        Creates a File with the correct dir/file URI based on source.
        """
        from .Err import ArgErr

        if not dest.isDir():
            raise ArgErr.make(f"Not a dir: `{dest}`")

        return self.copyTo(dest._plusNameOf(self), options)

    def rename(self, newName):
        """Rename this file."""
        new_path = self._path.parent / newName
        self._path.rename(new_path)
        return File.os(str(new_path))

    #########################################################################
    # I/O
    #########################################################################

    def open(self, mode="rw"):
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

    def readAllStr(self, normalizeNewlines=True):
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

    def readAllLines(self):
        """Read file as list of lines."""
        from .List import List as FanList
        content = self.readAllStr()
        lines = content.split('\n')
        # Remove trailing empty string from final newline
        if lines and lines[-1] == '':
            lines = lines[:-1]
        return FanList.fromLiteral(lines, "sys::Str")

    def readAllBuf(self):
        """Read entire file into buffer."""
        from .Buf import Buf
        data = self._path.read_bytes()
        return Buf.fromBytes(data)

    def eachLine(self, callback):
        """Iterate over each line in file."""
        for line in self.readAllLines():
            callback(line)

    def withOut(self, callback, append=False, bufSize=None):
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

    def withIn(self, callback, bufSize=None):
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

    #########################################################################
    # Trap (dynamic invoke)
    #########################################################################

    def trap(self, name, args=None):
        """Dynamic method invocation."""
        if args is None:
            args = []
        method = getattr(self, name, None)
        if method is not None and callable(method):
            return method(*args)
        # Try property access
        if hasattr(self, name):
            return getattr(self, name)
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

    def writeBuf(self, other, n=None):
        self._buf.writeBuf(other, n)
        return self

    def writeI2(self, x):
        self._buf.writeI2(x)
        return self

    def writeI4(self, x):
        self._buf.writeI4(x)
        return self

    def writeI8(self, x):
        self._buf.writeI8(x)
        return self

    def writeF4(self, x):
        self._buf.writeF4(x)
        return self

    def writeF8(self, x):
        self._buf.writeF8(x)
        return self

    def writeBool(self, x):
        self._buf.writeBool(x)
        return self

    def writeDecimal(self, x):
        self._buf.writeDecimal(x)
        return self

    def writeUtf(self, s):
        self._buf.writeUtf(s)
        return self

    def writeChar(self, c):
        self._buf.writeChar(c)
        return self

    def writeChars(self, s, off=0, length=None):
        self._buf.writeChars(s, off, length)
        return self

    def print_(self, obj):
        self._buf.print_(obj)
        return self

    print = print_

    def printLine(self, obj=None):
        self._buf.printLine(obj)
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

    def readBuf(self, other, n):
        return self._buf.readBuf(other, n)

    def unread(self, n):
        self._buf.unread(n)
        return self

    def readAllBuf(self):
        return self._buf.readAllBuf()

    def readBufFully(self, buf, n):
        return self._buf.readBufFully(buf, n)

    def peek(self):
        return self._buf.peek()

    def readU1(self):
        return self._buf.readU1()

    def readS1(self):
        return self._buf.readS1()

    def readU2(self):
        return self._buf.readU2()

    def readS2(self):
        return self._buf.readS2()

    def readU4(self):
        return self._buf.readU4()

    def readS4(self):
        return self._buf.readS4()

    def readS8(self):
        return self._buf.readS8()

    def readF4(self):
        return self._buf.readF4()

    def readF8(self):
        return self._buf.readF8()

    def readBool(self):
        return self._buf.readBool()

    def readUtf(self):
        return self._buf.readUtf()

    def readChar(self):
        return self._buf.readChar()

    def unreadChar(self, c):
        self._buf.unreadChar(c)
        return self

    def peekChar(self):
        return self._buf.peekChar()

    def readChars(self, n):
        return self._buf.readChars(n)

    def readLine(self, max_chars=None):
        return self._buf.readLine(max_chars)

    def readAllStr(self, normalize=True):
        return self._buf.readAllStr(normalize)

    def readAllLines(self):
        return self._buf.readAllLines()

    def eachLine(self, f):
        self._buf.eachLine(f)

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

    def readStrToken(self, max_chars=None, func=None):
        """Read string token until whitespace or func returns true."""
        from .Int import Int
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""
        c = self._buf.readChar()
        if c is None:
            return None
        chars = []
        while True:
            if func is None:
                terminate = Int.isSpace(c)
            else:
                terminate = func.call(c)
            if terminate:
                self._buf.unreadChar(c)
                break
            chars.append(chr(c))
            if len(chars) >= max_len:
                break
            c = self._buf.readChar()
            if c is None:
                break
        return ''.join(chars)

    def readNullTerminatedStr(self, max_chars=None):
        """Read string until null byte or max chars."""
        max_len = int(max_chars) if max_chars is not None else 2147483647
        if max_len <= 0:
            return ""
        c = self._buf.readChar()
        if c is None:
            return None
        chars = []
        while True:
            if c == 0:
                break
            chars.append(chr(c))
            if len(chars) >= max_len:
                break
            c = self._buf.readChar()
            if c is None:
                break
        return ''.join(chars)

    def readDecimal(self):
        """Read decimal as string (Fantom serialization)."""
        s = self._buf.readUtf()
        from .Decimal import Decimal
        return Decimal.fromStr(s)

    def charset(self, val=None):
        return self._buf.charset(val)

    def endian(self, val=None):
        return self._buf.endian(val)

    def close(self):
        return True


# Backward compatibility alias
FileOutStream = SysOutStream
