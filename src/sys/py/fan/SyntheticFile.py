#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .File import File


class SyntheticFile(File):
    """SyntheticFile provides default no-op implementation of File API.

    This is a virtual file not backed by any real filesystem path.
    """

    def __init__(self, uri):
        """Constructor - store URI without resolving to path."""
        from .Uri import Uri

        if isinstance(uri, str):
            self._uri = Uri.fromStr(uri)
        elif isinstance(uri, Uri):
            self._uri = uri
        else:
            self._uri = uri

        # SyntheticFile has no real path
        self._path = None

    @staticmethod
    def make(uri):
        """Factory method to create SyntheticFile."""
        return SyntheticFile(uri)

    def typeof(self):
        from .Type import Type
        return Type.find("util::SyntheticFile")

    def exists(self):
        """Return false - synthetic files don't exist."""
        return False

    def size(self):
        """Return null."""
        return None

    def modified(self, val=None):
        """Get returns null, set is no-op."""
        if val is not None:
            return  # No-op
        return None

    def osPath(self):
        """Return null - no OS path."""
        return None

    def parent(self):
        """Return null."""
        return None

    def list(self, pattern=None):
        """Return empty list."""
        from .List import List as FanList
        return FanList.fromLiteral([], "sys::File")

    list_ = list

    def normalize(self):
        """Return this."""
        return self

    def plus(self, uri, checkSlash=True):
        """Return another SyntheticFile."""
        from .Uri import Uri
        if isinstance(uri, str):
            uri = Uri.fromStr(uri)
        resolved = self._uri.plus(uri) if hasattr(self._uri, 'plus') else Uri.fromStr(str(self._uri) + str(uri))
        return SyntheticFile(resolved)

    def create(self):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be created")

    def moveTo(self, to):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be moved")

    def delete(self):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be deleted")

    def deleteOnExit(self):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be deleted")

    def open(self, mode="rw"):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be opened")

    def mmap(self, mode="rw", pos=0, size=None):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be memory mapped")

    def in_(self, bufSize=None):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be read")

    def out(self, append=False, bufSize=None):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be written")

    def readAllStr(self, normalizeNewlines=True):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be read")

    def readAllLines(self):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be read")

    def readAllBuf(self):
        """Raise IOErr."""
        from .Err import IOErr
        raise IOErr.make("SyntheticFile cannot be read")
