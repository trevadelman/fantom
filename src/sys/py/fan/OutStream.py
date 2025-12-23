#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class OutStream(Obj):
    """
    OutStream base class for writing bytes and characters.
    """

    # XML escape flags (as static methods for transpiler compatibility)
    @staticmethod
    def xmlEscNewlines():
        return 0x01

    @staticmethod
    def xmlEscQuotes():
        return 0x02

    @staticmethod
    def xmlEscUnicode():
        return 0x04

    def __init__(self, out=None):
        self._out = out
        self._charset = None
        self._endian = None

    def write(self, b):
        """Write a single byte. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.write(b)
            return self
        raise NotImplementedError("OutStream.write not implemented")

    def writeBuf(self, buf, n=None):
        """Write bytes from buffer. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeBuf(buf, n)
            return self
        raise NotImplementedError("OutStream.writeBuf not implemented")

    def writeChar(self, c):
        """Write a single character using current charset. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeChar(c)
            return self
        raise NotImplementedError("OutStream.writeChar not implemented")

    def writeChars(self, s, off=0, length=None):
        """Write characters from string. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeChars(s, off, length)
            return self
        raise NotImplementedError("OutStream.writeChars not implemented")

    def print_(self, obj):
        """Print object as string. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.print_(obj)
            return self
        raise NotImplementedError("OutStream.print not implemented")

    print = print_

    def printLine(self, obj=None):
        """Print object followed by newline. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.printLine(obj)
            return self
        raise NotImplementedError("OutStream.printLine not implemented")

    def writeI2(self, x):
        """Write 16-bit integer. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeI2(x)
            return self
        raise NotImplementedError("OutStream.writeI2 not implemented")

    def writeI4(self, x):
        """Write 32-bit integer. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeI4(x)
            return self
        raise NotImplementedError("OutStream.writeI4 not implemented")

    def writeI8(self, x):
        """Write 64-bit integer. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeI8(x)
            return self
        raise NotImplementedError("OutStream.writeI8 not implemented")

    def writeF4(self, x):
        """Write 32-bit float. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeF4(x)
            return self
        raise NotImplementedError("OutStream.writeF4 not implemented")

    def writeF8(self, x):
        """Write 64-bit float. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeF8(x)
            return self
        raise NotImplementedError("OutStream.writeF8 not implemented")

    def writeBool(self, x):
        """Write boolean. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeBool(x)
            return self
        raise NotImplementedError("OutStream.writeBool not implemented")

    def writeUtf(self, s):
        """Write UTF-8 string with length prefix. Returns this (for method chaining)."""
        if self._out is not None:
            self._out.writeUtf(s)
            return self
        raise NotImplementedError("OutStream.writeUtf not implemented")

    def flush(self):
        """Flush the stream."""
        if self._out is not None:
            return self._out.flush()
        return self

    def sync(self):
        """Sync the stream."""
        return self.flush()

    def close(self):
        """Close the stream."""
        if self._out is not None:
            return self._out.close()
        return True

    def charset(self, val=None):
        """Get or set charset."""
        if val is None:
            if self._charset is None:
                from .Charset import Charset
                self._charset = Charset.utf8()
            return self._charset
        self._charset = val
        return self

    def endian(self, val=None):
        """Get or set endian."""
        if val is None:
            if self._endian is None:
                from .Endian import Endian
                self._endian = Endian.big()
            return self._endian
        self._endian = val
        return self

    def typeof(self):
        from .Type import Type
        return Type.find("sys::OutStream")
