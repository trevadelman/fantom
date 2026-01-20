#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Num(Obj):
    """Abstract base class for numeric types (Int, Float, Decimal)"""

    @staticmethod
    def to_int(val):
        """Convert to Int"""
        import math
        if val is None:
            return None
        if isinstance(val, float):
            # Handle special values - Fantom returns maxVal/minVal for infinity
            if math.isnan(val):
                return 0
            if math.isinf(val):
                if val > 0:
                    return 9223372036854775807  # Int.maxVal
                else:
                    return -9223372036854775808  # Int.minVal
            return int(val)
        return int(val)

    @staticmethod
    def to_float(val):
        """Convert to Float"""
        if val is None:
            return None
        return float(val)

    @staticmethod
    def to_decimal(val):
        """Convert to Decimal - stub returns float for now"""
        if val is None:
            return None
        # Return a Decimal object when we implement it
        # For now, just return float
        return float(val)

    @staticmethod
    def locale_decimal():
        """Get locale decimal separator for the current locale.

        Returns "." for English locales, "," for most European locales.
        """
        from .Locale import Locale
        locale = Locale.cur()
        lang = locale.lang() if hasattr(locale, 'lang') else 'en'
        # English uses period, most European locales use comma
        if lang == 'en':
            return "."
        return ","

    @staticmethod
    def locale_grouping():
        """Get locale grouping separator for the current locale.

        Returns "," for English locales, non-breaking space for most European locales.
        """
        from .Locale import Locale
        locale = Locale.cur()
        lang = locale.lang() if hasattr(locale, 'lang') else 'en'
        # English uses comma, most European locales use non-breaking space
        if lang == 'en':
            return ","
        return "\u00a0"  # Non-breaking space

    @staticmethod
    def locale_minus():
        """Get locale minus sign"""
        return "-"

    @staticmethod
    def locale_percent():
        """Get locale percent sign"""
        return "%"

    @staticmethod
    def locale_pos_inf():
        """Get locale positive infinity symbol.

        Returns the infinity symbol (∞) which matches Java/JVM behavior.
        JS runtime may return "Infinity" depending on browser/platform.
        """
        return "\u221e"  # ∞

    @staticmethod
    def locale_neg_inf():
        """Get locale negative infinity symbol.

        Returns minus sign with infinity symbol (-∞).
        """
        return "-\u221e"  # -∞

    @staticmethod
    def locale_na_n():
        """Get locale NaN symbol.

        Returns the replacement character (U+FFFD) which matches Java/JVM behavior.
        JS runtime may return "NaN" depending on browser/platform.
        """
        return "\ufffd"  # Replacement character
