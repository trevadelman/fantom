#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Facet(Obj):
    """Base class for facets (annotations/metadata on types and slots).

    In Fantom, facets are compile-time annotations that can be applied to
    types, slots (fields and methods), and enum values. This base class
    provides the common interface for all facet types.
    """

    def typeof(self):
        """Return Fantom Type for this Facet."""
        from .Type import Type
        return Type.find("sys::Facet")

    def is_immutable(self):
        """Facets are always immutable in Fantom (they are const)."""
        return True
