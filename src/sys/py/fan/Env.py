#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Env(Obj):
    """Env stub for bootstrap - returns 'py' runtime"""

    _instance = None

    @staticmethod
    def cur():
        if Env._instance is None:
            Env._instance = Env()
        return Env._instance

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
        result = List.fromLiteral(args_list, "sys::Str")
        return result.toImmutable()

    def idHash(self, obj):
        """Get identity hash code for object.

        Returns the same value for the lifetime of the object.
        """
        if obj is None:
            return 0
        return id(obj)

    def path(self):
        """Get search path for files.

        Returns list of directories to search for files.
        The first is workDir, last is homeDir.
        """
        from .List import List
        # Default path is workDir then homeDir
        work = self.workDir()
        home = self.homeDir()
        # workDir and homeDir might be the same
        if work == home:
            result = List.fromLiteral([work], "sys::File")
        else:
            result = List.fromLiteral([work, home], "sys::File")
        return result.toImmutable()

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

    def host(self):
        import socket
        return socket.gethostname()

    def user(self):
        import os
        return os.environ.get("USER", "unknown")

    def homeDir(self):
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

    def workDir(self):
        """Get current working directory as File."""
        import os
        from .File import File
        return File.os(os.getcwd() + os.sep)

    def tempDir(self):
        """Get temp directory as File."""
        import os
        import tempfile
        from .File import File
        return File.os(tempfile.gettempdir() + os.sep)

    def vars(self):
        """Return environment variables as a Map[Str,Str].

        Returns an immutable Map containing environment variables.
        For Python runtime, this will NOT include java.home since we're not on JVM.
        """
        import os
        from .Map import Map

        # Create a map from Python environment variables
        env_map = Map()
        for key, value in os.environ.items():
            env_map.set(key, value)

        return env_map.toImmutable()

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

    def writeChars(self, s, off=0, length=None):
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

    def printLine(self, obj=None):
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

    def writeChars(self, s, off=0, length=None):
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

    def printLine(self, obj=None):
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

    def readLine(self, max_chars=None):
        import sys
        line = sys.stdin.readline()
        if not line:
            return None
        # Remove trailing newline
        return line.rstrip('\n\r')

    def readAllStr(self):
        import sys
        return sys.stdin.read()

    def close(self):
        return True
