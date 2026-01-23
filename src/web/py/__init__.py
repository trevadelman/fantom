# Hand-written web module for Python
# Contains native implementations for HTTP client using Python's requests library

# Import and patch WebOutStream first
# This ensures the patch is applied before any other code imports it
from . import WebOutStream as _WebOutStreamModule

# Sentinel to distinguish "not passed" from "passed None"
_MISSING = object()


def _style_fixed(self, attrs=_MISSING):
    """Fixed style() that applies default when not passed.

    Uses sentinel to distinguish:
    - style() -> attrs is _MISSING -> use default "type='text/css'"
    - style(None) -> attrs is None -> no default, produces <style>
    Original Fantom: style(Str? attrs := "type='text/css'")
    """
    if attrs is _MISSING:
        attrs = "type='text/css'"
    return self.tag("style", attrs).nl()


_WebOutStreamModule.WebOutStream.style = _style_fixed


def _script_fixed(self, attrs=_MISSING):
    """Fixed script() that applies default when not passed.

    Uses sentinel to distinguish:
    - script() -> attrs is _MISSING -> use default "type='text/javascript'"
    - script(None) -> attrs is None -> no default, produces <script>
    Original Fantom: script(Str? attrs := "type='text/javascript'")
    """
    if attrs is _MISSING:
        attrs = "type='text/javascript'"
    return self.tag("script", attrs).nl()


_WebOutStreamModule.WebOutStream.script = _script_fixed

# Import other patches after WebOutStream
from . import WebClient
from . import Cookie
