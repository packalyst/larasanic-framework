"""
HttpRequest Facade
Provides easy access to request context variables
"""
from larasanic.support.facades.facade import Facade, FacadeMeta
from typing import Any, Optional, Dict
from larasanic.support import Config


class HttpRequestMeta(FacadeMeta):
    """Custom metaclass for HttpRequest to handle attribute proxying"""

    def __getattr__(cls, name: str) -> Any:
        """
        Override to proxy to Sanic request instead of request.ctx
        """
        # First check if it's a method on HttpRequest itself
        if name in dir(cls):
            return object.__getattribute__(cls, name)

        # Otherwise, proxy to the underlying Sanic request
        request = cls.get_current_request()
        if request and hasattr(request, name):
            return getattr(request, name)

        # Fall back to parent behavior for facade root (request.ctx)
        return super().__getattr__(name)


class HttpRequest(Facade, metaclass=HttpRequestMeta):
    """
    HttpRequest Facade

    Provides easy access to request context variables (.ctx).

    Example:
        # Set context variable
        HttpRequest.set('user_id', 123)
        HttpRequest.set('is_admin', True)

        # Get context variable
        user_id = HttpRequest.get('user_id')
        is_admin = HttpRequest.get('is_admin', default=False)

        # Append to context list
        HttpRequest.append('breadcrumbs', {'name': 'Home', 'url': '/'})
        HttpRequest.append('breadcrumbs', {'name': 'Products', 'url': '/products'})

        # Get all context
        ctx_data = HttpRequest.all()

        # Check if key exists
        if HttpRequest.has('user_id'):
            print("User is authenticated")

        # Get current user (if set by auth middleware)
        user = HttpRequest.user()

        # Get current request
        request = HttpRequest.request()
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        """Not used - HttpRequest works directly with request"""
        return 'http_request'

    @classmethod
    def get_facade_root(cls):
        """Override - HttpRequest doesn't use container"""
        request = cls.get_current_request()
        if not request:
            raise RuntimeError(
                "No active request context. "
                "HttpRequest facade can only be used within request handlers."
            )
        return request.ctx

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Get a context variable

        Args:
            key: Context variable name
            default: Default value if not found

        Returns:
            Context variable value or default
        """
        ctx = cls.get_facade_root()
        return getattr(ctx, key, default)

    @classmethod
    def set(cls, key: str, value: Any):
        """
        Set a context variable

        Args:
            key: Context variable name
            value: Value to set
        """
        ctx = cls.get_facade_root()
        setattr(ctx, key, value)

    @classmethod
    def append(cls, key: str, value: Any):
        """
        Append a value to a context list variable

        If the key doesn't exist, creates a new list with the value.
        If the key exists but is not a list, raises a TypeError.

        Args:
            key: Context variable name (must be a list)
            value: Value to append

        Raises:
            TypeError: If the existing value is not a list

        Example:
            # Append to breadcrumbs
            HttpRequest.append('breadcrumbs', {'name': 'Home', 'url': '/'})
            HttpRequest.append('breadcrumbs', {'name': 'Products', 'url': '/products'})

            # Append to errors
            HttpRequest.append('errors', 'Validation failed')
        """
        ctx = cls.get_facade_root()

        if not hasattr(ctx, key):
            # Create new list if key doesn't exist
            setattr(ctx, key, [value])
        else:
            # Get existing value
            existing = getattr(ctx, key)

            # Check if it's a list
            if not isinstance(existing, list):
                raise TypeError(
                    f"Cannot append to '{key}': existing value is {type(existing).__name__}, not list"
                )

            # Append to list
            existing.append(value)

    @classmethod
    def has(cls, key: str) -> bool:
        """
        Check if context variable exists

        Args:
            key: Context variable name

        Returns:
            True if exists
        """
        ctx = cls.get_facade_root()
        return hasattr(ctx, key)

    @classmethod
    def all(cls) -> dict:
        """
        Get all context variables as dictionary

        Returns:
            Dictionary of all context variables
        """
        ctx = cls.get_facade_root()
        return {key: getattr(ctx, key) for key in dir(ctx) if not key.startswith('_')}

    @classmethod
    def get_user(cls) -> Optional[Any]:
        return cls.get('user_request', None)
    
    @classmethod
    def set_user(cls, value: Any):
        return cls.set('user_request', value)

    @classmethod
    def get_session(cls) -> Optional[Any]:
        return cls.get('session_request', None)

    @classmethod
    def set_session(cls, value: Any):
        return cls.set('session_request', value)
    
    @classmethod
    def request(cls):
        """
        Get the current request object

        Returns:
            Sanic request object
        """
        return cls.get_current_request()

    # ===================================================================
    # Request Analysis Helper Properties
    # ===================================================================

    @classmethod
    def _request_analysis(cls) -> Dict[str, Any]:
        return cls.get('_request_analysis', {})

    @classmethod
    def is_ajax(cls) -> bool:
        """Check if the request is an AJAX/API request """
        return cls._request_analysis().get('is_ajax', False)

    @classmethod
    def is_json_request(cls) -> bool:
        """Check if the request expects JSON response """
        return cls._request_analysis().get('is_json_request', False)

    @classmethod
    def wants_json(cls) -> bool:
        """Check if the client prefers JSON response """
        return cls._request_analysis().get('wants_json', False)

    @classmethod
    def wants_html(cls) -> bool:
        """Check if the client prefers HTML response """
        return cls._request_analysis().get('wants_html', False)

    @classmethod
    def request_type(cls) -> str:
        """Get the type of request """
        return cls._request_analysis().get('request_type', 'unknown')

    @classmethod
    def preferred_response(cls) -> str:
        """Get the preferred response format """
        return cls._request_analysis().get('preferred_response', 'html')

    @classmethod
    def content_type(cls) -> str:
        """Get the content type being sent in the request """
        return cls._request_analysis().get('content_type', 'none')

    @classmethod
    def client_ip(cls) -> str:
        """Get client IP address """
        return cls._request_analysis().get('client_ip', 'unknown')

    @classmethod
    def bearer_token(cls) -> Optional[str]:
        return cls._request_analysis().get('bearer_token')

    @classmethod
    def user_agent(cls) -> str:
        """Get user agent string """
        return cls._request_analysis().get('user_agent', 'Unknown')
    
    @classmethod
    def has_spa_header(cls) -> str:
        """Get user agent string """
        spa_header_name = Config.get('security.SPA_REQUEST_HEADER_NAME', 'X-SPA-Request')
        return bool(cls.get_header(spa_header_name))

    @classmethod
    def referer(cls) -> Optional[str]:
        """Get referer URL """
        return cls._request_analysis().get('referer')

    @classmethod
    def scheme(cls) -> str:
        """Get request scheme (http or https)"""
        request = cls.get_current_request()
        return request.scheme if request else 'http'

    @classmethod
    def host(cls) -> str:
        """Get request host (domain:port)"""
        request = cls.get_current_request()
        return request.host if request else ''
    
    @classmethod
    def method(cls) -> str:
        """Get request host (domain:port)"""
        request = cls.get_current_request()
        return request.method if request else ''

    @classmethod
    def path(cls) -> str:
        """Get request path"""
        request = cls.get_current_request()
        return request.path if request else '/'

    @classmethod
    def path_with_query(cls) -> str:
        request = cls.get_current_request()
        if not request:
            return '/'
        path_with_query = request.path
        if request.query_string:
            path_with_query += f"?{request.query_string}"
        return path_with_query
    
    @classmethod
    def query_string(cls) -> str:
        """Get query string (without ?)"""
        request = cls.get_current_request()
        return request.query_string if request else ''

    @classmethod
    def is_mobile(cls) -> bool:
        """Check if the request is from a mobile device """
        return cls._request_analysis().get('user_agent_type') == 'mobile'

    @classmethod
    def is_bot(cls) -> bool:
        """Check if the request is from a bot/crawler """
        return cls._request_analysis().get('user_agent_type') == 'bot'

    @classmethod
    def should_return_partial(cls) -> bool:
        """Determine if a partial HTML response should be returned (for AJAX)"""

        return cls.request_type() == 'ajax' and cls.preferred_response() in ['html', 'text']

    @classmethod
    def get_best_response_format(cls, available_formats: list = None) -> str:
        """
            Determine the best response format based on request and available formats
        """
        if available_formats is None:
            available_formats = ['json', 'html', 'xml', 'text']

        preferred = cls.preferred_response()

        # If preferred format is available, use it
        if preferred in available_formats:
            return preferred

        # Fallback logic
        if 'html' in available_formats:
            return 'html'
        elif 'json' in available_formats:
            return 'json'
        elif 'text' in available_formats:
            return 'text'

        return 'html'
    

    @classmethod
    def path_starts_with(cls, prefix: str) -> bool:
        """Check if the current request path starts with a prefix

        Args:
            prefix: The path prefix to check

        Returns:
            True if path starts with prefix, False otherwise

        Example:
            if HttpRequest.path_starts_with('/api/'):
                # Handle API request
        """
        request = cls.get_current_request()
        if not request:
            return False
        return request.path.startswith(prefix)

    @classmethod
    def url(cls) -> str:
        request = cls.get_current_request()
        return request.url if request else '/'

    # ===================================================================
    # Direct Sanic Request Attributes
    # Note: Handled by HttpRequestMeta.__getattr__ to proxy to Sanic request
    # ===================================================================

    # ===================================================================
    # HTTP FORM
    # ===================================================================

    @classmethod
    def input(cls, name: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Get input from request (checks args, form, json in order)
        Laravel-style input retrieval

        Args:
            name: Input name
            default: Default value if not found

        Returns:
            Input value or default

        Example:
            page = HttpRequest.input('page', 1)
            email = HttpRequest.input('email')
        """
        request = cls.get_current_request()

        # Check query parameters first
        if request.args and name in request.args:
            return request.args.get(name, default)

        # Check form data
        if request.form and name in request.form:
            return request.form.get(name, default)

        # Check JSON body
        if request.json and isinstance(request.json, dict) and name in request.json:
            return request.json.get(name, default)

        return default

    @classmethod
    def input_list(cls, name: str, default: Optional[list] = None) -> list:
        """
        Get list input from request (for multiple values)

        Args:
            name: Input name
            default: Default value if not found

        Returns:
            List of values or default

        Example:
            statuses = HttpRequest.input_list('status')  # ['active', 'pending']
            tags = HttpRequest.input_list('tags', [])
        """
        request = cls.get_current_request()

        # Check query parameters (supports multiple values)
        if request.args and name in request.args:
            return request.args.getlist(name)

        # Check form data (supports multiple values)
        if request.form and name in request.form:
            return request.form.getlist(name)

        # Check JSON body (should be array)
        if request.json and isinstance(request.json, dict) and name in request.json:
            value = request.json.get(name)
            if isinstance(value, list):
                return value
            return [value]

        return default if default is not None else []
    

    # ===================================================================
    # HTTP Header Access Methods
    # ===================================================================

    @classmethod
    def get_header(cls, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a request header value (case-insensitive)"""
        return cls.get_current_request().headers.get(name, default)

    @classmethod
    def get_headers(cls):
        """Get all request headers  """
        return cls.get_current_request().headers.items()

    @classmethod
    def get_bearer_token(cls) -> Optional[str]:
        """Extract Bearer token from Authorization header"""
        auth_header = cls.get_header('Authorization', '')
        if auth_header.lower().startswith('bearer '):
            return auth_header[7:]
        return None

    # ===================================================================
    # Cookie Access Methods
    # ===================================================================

    @classmethod
    def get_cookie(cls, key: str, default: Any = None) -> Any:
        """Get cookie value

        Args:
            key: Cookie name
            default: Default value if cookie not found

        Returns:
            Cookie value or default

        Example:
            session_id = HttpRequest.get_cookie('session_id')
            theme = HttpRequest.get_cookie('theme', 'light')
        """
        request = cls.get_current_request()
        if not request:
            return default
        return request.cookies.get(key, default)

    @classmethod
    def has_cookie(cls, key: str) -> bool:
        """Check if cookie exists

        Args:
            key: Cookie name

        Returns:
            True if cookie exists, False otherwise

        Example:
            if HttpRequest.has_cookie('session_id'):
                # Session exists
        """
        request = cls.get_current_request()
        if not request:
            return False
        return key in request.cookies

    # ===================================================================
    # Internal Request Analysis Methods
    # ===================================================================

    @classmethod
    def _handle_spa_request(cls) -> Dict[str, Any]:
        """Analyze request and return detailed information"""
        

        request = cls.get_current_request()
        return_data = {
            'is_ajax': False,
            'is_json_request': False,
            'wants_json': False,
            'wants_html': False,
            'preferred_response': 'html',

            'content_type': cls._get_request_content_type(),
            'client_ip': cls._get_client_ip(),
            'bearer_token': cls.get_bearer_token(),
            'user_agent': cls.get_header('User-Agent', 'Unknown'),
            'referer': cls.get_header('Referer'),

            'has_json_accept': False,
            'has_json_content': False,

            'request_type': 'browser',
        }

        # Skip analysis for static files
        skip_paths = ['/static/', '/favicon.ico', '/robots.txt', '/sitemap.xml', '/health']
        if any(cls.path_starts_with(path) for path in skip_paths):
            return_data.update({'request_type': 'static'})
            return return_data

        # Check for XMLHttpRequest
        if cls.get_header('X-Requested-With', '').lower() == 'xmlhttprequest':
            return_data['request_type'] = 'ajax'
            return_data['is_ajax'] = True

        return_data['user_agent_type'] = cls._get_user_agent_type()
        return_data['preferred_response'] = cls._get_request_response_type()

        is_json_request = return_data['request_type'] == 'json_api' or return_data['preferred_response'] == 'json'
        wants_json = return_data['preferred_response'] == 'json' or return_data['content_type'] == 'json'
        wants_html = return_data['preferred_response'] == 'html'
        
        return_data.update({
            'is_json_request': is_json_request,
            'wants_json': wants_json,
            'wants_html': wants_html,
        })
        
        return return_data

    @classmethod
    def _get_user_agent_type(cls) -> str:
        """Analyze User-Agent header to determine client type"""
        user_agent = cls.get_header('User-Agent', '').lower()
        if user_agent:
            if 'curl' in user_agent:
                return 'curl'
            elif 'postman' in user_agent or 'insomnia' in user_agent:
                return 'postman'
            elif 'bot' in user_agent or 'crawler' in user_agent:
                return 'bot'
            elif 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
                return 'mobile'
        return 'browser'

    @classmethod
    def _get_request_response_type(cls) -> str:
        """Parse Accept header to determine preferred response format"""
        accept_header = cls.get_header('Accept', '').lower()
        preferred_response = 'html'

        if accept_header:
            accepts = []
            for item in accept_header.split(','):
                parts = item.strip().split(';')
                mime_type = parts[0].strip()
                q_value = 1.0
                for part in parts[1:]:
                    if part.strip().startswith('q='):
                        try:
                            q_value = float(part.strip()[2:])
                        except ValueError:
                            q_value = 1.0
                accepts.append((mime_type, q_value))

            accepts.sort(key=lambda x: x[1], reverse=True)
            if accepts:
                top_mime = accepts[0][0]
                if 'application/json' in top_mime:
                    preferred_response = 'json'
                elif 'text/html' in top_mime:
                    preferred_response = 'html'
                elif 'application/xml' in top_mime or 'text/xml' in top_mime:
                    preferred_response = 'xml'
                elif 'text/plain' in top_mime:
                    preferred_response = 'text'
        return preferred_response

    @classmethod
    def _get_request_content_type(cls) -> str:
        """Analyze Content-Type header"""
        content_type_header = cls.get_header('Content-Type', '').lower()
        content_type = 'none'

        if content_type_header:
            if 'application/json' in content_type_header:
                content_type = 'json'
            elif 'application/x-www-form-urlencoded' in content_type_header:
                content_type = 'form'
            elif 'multipart/form-data' in content_type_header:
                content_type = 'multipart'
            elif 'text/' in content_type_header:
                content_type = 'text'
        return content_type

    @classmethod
    def _get_client_ip(cls) -> str:
        """Get client IP address from headers or direct connection"""
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = cls.get_header('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()

        # Check for real IP header
        real_ip = cls.get_header('X-Real-IP')
        if real_ip:
            return real_ip

        # Fallback to direct IP
        return cls.get_current_request().ip or 'unknown'
