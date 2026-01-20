#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

import subprocess
import os
import threading
from .Obj import Obj


class Process(Obj):
    """
    Process represents an external OS process.
    """

    # Sentinel value to distinguish "no argument" from "argument is None"
    _UNSET = object()

    def __init__(self, command=None):
        self._command = command if command is not None else []
        self._dir = None
        self._env = None  # Lazy init with system env
        self._mergeErr = True
        self._out = None  # Will use Env.cur.out by default
        self._err = None  # Will use Env.cur.err by default
        self._in = None
        self._process = None
        self._started = False
        self._out_explicit = False  # Track if out was explicitly set
        self._err_explicit = False  # Track if err was explicitly set

    @staticmethod
    def make(command=None):
        """Create a new Process with the given command."""
        if command is None:
            return Process()
        return Process(list(command))

    def command(self, val=None):
        """Get or set the command list."""
        if val is None:
            return self._command
        self._check_not_started()
        self._command = list(val)
        return self

    def dir_(self, val=_UNSET):
        """Get or set the working directory."""
        if val is Process._UNSET:
            return self._dir
        self._check_not_started()
        self._dir = val
        return self

    def env(self):
        """Get the environment variables map (mutable)."""
        if self._env is None:
            from .Map import Map
            self._env = Map()
            for k, v in os.environ.items():
                self._env.set_(k, v)
        return self._env

    def merge_err(self, val=None):
        """Get or set whether stderr merges with stdout."""
        if val is None:
            return self._mergeErr
        self._check_not_started()
        self._mergeErr = val
        return self

    def out(self, val=_UNSET):
        """Get or set stdout OutStream."""
        if val is Process._UNSET:
            if self._out is None and not self._out_explicit:
                from .Env import Env
                return Env.cur().out()
            return self._out
        self._check_not_started()
        self._out = val
        self._out_explicit = True
        return self

    def err(self, val=_UNSET):
        """Get or set stderr OutStream."""
        if val is Process._UNSET:
            if self._err is None and not self._err_explicit:
                from .Env import Env
                return Env.cur().err()
            return self._err
        self._check_not_started()
        self._err = val
        self._err_explicit = True
        return self

    def in_(self, val=_UNSET):
        """Get or set stdin InStream."""
        if val is Process._UNSET:
            return self._in
        self._check_not_started()
        self._in = val
        return self

    # Alias for transpiled code that uses 'in' which is Python keyword
    def set_in(self, val):
        return self.in_(val)

    def get_in(self):
        return self.in_()

    def run(self):
        """Start the process. Returns this."""
        if self._started:
            from .Err import Err
            raise Err.make("Process already started")

        # Build command list
        cmd = [str(c) for c in self._command]

        # Build environment
        env = dict(os.environ)
        if self._env is not None:
            for k in self._env.keys():
                env[str(k)] = str(self._env.get(k))

        # Get working directory
        cwd = None
        if self._dir is not None:
            cwd = self._dir.os_path()

        # Determine stream handling
        stdin_pipe = subprocess.PIPE if self._in is not None else None
        stdout_pipe = subprocess.PIPE
        stderr_pipe = subprocess.STDOUT if self._mergeErr else subprocess.PIPE

        # If out is explicitly null, discard output
        if self._out_explicit and self._out is None:
            stdout_pipe = subprocess.DEVNULL
            stderr_pipe = subprocess.DEVNULL if self._mergeErr else subprocess.DEVNULL

        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=stdin_pipe,
                stdout=stdout_pipe,
                stderr=stderr_pipe,
                env=env,
                cwd=cwd
            )
            self._started = True

            # Read stdin data for later use in communicate()
            if self._in is not None:
                self._stdin_data = self._read_all_from_stream(self._in)
            else:
                self._stdin_data = None

        except Exception as e:
            from .Err import IOErr
            raise IOErr.make(f"Failed to start process: {e}")

        return self

    def join(self):
        """Wait for process to exit, return exit code."""
        if not self._started or self._process is None:
            from .Err import Err
            raise Err.make("Process not started")

        # Determine output stream
        out_stream = self._out
        if out_stream is None and not self._out_explicit:
            from .Env import Env
            out_stream = Env.cur().out()

        err_stream = self._err
        if err_stream is None and not self._err_explicit:
            from .Env import Env
            err_stream = Env.cur().err()

        # Read stdout/stderr and write to streams (pass stdin_data if provided)
        stdin_data = getattr(self, '_stdin_data', None)
        stdout_data, stderr_data = self._process.communicate(input=stdin_data)

        # Write stdout
        if stdout_data and out_stream is not None:
            self._write_to_stream(out_stream, stdout_data)

        # Write stderr (if not merged)
        if stderr_data and err_stream is not None:
            self._write_to_stream(err_stream, stderr_data)

        return self._process.returncode

    def kill(self):
        """Kill the process."""
        if self._process is not None:
            self._process.kill()
        return self

    def _check_not_started(self):
        """Raise error if already started."""
        if self._started:
            from .Err import Err
            raise Err.make("Process already running")

    def _read_all_from_stream(self, stream):
        """Read all data from a Fantom InStream."""
        data = bytearray()
        while True:
            b = stream.read()
            if b is None:
                break
            data.append(b)
        return bytes(data)

    def _write_to_stream(self, stream, data):
        """Write bytes to a Fantom OutStream."""
        for b in data:
            stream.write(b)
        if hasattr(stream, 'flush'):
            stream.flush()

    def typeof(self):
        from .Type import Type
        return Type.find("sys::Process")

    def to_str(self):
        return f"Process({self._command})"

    def __str__(self):
        return self.to_str()
