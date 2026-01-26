#
# web::WebClient - Python native implementation
#
# HTTP client using Python's standard library (urllib).
# This replaces the Fantom implementation which uses raw TcpSocket.
#

import io
import gzip
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
import ssl
from fan.sys.Obj import Obj
from fan.sys.Buf import Buf
from fan.sys.Map import Map


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Handler that prevents automatic redirects."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class WebClient(Obj):
    """HTTP client using Python's standard library.

    This is a Python-native implementation that wraps urllib.request
    to provide the Fantom WebClient API.

    Usage:
        c = WebClient.make(Uri.from_str("http://example.com/api"))
        c.req_method("POST")
        c.req_headers()["Content-Type"] = "application/json"
        c.write_req()
        c.req_out().print_('{"key": "value"}').close()
        c.read_res()
        result = c.res_in().read_all_str()
        c.close()
    """

    @staticmethod
    def make(req_uri=None):
        """Create a new WebClient with optional request URI."""
        # Validate URI is absolute if provided
        if req_uri is not None:
            WebClient._validate_uri(req_uri)
        return WebClient(req_uri)

    @staticmethod
    def _validate_uri(uri):
        """Validate that URI is absolute."""
        if uri is None:
            return
        # Check if URI is absolute
        is_abs = False
        if hasattr(uri, 'is_abs'):
            is_abs = uri.is_abs()
        elif hasattr(uri, 'to_str'):
            uri_str = uri.to_str()
            is_abs = uri_str.startswith('http://') or uri_str.startswith('https://')
        else:
            uri_str = str(uri)
            is_abs = uri_str.startswith('http://') or uri_str.startswith('https://')

        if not is_abs:
            from fan.sys.Err import ArgErr
            raise ArgErr.make(f"reqUri is not absolute: {uri}")

    def __init__(self, req_uri=None):
        super().__init__()
        # Validate URI is absolute if provided
        if req_uri is not None:
            WebClient._validate_uri(req_uri)

        # Request state - use Fantom Map with case_insensitive=True
        self._req_uri = req_uri
        self._req_method = "GET"
        self._req_headers = Map.from_literal([], [], "sys::Str", "sys::Str")
        self._req_headers.case_insensitive = True
        self._req_headers["Accept-Encoding"] = "gzip"
        self._req_body = None  # Buffer for request body

        # Response state - use Fantom Map with case_insensitive=True
        self._res_code = 0
        self._res_phrase = ""
        self._res_version = None  # HTTP version as Version object
        self._res_headers = Map.from_literal([], [], "sys::Str", "sys::Str")
        self._res_headers.case_insensitive = True
        self._response = None  # urllib response object
        self._response_content = None  # Cached response content

        # Configuration
        self._cookies = []
        self._follow_redirects = True
        self._socket_config = None

        # Cookie jar for urllib
        self._cookie_jar = http.cookiejar.CookieJar()

        # Stream wrappers
        self._req_out_stream = None
        self._res_in_stream = None

    def _build_opener(self, use_https=False):
        """Build urllib opener with appropriate handlers."""
        handlers = [urllib.request.HTTPCookieProcessor(self._cookie_jar)]
        if not self._follow_redirects:
            handlers.append(NoRedirectHandler())
        if use_https:
            # Create SSL context
            # Check if socket_config disables SSL verification (for testing)
            verify_ssl = True
            if self._socket_config is not None:
                if hasattr(self._socket_config, '_verify_ssl'):
                    verify_ssl = self._socket_config._verify_ssl

            if verify_ssl:
                ssl_context = ssl.create_default_context()
            else:
                # Disable verification for testing (not recommended for production)
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ssl_context))
        return urllib.request.build_opener(*handlers)

    # =========================================================================
    # Request Configuration
    # =========================================================================

    def req_uri(self, val=None):
        """Get or set the request URI."""
        if val is None:
            return self._req_uri
        self._req_uri = val
        return self

    def req_method(self, val=None):
        """Get or set the HTTP method (GET, POST, etc.)."""
        if val is None:
            return self._req_method
        self._req_method = val.upper() if isinstance(val, str) else str(val).upper()
        return self

    def req_headers(self):
        """Get the request headers (case-insensitive dict).

        Returns a wrapper that allows both Fantom Map operations and direct access.
        """
        if not hasattr(self, '_req_headers_wrapper'):
            self._req_headers_wrapper = HeadersWrapper(self._req_headers)
        return self._req_headers_wrapper

    def cookies(self, val=None):
        """Get or set cookies for the request.

        When setting cookies, the Cookie header is automatically updated.
        Returns a Fantom List (not Python list) for Fantom compatibility.
        """
        if val is None:
            from fan.sys.List import List
            return List.from_list(self._cookies)
        # Accept either Fantom List or Python list
        if hasattr(val, 'to_list'):
            self._cookies = val.to_list()
        else:
            self._cookies = val if val else []
        # Update Cookie header when cookies are set
        self._update_cookie_header()
        return self

    def _update_cookie_header(self):
        """Update the Cookie request header based on current cookies."""
        if not self._cookies:
            # Remove Cookie header if no cookies
            if "Cookie" in self._req_headers:
                del self._req_headers["Cookie"]
            return
        # Build cookie string
        cookie_parts = []
        for cookie in self._cookies:
            if hasattr(cookie, 'to_name_val_str'):
                cookie_parts.append(cookie.to_name_val_str())
            elif hasattr(cookie, '_name') and hasattr(cookie, '_val'):
                cookie_parts.append(f"{cookie._name}={cookie._val}")
        if cookie_parts:
            self._req_headers["Cookie"] = "; ".join(cookie_parts)
        else:
            if "Cookie" in self._req_headers:
                del self._req_headers["Cookie"]

    def follow_redirects(self, val=None):
        """Get or set whether to follow redirects."""
        if val is None:
            return self._follow_redirects
        self._follow_redirects = val
        return self

    def socket_config(self, val=None):
        """Get or set the socket configuration (for timeouts)."""
        if val is None:
            return self._socket_config
        self._socket_config = val
        return self

    # =========================================================================
    # Request Execution
    # =========================================================================

    def write_req(self):
        """Prepare to write the request.

        In Python's urllib, we buffer the request and send it
        all at once in read_res(). This method prepares the buffer.
        """
        # Create buffer for request body
        self._req_body = Buf.make()
        self._req_out_stream = self._req_body.out()
        return self

    def req_out(self):
        """Get the output stream for writing the request body.

        Returns an OutStream that writes to an internal buffer.
        The actual HTTP request is sent when read_res() is called.
        """
        if self._req_out_stream is None:
            raise IOError("Call write_req() before req_out()")
        return self._req_out_stream

    def read_res(self):
        """Execute the HTTP request and read the response.

        This is where the actual HTTP call happens. The request body
        (if any) is sent, and the response is read.
        """
        # Get URI as string
        uri_str = self._get_uri_string()

        # Prepare request data
        data = None
        if self._req_body is not None and self._req_body.size() > 0:
            self._req_body.flip()
            data = self._req_body.read_all_buf().to_py()

        # Prepare headers as dict
        headers = dict(self._req_headers)

        # Get timeout from socket config
        timeout = self._get_timeout()

        # Check if HTTPS
        use_https = uri_str.startswith('https://')

        # Build the opener with appropriate handlers
        opener = self._build_opener(use_https=use_https)

        # Create the request
        req = urllib.request.Request(
            uri_str,
            data=data,
            headers=headers,
            method=self._req_method
        )

        # Make the request
        try:
            self._response = opener.open(req, timeout=timeout[0])

            # Store response info
            self._res_code = self._response.status
            self._res_phrase = self._response.reason or ""

            # Read and potentially decompress content
            self._response_content = self._response.read()
            content_encoding = self._response.headers.get('Content-Encoding', '')
            if content_encoding == 'gzip':
                try:
                    self._response_content = gzip.decompress(self._response_content)
                except Exception:
                    pass  # Keep original content if decompression fails

            # Convert response headers to Fantom Map
            self._res_headers = Map.from_literal([], [], "sys::Str", "sys::Str")
            self._res_headers.case_insensitive = True
            for key in self._response.headers.keys():
                self._res_headers[key] = self._response.headers[key]

            # Update req_uri to final URL after redirects
            if self._follow_redirects and self._response.url:
                from fan.sys.Uri import Uri
                self._req_uri = Uri.from_str(self._response.url)

            # Set HTTP version (urllib doesn't expose this directly, default to 1.1)
            from fan.sys.Version import Version
            self._res_version = Version.from_str("1.1")

            # Handle cookies from response
            self._update_cookies_from_response()

            # Prepare response input stream
            self._res_in_stream = None  # Will be created on demand

        except urllib.error.HTTPError as e:
            # HTTPError is a valid response with status code >= 400
            self._response = e
            self._res_code = e.code
            self._res_phrase = e.reason or ""

            # Read content from error response
            try:
                self._response_content = e.read()
                content_encoding = e.headers.get('Content-Encoding', '')
                if content_encoding == 'gzip':
                    try:
                        self._response_content = gzip.decompress(self._response_content)
                    except Exception:
                        pass
            except Exception:
                self._response_content = b''

            # Convert response headers to Fantom Map
            self._res_headers = Map.from_literal([], [], "sys::Str", "sys::Str")
            self._res_headers.case_insensitive = True
            for key in e.headers.keys():
                self._res_headers[key] = e.headers[key]

            from fan.sys.Version import Version
            self._res_version = Version.from_str("1.1")

            self._res_in_stream = None

        except urllib.error.URLError as e:
            raise IOError(f"HTTP request failed: {e.reason}")
        except Exception as e:
            raise IOError(f"HTTP request failed: {e}")

        return self

    def _get_uri_string(self):
        """Convert the request URI to a string."""
        uri = self._req_uri
        if uri is None:
            raise ValueError("reqUri is not set")
        if hasattr(uri, 'to_str'):
            return uri.to_str()
        return str(uri)

    def _get_timeout(self):
        """Get timeout tuple (connect, read) from socket config."""
        if self._socket_config is not None:
            if hasattr(self._socket_config, 'get_timeout_seconds'):
                return self._socket_config.get_timeout_seconds()
        return (60, 60)  # Default 60 second timeout

    def _update_cookies_from_response(self):
        """Update cookies from cookie jar after response."""
        if self._cookie_jar is None:
            return
        # Convert cookiejar cookies to our Cookie objects using Cookie.make()
        from fan.web.Cookie import Cookie as FanCookie
        new_cookies = []
        for cookie in self._cookie_jar:
            # Use Cookie.make() with it-block to set domain/path
            def make_it_block(c, domain=cookie.domain, path=cookie.path):
                if domain:
                    c._domain = domain
                if path:
                    c._path = path
            c = FanCookie.make(cookie.name, cookie.value, make_it_block)
            new_cookies.append(c)
        if new_cookies:
            self._cookies = new_cookies

    # =========================================================================
    # Response Access
    # =========================================================================

    def res_code(self):
        """Get the HTTP status code."""
        return self._res_code

    def res_phrase(self):
        """Get the HTTP status reason phrase."""
        return self._res_phrase

    def res_version(self):
        """Get the HTTP response version as a Version object.

        Returns:
            Version representing the HTTP version (e.g., Version("1.1"))
        """
        from fan.sys.Version import Version
        if self._res_version is not None:
            return self._res_version
        # Default to HTTP/1.1
        return Version.from_str("1.1")

    def res_headers(self):
        """Get the response headers (case-insensitive dict)."""
        if not hasattr(self, '_res_headers_wrapper'):
            self._res_headers_wrapper = HeadersWrapper(self._res_headers)
        return self._res_headers_wrapper

    def res_header(self, key, checked=True):
        """Get a response header by key."""
        val = self._res_headers.get(key)
        if val is not None or not checked:
            return val
        raise Exception(f"Missing HTTP header '{key}'")

    def res_in(self):
        """Get the input stream for reading the response body."""
        if self._response is None and self._response_content is None:
            raise IOError(f"No input stream for response {self._res_code}")

        if self._res_in_stream is None:
            # Create an InStream wrapping the response content
            content = self._response_content if self._response_content is not None else b''
            self._res_in_stream = Buf.from_bytes(content).in_()

        return self._res_in_stream

    def res_str(self):
        """Read the entire response as a string."""
        return self.res_in().read_all_str()

    def res_buf(self):
        """Read the entire response as a Buf."""
        return self.res_in().read_all_buf()

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_str(self):
        """Make a GET request and return the response as a string."""
        try:
            return self.get_in().read_all_str()
        finally:
            self.close()

    def get_buf(self):
        """Make a GET request and return the response as a Buf."""
        try:
            return self.get_in().read_all_buf()
        finally:
            self.close()

    def get_in(self):
        """Make a GET request and return the response input stream."""
        self._req_method = "GET"
        self.write_req()
        self.read_res()
        if self._res_code != 200:
            raise IOError(f"Bad HTTP response {self._res_code} {self._res_phrase}")
        return self.res_in()

    def post_str(self, content):
        """POST a string and read the response."""
        return self.write_str("POST", content).read_res()

    def post_buf(self, buf):
        """POST a buffer and read the response."""
        return self.write_buf("POST", buf).read_res()

    def write_str(self, method, content):
        """Write a string as the request body."""
        self._req_method = method
        if "Content-Type" not in self._req_headers:
            self._req_headers["Content-Type"] = "text/plain; charset=utf-8"
        body = content.encode('utf-8') if isinstance(content, str) else content
        self._req_headers["Content-Length"] = str(len(body))
        self.write_req()
        self.req_out().write_buf(Buf.from_bytes(body)).close()
        return self

    def write_buf(self, method, content):
        """Write a buffer as the request body."""
        self._req_method = method
        if "Content-Type" not in self._req_headers:
            self._req_headers["Content-Type"] = "application/octet-stream"
        if hasattr(content, 'size'):
            self._req_headers["Content-Length"] = str(content.size())
        self.write_req()
        if hasattr(content, 'seek'):
            content.seek(0)
        self.req_out().write_buf(content).close()
        return self

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def is_connected(self):
        """Check if currently connected."""
        return self._response is not None

    def close(self):
        """Close the client and release resources."""
        if self._response is not None:
            try:
                self._response.close()
            except Exception:
                pass
            self._response = None
        self._response_content = None
        self._req_out_stream = None
        self._res_in_stream = None
        return self

    def to_str(self):
        """String representation."""
        uri = self._get_uri_string() if self._req_uri else "null"
        return f"WebClient({uri})"


class HeadersWrapper:
    """Wrapper for headers dict that supports both Fantom Map operations
    and direct Python dict access.

    This allows code like:
        c.req_headers()["Content-Type"] = "application/json"
        c.req_headers().each(lambda v, k: print(f"{k}: {v}"))
    """

    def __init__(self, headers):
        self._headers = headers

    def __getitem__(self, key):
        return self._headers.get(key)

    def __setitem__(self, key, value):
        self._headers[key] = value

    def __delitem__(self, key):
        if key in self._headers:
            del self._headers[key]

    def __contains__(self, key):
        return key in self._headers

    def __iter__(self):
        return iter(self._headers)

    def get(self, key, default=None):
        return self._headers.get(key, default)

    def set_all(self, other):
        """Set all headers from another dict/Map."""
        if hasattr(other, '_headers'):
            other = other._headers
        if hasattr(other, 'items'):
            for k, v in other.items():
                self._headers[k] = v
        elif hasattr(other, 'each'):
            other.each(lambda v, k: self._headers.__setitem__(k, v))
        return self

    def contains_key(self, key):
        return key in self._headers

    def remove(self, key):
        if key in self._headers:
            del self._headers[key]
        return self

    def each(self, func):
        """Iterate over headers calling func(value, key)."""
        for k, v in self._headers.items():
            func(v, k)
        return self

    def to_str(self):
        return str(dict(self._headers))

    @property
    def case_insensitive(self):
        """For Fantom Map compatibility."""
        return True
