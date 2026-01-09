#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .File import File


class MemFile(File):
    """In-memory file backed by a Buf.

    MemFile is used when Buf.toFile() is called to create a virtual file
    that is backed by the buffer's contents, not the filesystem.
    """

    def __init__(self, buf, uri):
        """Create MemFile backed by buffer with given URI."""
        super().__init__(uri)
        self._buf = buf
        from .DateTime import DateTime
        self._ts = DateTime.now()
        # Clear the _path attribute since this isn't a real file
        self._path = None

    @staticmethod
    def make(buf, uri):
        """Create MemFile from buffer and URI."""
        return MemFile(buf, uri)

    def exists(self):
        """MemFile always exists."""
        return True

    def size(self):
        """Return buffer size."""
        return self._buf.size()

    def modified(self, val=None):
        """Get or set modified time."""
        if val is None:
            return self._ts
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def os_path(self):
        """MemFile has no OS path."""
        return None

    def parent(self):
        """MemFile has no parent."""
        return None

    def list(self, regex=None):
        """MemFile has no children."""
        from .List import List
        from .Type import Type
        return List.from_list([], "sys::File")

    def normalize(self):
        """Return self."""
        return self

    def plus(self, uri, check_slash=True):
        """Not supported for MemFile."""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def create(self):
        """Not supported for MemFile."""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def move_to(self, to):
        """Not supported for MemFile."""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def delete(self):
        """Not supported for MemFile."""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def delete_on_exit(self):
        """Not supported for MemFile."""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def open(self, mode=None):
        """Not supported for MemFile."""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def mmap(self, mode=None, pos=None, size=None):
        """Not supported for MemFile."""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def in_(self, buf_size=None):
        """Return InStream for reading buffer contents."""
        # Reset buffer position to start for reading
        self._buf.seek(0)
        return self._buf.in_()

    def out(self, append=False, buf_size=None):
        """Not supported for MemFile."""
        from .Err import UnsupportedErr
        raise UnsupportedErr.make("MemFile")

    def read_all_buf(self):
        """Read entire buffer content."""
        self._buf.seek(0)
        return self._buf.read_all_buf()

    def read_all_str(self, normalize=True):
        """Read entire content as string."""
        self._buf.seek(0)
        return self._buf.read_all_str(normalize)

    def to_str(self):
        """Return URI string."""
        return self._uri.to_str()

    def __str__(self):
        return self.to_str()
