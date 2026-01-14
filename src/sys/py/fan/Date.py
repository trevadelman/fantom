#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#
# Date module - re-exports Date class from DateTime module
# This file structure matches the JavaScript pattern (Date.js)
#

from .DateTime import Date

# Re-export everything - allows 'from fan.sys.Date import Date' to work
__all__ = ['Date']
