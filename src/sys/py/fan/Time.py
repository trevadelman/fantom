#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#
# Time module - re-exports Time class from DateTime module
# This file structure matches the JavaScript pattern (Time.js)
#

from .DateTime import Time

# Re-export everything - allows 'from fan.sys.Time import Time' to work
__all__ = ['Time']
