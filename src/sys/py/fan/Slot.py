#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


# Flag constants (from FConst)
class FConst:
    """Fantom compiler flag constants."""
    Public = 0x00000001
    Private = 0x00000002
    Protected = 0x00000004
    Internal = 0x00000008
    Native = 0x00000010
    Enum = 0x00000020
    Mixin = 0x00000040
    Final = 0x00000080
    Ctor = 0x00000100
    Override = 0x00000200
    Abstract = 0x00000400
    Static = 0x00000800
    Virtual = 0x00001000
    Const = 0x00002000
    Readonly = 0x00004000
    Facet = 0x00008000
    Getter = 0x00010000
    Setter = 0x00020000
    Synthetic = 0x00100000
    Once = 0x00200000


class Slot(Obj):
    """Base class for Field and Method reflection."""

    def __init__(self, parent=None, name="", flags=0):
        super().__init__()
        self._parent = parent
        self._name = name
        self._flags = flags

    def parent(self):
        """Get declaring type."""
        return self._parent

    def name(self):
        """Get slot name."""
        return self._name

    def flags_(self):
        """Get raw flags value."""
        return self._flags

    def qname(self):
        """Get qualified name (Type.slotName)."""
        if self._parent:
            return f"{self._parent.qname()}.{self._name}"
        return self._name

    def isField(self):
        """Return true if this is a Field."""
        return False

    def isMethod(self):
        """Return true if this is a Method."""
        return False

    def isCtor(self):
        """Return true if this is a constructor."""
        return (self._flags & FConst.Ctor) != 0

    def isPublic(self):
        """Return true if public access."""
        return (self._flags & FConst.Public) != 0 or self._flags == 0  # Default to public

    def isProtected(self):
        """Return true if protected access."""
        return (self._flags & FConst.Protected) != 0

    def isPrivate(self):
        """Return true if private access."""
        return (self._flags & FConst.Private) != 0

    def isInternal(self):
        """Return true if internal access."""
        return (self._flags & FConst.Internal) != 0

    def isStatic(self):
        """Return true if static."""
        return (self._flags & FConst.Static) != 0

    def isVirtual(self):
        """Return true if virtual."""
        return (self._flags & FConst.Virtual) != 0

    def isAbstract(self):
        """Return true if abstract."""
        return (self._flags & FConst.Abstract) != 0

    def isOverride(self):
        """Return true if override."""
        return (self._flags & FConst.Override) != 0

    def isFinal(self):
        """Return true if final."""
        return (self._flags & FConst.Final) != 0

    def isConst(self):
        """Return true if const."""
        return (self._flags & FConst.Const) != 0

    def isNative(self):
        """Return true if native."""
        return (self._flags & FConst.Native) != 0

    def isSynthetic(self):
        """Return true if synthetic."""
        return (self._flags & FConst.Synthetic) != 0

    def toStr(self):
        return self.qname()

    def literalEncode(self, out):
        """Encode for serialization.

        Slot literals are written as: ParentType#slotName
        For example: sys::Float#nan
        """
        out.w(self._parent.qname())
        out.w("#")
        out.w(self._name)

    def __repr__(self):
        return self.toStr()

    def trap(self, name, args=None):
        """Dynamic method invocation via -> operator.

        Allows: slot->methodName(args)

        Args:
            name: Method name to invoke
            args: List of arguments (default empty list)
        """
        if args is None:
            args = []

        # Look up method on self
        method = getattr(self, name, None)
        if method is not None and callable(method):
            return method(*args) if args else method()

        # Not found
        from .Err import UnknownSlotErr
        raise UnknownSlotErr.make(f"{self.qname()}.{name}")

    @staticmethod
    def find(qname, checked=True):
        """Find slot by qualified name like 'sys::Str.size'.

        Args:
            qname: Qualified name in format 'pod::Type.slot'
            checked: If True, raise UnknownSlotErr if not found

        Returns:
            Slot instance or None
        """
        # Parse qname like "sys::Str.size" or "testSys::Foo.bar"
        # Find the last '.' which separates type from slot
        dot_idx = qname.rfind('.')
        if dot_idx < 0:
            if checked:
                from .Err import UnknownSlotErr
                raise UnknownSlotErr.make(f"Invalid slot qname: {qname}")
            return None

        type_qname = qname[:dot_idx]
        slot_name = qname[dot_idx + 1:]

        # Find the type
        from .Type import Type
        type_obj = Type.find(type_qname, checked)
        if type_obj is None:
            return None

        # Find the slot on the type
        return type_obj.slot(slot_name, checked)

    @staticmethod
    def findMethod(qname, checked=True):
        """Find method by qualified name."""
        slot = Slot.find(qname, checked)
        if slot is None:
            return None
        if slot.isMethod():
            return slot
        if checked:
            from .Err import CastErr
            raise CastErr.make(f"{qname} is not a method")
        return None

    @staticmethod
    def findField(qname, checked=True):
        """Find field by qualified name."""
        slot = Slot.find(qname, checked)
        if slot is None:
            return None
        if slot.isField():
            return slot
        if checked:
            from .Err import CastErr
            raise CastErr.make(f"{qname} is not a field")
        return None

    @staticmethod
    def findFunc(qname, checked=True):
        """Find slot by qualified name and return its func.

        This is a convenience method that finds a slot (typically a Method)
        and returns its Func wrapper for direct invocation.

        Args:
            qname: Qualified name in format 'pod::Type.slot'
            checked: If True, raise UnknownSlotErr if not found

        Returns:
            Func wrapper or None if not found
        """
        slot = Slot.find(qname, checked)
        if slot is None:
            return None
        # Return the func wrapper for the slot
        if hasattr(slot, 'func') and callable(slot.func):
            return slot.func()
        return None
