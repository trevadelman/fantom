#
# web::WebClient - Python native implementation
#
# HTTP client using Python's requests library.
# This replaces the Fantom implementation which uses raw TcpSocket.
#

import io
from fan.sys.Obj import Obj
from fan.sys.Buf import Buf
from fan.sys.Map import Map

# Try to import requests, provide helpful error if not installed
try:
    import requests
except ImportError:
    raise ImportError(
        "The 'requests' library is required for HTTP client functionality.\n"
        "Install it with: pip install requests"
    )


class WebClient(Obj):
    """HTTP client using Python's requests library.

    This is a Python-native implementation that wraps the requests library
    to provide the Fantom WebClient API. The requests library handles:
    - SSL/TLS
    - Chunked transfer encoding
    - Cookies
    - Redirects
    - Connection pooling

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
        self._response = None  # requests.Response object

        # Configuration
        self._cookies = []
        self._follow_redirects = True
        self._socket_config = None
        self._session = requests.Session()

        # Stream wrappers
        self._req_out_stream = None
        self._res_in_stream = None

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
        """
        if val is None:
            return self._cookies
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

        In Python's requests library, we buffer the request and send it
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

        # Prepare cookies
        cookies = {}
        for cookie in self._cookies:
            if hasattr(cookie, '_name') and hasattr(cookie, '_val'):
                cookies[cookie._name] = cookie._val

        # Make the request
        try:
            self._response = self._session.request(
                method=self._req_method,
                url=uri_str,
                headers=headers,
                data=data,
                cookies=cookies if cookies else None,
                allow_redirects=self._follow_redirects,
                timeout=timeout,
            )

            # Store response info
            self._res_code = self._response.status_code
            self._res_phrase = self._response.reason or ""

            # Convert response headers to Fantom Map
            self._res_headers = Map.from_literal([], [], "sys::Str", "sys::Str")
            self._res_headers.case_insensitive = True
            for key, value in self._response.headers.items():
                self._res_headers[key] = value

            # Update req_uri to final URL after redirects
            if self._follow_redirects and self._response.url:
                from fan.sys.Uri import Uri
                self._req_uri = Uri.from_str(self._response.url)

            # Set HTTP version from response
            from fan.sys.Version import Version
            raw_version = getattr(self._response.raw, 'version', None)
            if raw_version == 10:
                self._res_version = Version.from_str("1.0")
            elif raw_version == 11:
                self._res_version = Version.from_str("1.1")
            elif raw_version == 20:
                self._res_version = Version.from_str("2.0")
            else:
                self._res_version = Version.from_str("1.1")  # Default

            # Handle cookies from response
            self._update_cookies_from_response()

            # Prepare response input stream
            self._res_in_stream = None  # Will be created on demand

        except requests.exceptions.RequestException as e:
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
        """Update cookies from Set-Cookie response headers."""
        if self._response is None:
            return
        # Convert requests cookies to our Cookie objects using Cookie.make()
        from fan.web.Cookie import Cookie as FanCookie
        new_cookies = []
        for cookie in self._response.cookies:
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
        # requests library stores raw HTTP version
        if self._response is not None:
            # requests uses raw.version which is 10 for HTTP/1.0, 11 for HTTP/1.1
            raw_version = getattr(self._response.raw, 'version', None)
            if raw_version == 10:
                return Version.from_str("1.0")
            elif raw_version == 11:
                return Version.from_str("1.1")
            elif raw_version == 20:
                return Version.from_str("2.0")
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
        if self._response is None:
            raise IOError(f"No input stream for response {self._res_code}")

        if self._res_in_stream is None:
            # Create an InStream wrapping the response content
            content = self._response.content
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
            self._response.close()
            self._response = None
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
