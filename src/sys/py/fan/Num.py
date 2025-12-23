#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Num(Obj):
    """Abstract base class for numeric types (Int, Float, Decimal)"""

    @staticmethod
    def toInt(val):
        """Convert to Int"""
        if val is None:
            return None
        if isinstance(val, float):
            return int(val)
        return int(val)

    @staticmethod
    def toFloat(val):
        """Convert to Float"""
        if val is None:
            return None
        return float(val)

    @staticmethod
    def toDecimal(val):
        """Convert to Decimal - stub returns float for now"""
        if val is None:
            return None
        # Return a Decimal object when we implement it
        # For now, just return float
        return float(val)

    @staticmethod
    def localeDecimal():
        """Get locale decimal separator"""
        return "."

    @staticmethod
    def localeGrouping():
        """Get locale grouping separator"""
        return ","

    @staticmethod
    def localeMinus():
        """Get locale minus sign"""
        return "-"

    @staticmethod
    def localePercent():
        """Get locale percent sign"""
        return "%"

    @staticmethod
    def localePosInf():
        """Get locale positive infinity symbol"""
        return "INF"

    @staticmethod
    def localeNegInf():
        """Get locale negative infinity symbol"""
        return "-INF"

    @staticmethod
    def localeNaN():
        """Get locale NaN symbol"""
        return "NaN"
