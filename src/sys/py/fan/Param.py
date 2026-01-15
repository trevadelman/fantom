#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Param(Obj):
    """Method parameter metadata for reflection.

    Represents a single parameter of a Fantom method, including:
    - name: Parameter name
    - type: Parameter Type
    - hasDefault: Whether parameter has a default value
    """

    def __init__(self, name, param_type, has_default=False):
        """Create a Param object.

        Args:
            name: Parameter name
            param_type: Parameter Type object
            has_default: Whether this parameter has a default value
        """
        super().__init__()
        self._name = name
        self._type = param_type
        self._has_default = has_default

    def name(self):
        """Get parameter name."""
        return self._name

    def type(self):
        """Get parameter type - lazily resolves from string signature if needed.

        Type resolution is deferred to avoid circular imports during module
        initialization. The param type may be stored as a string and resolved
        to a Type object on first access.
        """
        if isinstance(self._type, str):
            from .Type import Type
            self._type = Type.find(self._type, False) or Type.find("sys::Obj")
        return self._type

    def type_(self):
        """Alias for type() - Fantom compatible."""
        return self.type()

    def has_default(self):
        """Check if parameter has a default value."""
        return self._has_default

    def to_str(self):
        """String representation."""
        return f"{self._type.signature() if self._type else '?'} {self._name}"

    def __repr__(self):
        return f"Param({self._name}, {self._type})"

    @staticmethod
    def no_params():
        """Return an empty immutable list of params."""
        return []
