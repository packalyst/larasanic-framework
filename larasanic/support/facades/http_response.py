"""
HttpResponse Facade
Collects response data during request processing and builds the final response
"""
from larasanic.support.facades.facade import Facade
from typing import Any, Optional, Dict, Union
from sanic.response import HTTPResponse, html, json, text, redirect, raw
from sanic.cookies import Cookie


class ResponseBuilder:
    """
    Fluent response builder for method chaining (Laravel-style)

    Example:
        return response({'user': 'John'}) \\
            .header('X-Custom', 'value') \\
            .cookie('session', 'abc123') \\
            .status(200)
    """

    def __init__(self, content: Any = None):
        self._content = content
        self._headers = {}
        self._cookies = {}
        self._status = 200
        self._type = None
        self._meta = {}  # Store metadata for structured responses

    def __await__(self):
        """
        Make ResponseBuilder awaitable

        Allows: response = await response(data)
        This calls build() and returns HTTPResponse
        """
        import inspect
        async def _build():
            result = self.build()
            # If build() returns a coroutine (ViewResponseBuilder), await it
            if inspect.iscoroutine(result):
                return await result
            return result
        return _build().__await__()

    def header(self, key: str, value: str) -> 'ResponseBuilder':
        """Add a header (chainable)"""
        self._headers[key] = value
        return self

    def headers(self, headers: Dict[str, str]) -> 'ResponseBuilder':
        """Add multiple headers (chainable)"""
        self._headers.update(headers)
        return self

    def cookie(
        self,
        key: str,
        value: str,
        max_age: Optional[int] = None,
        expires: Optional[int] = None,
        path: str = '/',
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = True,
        samesite: Optional[str] = 'Lax',
        partitioned: bool = False,
        comment: Optional[str] = None,
        host_prefix: bool = False,
        secure_prefix: bool = False
    ) -> 'ResponseBuilder':
        """Add a cookie (chainable)"""
        self._cookies[key] = {
            'value': value,
            'max_age': max_age,
            'expires': expires,
            'path': path,
            'domain': domain,
            'secure': secure,
            'httponly': httponly,
            'samesite': samesite,
            'partitioned': partitioned,
            'comment': comment,
            'host_prefix': host_prefix,
            'secure_prefix': secure_prefix,
        }
        return self

    def with_cookie(self, *args, **kwargs) -> 'ResponseBuilder':
        """Alias for cookie() (Laravel style: withCookie)"""
        return self.cookie(*args, **kwargs)

    def without_cookie(self, key: str, path: str = '/', domain: Optional[str] = None) -> 'ResponseBuilder':
        """Delete a cookie (chainable)"""
        from datetime import datetime, timezone
        # Set expires to epoch time (January 1, 1970) to delete cookie
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return self.cookie(key, '', max_age=0, expires=epoch, path=path, domain=domain)

    def status(self, code: int) -> 'ResponseBuilder':
        """Set status code (chainable)"""
        self._status = code
        return self

    def type(self, response_type: str) -> 'ResponseBuilder':
        """Set response type explicitly (chainable)"""
        self._type = response_type
        return self

    def with_meta(self, key: str, value: Any) -> 'ResponseBuilder':
        """Add metadata for structured response (chainable)"""
        if value is not None:
            self._meta[key] = value
        return self

    def build(self) -> HTTPResponse:
        """
        Build the final Sanic HTTPResponse

        This method merges:
        1. Data from this ResponseBuilder (immediate response)
        2. Data from HttpResponse facade (queued during request lifecycle)

        Priority: ResponseBuilder data > HttpResponse facade data
        """
        from larasanic.support.facades import HttpRequest

        # Determine response type if not explicitly set
        response_type = self._type or self._determine_response_type()
        # Create the base response
        response = self._create_response(self._content, response_type)

        # STEP 1: Apply queued data from HttpResponse facade (middleware, etc.)
        try:
            # Get queued cookies from HttpResponse facade
            queued_cookies = HttpResponse.get_queued_cookies()
            for key, cookie_data in queued_cookies.items():
                # Only apply if not already set by ResponseBuilder
                if key not in self._cookies:
                    response.cookies.add_cookie(
                        key,
                        cookie_data['value'],
                        max_age=cookie_data['max_age'],
                        expires=cookie_data['expires'],
                        path=cookie_data['path'],
                        domain=cookie_data['domain'],
                        secure=cookie_data['secure'],
                        httponly=cookie_data['httponly'],
                        samesite=cookie_data['samesite'],
                        partitioned=cookie_data['partitioned'],
                        comment=cookie_data['comment'],
                        host_prefix=cookie_data['host_prefix'],
                        secure_prefix=cookie_data['secure_prefix'],
                    )

            # Get queued headers from HttpResponse facade
            queued_headers = HttpResponse.get_queued_headers()
            for key, value in queued_headers.items():
                # Only apply if not already set by ResponseBuilder
                if key not in self._headers:
                    response.headers[key] = value

        except RuntimeError:
            # No request context (e.g., testing) - skip queued data
            pass

        # STEP 2: Apply ResponseBuilder's own data (overrides queued data)
        for key, value in self._headers.items():
            response.headers[key] = value

        for key, cookie_data in self._cookies.items():
            response.cookies.add_cookie(
                key,
                cookie_data['value'],
                max_age=cookie_data['max_age'],
                expires=cookie_data['expires'],
                path=cookie_data['path'],
                domain=cookie_data['domain'],
                secure=cookie_data['secure'],
                httponly=cookie_data['httponly'],
                samesite=cookie_data['samesite'],
                partitioned=cookie_data['partitioned'],
                comment=cookie_data['comment'],
                host_prefix=cookie_data['host_prefix'],
                secure_prefix=cookie_data['secure_prefix'],
            )

        return response

    def _determine_response_type(self) -> str:
        """Auto-detect response type from content"""
        from larasanic.support.facades import HttpRequest
        content = self._content

        if content is None:
            return 'text'

        if HttpRequest.wants_json():
            return 'json'

        match content:
            case HTTPResponse():
                return 'raw'
            case dict() | list():
                return 'json'
            case str():
                content_lower = content.strip().lower()
                if content_lower.startswith('<!doctype') or content_lower.startswith('<html'):
                    return 'html'
                elif '<' in content and '>' in content:
                    return 'html'
                else:
                    return 'text'
            case bytes():
                return 'raw'
            case _:
                return 'json'

    def _create_response(self, content: Any, response_type: str) -> HTTPResponse:
        """Create Sanic response based on type with structured format"""
        # Already HTTPResponse - return as-is
        status_code = self._status
        if isinstance(content, HTTPResponse):
            if status_code != 200:
                content.status = status_code
            return content

        # Build structured response if metadata exists
        structured_content = self._build_structured_response(content, response_type)

        if response_type == 'json':
            return json(structured_content, status=status_code)

        elif response_type == 'html':
            # For HTML, if it's structured (has metadata), convert to JSON for API
            # Otherwise return raw HTML
            from larasanic.support.facades import HttpRequest
            if HttpRequest.wants_json() and self._meta:
                return json(structured_content, status=status_code)
            else:
                # Return raw HTML (content should be the HTML string)
                return html(str(content), status=status_code)

        elif response_type == 'text':
            return text(str(content) if content else '', status=status_code)

        elif response_type == 'redirect':
            return redirect(str(content), status=status_code if status_code != 200 else 302)

        elif response_type == 'raw':
            if isinstance(content, bytes):
                return raw(content, status=status_code)
            else:
                return text(str(content), status=status_code)

        else:
            return text(str(content) if content else '', status=status_code)

    def _build_structured_response(self, content: Any, response_type: str) -> Any:
        """Build structured response format if metadata exists"""
        # No metadata - return content as-is
        response_data = {}

        # Add success/error flag
        if 'success' in self._meta:
            response_data['success'] = self._meta['success']
        else:
            if self._status >= 400:
                response_data['success'] = 'false'
            else:
                response_data['success'] = 'true'
        # Add data or message based on success flag
        if self._meta.get('success', True) or self._status == 200:
            # Success response
            response_data['data'] = content
            if 'message' in self._meta and self._meta['message']:
                response_data['message'] = self._meta['message']
            if 'meta' in self._meta and self._meta['meta']:
                response_data['meta'] = self._meta['meta']
        else:
            # Error response
            response_data['message'] = content  # content is the error message
            if 'errors' in self._meta and self._meta['errors']:
                response_data['errors'] = self._meta['errors']
            if 'code' in self._meta and self._meta['code']:
                response_data['code'] = self._meta['code']

        return response_data


class ViewResponseBuilder(ResponseBuilder):
    """
    View response builder for template rendering with method chaining

    Extends ResponseBuilder to support deferred template rendering.
    Can be used with or without await:
    - return view('template') - Returns builder for chaining
    - await view('template') - Returns HTTPResponse immediately

    Example:
        return view('dashboard', {'user': 'John'}) \\
            .header('X-Custom', 'value') \\
            .cookie('session', 'abc123')
    """

    def __init__(self, template: str = None, context: Dict = None):
        """
        Initialize view response builder

        Args:
            template: Template name (e.g., 'pages.home')
            context: Template context variables
        """
        super().__init__(content=None)  # No content yet (will render later)
        self.template = template
        self.context = context or {}

    def with_context(self, key: str, value: Any) -> 'ViewResponseBuilder':
        """
        Add data to view context (chainable)

        Args:
            key: Context variable name
            value: Context variable value

        Returns:
            Self for chaining

        Example:
            return view('profile') \\
                .with_context('user', user) \\
                .with_context('posts', posts)
        """
        self.context[key] = value
        return self

    async def build(self) -> HTTPResponse:
        """
        Render view template and build HTTP response

        This method:
        1. Renders the template using ViewEngine
        2. Sets the rendered HTML as content
        3. Merges queued cookies/headers from HttpResponse facade
        4. Returns final HTTPResponse

        Returns:
            Sanic HTTPResponse object
        """
        # Import here to avoid circular dependency
        from larasanic.view.engine import ViewEngine

        # Render the template to HTML string
        engine = ViewEngine(self.template, self.context)
        html_content = await engine.render()

        # Set rendered HTML as content
        self._content = html_content

        # Use parent's build() to create HTTPResponse with merged cookies/headers
        return super().build()


class HttpResponse(Facade):
    """
    HttpResponse Facade

    Used by middlewares to queue cookies and headers that will be applied
    when ResponseBuilder.build() is called.

    Example:
        # In middleware after_response
        HttpResponse.cookie('session_id', 'abc123')
        HttpResponse.header('X-Custom-Header', 'value')

        # ResponseBuilder.build() will automatically merge these
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        """Not used - HttpResponse works directly with request context"""
        return 'http_response'

    @classmethod
    def get_facade_root(cls):
        """Override - HttpResponse doesn't use container"""
        request = cls.get_current_request()
        if not request:
            raise RuntimeError(
                "No active request context. "
                "HttpResponse facade can only be used within request handlers."
            )
        return request.ctx

    # ===================================================================
    # Cookie Management
    # ===================================================================

    @classmethod
    def add_cookie(
        cls,
        key: str,
        value: str,
        max_age: Optional[int] = None,
        expires: Optional[int] = None,
        path: str = '/',
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = True,
        samesite: Optional[str] = 'Lax',
        partitioned: bool = False,
        comment: Optional[str] = None,
        host_prefix: bool = False,
        secure_prefix: bool = False
    ):
        """
        Queue a cookie to be added to the response

        Args:
            key: Cookie name
            value: Cookie value
            max_age: Max age in seconds
            expires: Expiration timestamp
            path: Cookie path
            domain: Cookie domain
            secure: Secure flag (HTTPS only)
            httponly: HttpOnly flag (JavaScript cannot access)
            samesite: SameSite policy ('Lax', 'Strict', 'None')
            partitioned: Partitioned cookie (CHIPS)
            comment: Cookie comment
            host_prefix: Use __Host- prefix
            secure_prefix: Use __Secure- prefix

        Example:
            HttpResponse.cookie('session_id', 'abc123', httponly=True, secure=True)
        """
        ctx = cls.get_facade_root()

        # Initialize cookies dict if not exists
        if not hasattr(ctx, '_response_cookies'):
            ctx._response_cookies = {}

        # Store cookie data
        ctx._response_cookies[key] = {
            'value': value,
            'max_age': max_age,
            'expires': expires,
            'path': path,
            'domain': domain,
            'secure': secure,
            'httponly': httponly,
            'samesite': samesite,
            'partitioned': partitioned,
            'comment': comment,
            'host_prefix': host_prefix,
            'secure_prefix': secure_prefix,
        }

    @classmethod
    def forget_cookie(cls, key: str, path: str = '/', domain: Optional[str] = None):
        """
        Queue a cookie to be deleted (expires immediately)

        Args:
            key: Cookie name
            path: Cookie path (must match original)
            domain: Cookie domain (must match original)

        Example:
            HttpResponse.forget_cookie('session_id')
        """
        from datetime import datetime, timezone
        # Set expires to epoch time (January 1, 1970) to delete cookie
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        cls.cookie(key, '', max_age=0, expires=epoch, path=path, domain=domain)

    @classmethod
    def get_queued_cookies(cls) -> Dict[str, Dict]:
        """Get all queued cookies"""
        ctx = cls.get_facade_root()
        return getattr(ctx, '_response_cookies', {})

    # ===================================================================
    # Header Management
    # ===================================================================

    @classmethod
    def header(cls, key: str, value: str):
        """
        Queue a header to be added to the response

        Args:
            key: Header name
            value: Header value

        Example:
            HttpResponse.header('X-Custom-Header', 'value')
        """
        ctx = cls.get_facade_root()

        # Initialize headers dict if not exists
        if not hasattr(ctx, '_response_headers'):
            ctx._response_headers = {}

        ctx._response_headers[key] = value

    @classmethod
    def headers(cls, headers: Dict[str, str]):
        """
        Queue multiple headers at once

        Args:
            headers: Dictionary of headers

        Example:
            HttpResponse.headers({'X-RateLimit': '100', 'X-Token': 'xyz'})
        """
        for key, value in headers.items():
            cls.header(key, value)

    @classmethod
    def get_queued_headers(cls) -> Dict[str, str]:
        """Get all queued headers"""
        ctx = cls.get_facade_root()
        return getattr(ctx, '_response_headers', {})


