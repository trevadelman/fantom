#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

import shutil
from fan.sys.Obj import Obj


class FileStore(Obj):
    """FileStore represents storage for a file.

    This is the abstract base class - LocalFileStore is the
    implementation for local file system storage.
    """

    def __init__(self):
        pass

    def total_space(self):
        """Total storage space in bytes, or null if unknown."""
        return None

    def avail_space(self):
        """Available storage space in bytes, or null if unknown."""
        return None

    def free_space(self):
        """Free storage space in bytes, or null if unknown."""
        return None


class LocalFileStore(FileStore):
    """LocalFileStore is the FileStore for local file system files."""

    def __init__(self, path=None):
        """Create LocalFileStore for the given path.

        Args:
            path: Path to get disk usage for (defaults to root)
        """
        super().__init__()
        self._path = path if path else "/"

    def typeof(self):
        from .Type import Type
        return Type.find("sys::LocalFileStore")

    def total_space(self):
        """Total storage space in bytes."""
        try:
            usage = shutil.disk_usage(self._path)
            return usage.total
        except Exception:
            return None

    def avail_space(self):
        """Available storage space in bytes (usable by non-root user)."""
        try:
            usage = shutil.disk_usage(self._path)
            # On most systems, 'free' represents space available to the user
            # This accounts for reserved blocks on Unix systems
            return usage.free
        except Exception:
            return None

    def free_space(self):
        """Free storage space in bytes (total unallocated)."""
        try:
            usage = shutil.disk_usage(self._path)
            return usage.free
        except Exception:
            return None
