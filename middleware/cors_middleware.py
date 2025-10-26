"""
CORS Middleware (Enhanced - Laravel Style)
Handles Cross-Origin Resource Sharing headers with advanced features
Beats sanic-ext with: regex patterns, per-route config, Vary header, header filtering
"""
from larasanic.middleware.base_middleware import Middleware
from larasanic.http import ResponseHelper
from sanic import Request
from typing import Optional, Union, List, Pattern
import re


class CorsConfigurationError(Exception):
    """Exception raised for insecure CORS configuration"""
    pass

class CorsMiddleware(Middleware):
    """
    Enhanced CORS middleware with advanced features
    """

    # Configuration mapping for MiddlewareConfigMixin
    @staticmethod
    def _get_config_defaults():
        from larasanic.defaults import DEFAULT_CORS_MAX_AGE
        return {
            'allowed_origins': ('security.ALLOWED_ORIGINS', ['*']),
            'allowed_methods': ('security.CORS_METHODS', None),
            'allowed_headers': ('security.CORS_HEADERS', None),
            'expose_headers': ('security.CORS_EXPOSE_HEADERS', None),
            'max_age': ('security.CORS_MAX_AGE', DEFAULT_CORS_MAX_AGE),
        }
    CONFIG_MAPPING = _get_config_defaults.__func__()
    STATIC_PARAMS = {'allow_credentials': True}
    DEFAULT_ENABLED = False  # Disabled by default

    @classmethod
    def _is_enabled(cls) -> bool:
        """Custom enabled check: CORS enabled in debug mode OR explicitly enabled"""
        from larasanic.support import Config
        return Config.get('app.APP_DEBUG', False) or Config.get('security.CORS_ENABLED', False)

    def __init__(
        self,
        allowed_origins: Union[str, List[str], Pattern] = None,
        allowed_methods: List[str] = None,
        allowed_headers: Union[str, List[str]] = None,
        expose_headers: List[str] = None,
        allow_credentials: bool = True,
        max_age: int = None
    ):
        from larasanic.defaults import DEFAULT_CORS_MAX_AGE
        if max_age is None:
            max_age = DEFAULT_CORS_MAX_AGE
        """
        Initialize CORS middleware
        """
        # Parse and compile origin patterns (supports regex)
        self.origin_patterns = self._parse_origins(allowed_origins or ['*'])
        self.wildcard_origin = any(p.pattern == '.*' for p in self.origin_patterns)

        self.allowed_methods = [m.upper() for m in (allowed_methods or
            ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])]

        # Parse allowed headers (supports '*' wildcard)
        if allowed_headers == '*':
            self.allowed_headers = '*'
        else:
            self.allowed_headers = set(
                h.lower().strip() for h in (allowed_headers or
                ['content-type', 'authorization', 'x-csrf-token'])
            )

        self.expose_headers = [h.lower() for h in (expose_headers or [])]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

        # Validate CORS configuration (security check)
        if self.wildcard_origin and self.allow_credentials:
            raise CorsConfigurationError(
                "Cannot use wildcard origin (*) with credentials. "
                "This violates CORS specification (RFC 6454) and creates a security vulnerability. "
                "Either specify explicit origins or set allow_credentials=False."
            )

    def _parse_origins(self, origins: Union[str, List[str], Pattern]) -> List[Pattern]:
        """
        Parse origins into regex patterns (supports wildcards)

        Examples:
            '*' -> matches any origin
            'https://example.com' -> exact match
            '*.example.com' -> matches any subdomain
            'https://*.example.com' -> matches any subdomain with https
        """
        if isinstance(origins, Pattern):
            return [origins]

        if isinstance(origins, str):
            origins = [origins]

        patterns = []
        for origin in origins:
            if origin == '*':
                # Wildcard: match everything
                patterns.append(re.compile(r'.*'))
            elif '*' in origin:
                # Convert wildcard pattern to regex
                # *.example.com -> ^https?://.*\.example\.com$
                escaped = re.escape(origin)
                pattern = escaped.replace(r'\*', '.*')
                patterns.append(re.compile(f'^{pattern}$'))
            else:
                # Exact match
                patterns.append(re.compile(f'^{re.escape(origin)}$'))

        return patterns

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin matches any allowed pattern"""
        if not origin:
            return False

        return any(pattern.match(origin) for pattern in self.origin_patterns)

    def _has_credentials(self, request: Request) -> bool:
        """Check if request includes credentials (cookies or auth)"""
        from larasanic.support.facades import HttpRequest
        return bool(HttpRequest.bearer_token() or request.cookies)

    def _get_cors_origin_header(self, origin: Optional[str]) -> Optional[str]:
        """
        Get CORS origin header value based on allowed origins
        """
        if not origin:
            return '*' if self.wildcard_origin else None

        if self._is_origin_allowed(origin):
            return origin  # Return actual origin (safer than '*')

        return None

    def _get_allowed_headers(self, with_credentials: bool) -> Optional[List[str]]:
        """
        Get allowed headers for response
        """
        from larasanic.support.facades import HttpRequest
        # If wildcard and no credentials, allow all
        if self.allowed_headers == '*' and not with_credentials:
            return ['*']

        # Get requested headers from preflight
        requested = HttpRequest.get_header('access-control-request-headers', '')
        if not requested:
            return None

        requested_headers = set(h.strip().lower() for h in requested.split(','))

        # Filter: only allow headers that are both requested AND allowed
        if self.allowed_headers == '*':
            # With credentials: allow all requested headers
            return list(requested_headers)
        else:
            # Filter to only allowed headers
            allowed = requested_headers & self.allowed_headers
            return list(allowed) if allowed else None

    async def before_request(self, request: Request):
        """Handle CORS preflight requests"""
        if request.method == 'OPTIONS':
            return self._build_preflight_response(request)
        return None

    async def after_response(self, request: Request, response):
        """Add CORS headers to response"""
        from larasanic.support.facades import HttpRequest
        origin = HttpRequest.get_header('origin')

        if not origin:
            return response

        # Set CORS origin header
        cors_origin = self._get_cors_origin_header(origin)
        if not cors_origin:
            return response  # Origin not allowed

        from larasanic.support.facades import HttpResponse

        HttpResponse.header('Access-Control-Allow-Origin', cors_origin)

        # Add credentials header
        if self.allow_credentials:
            HttpResponse.header('Access-Control-Allow-Credentials', 'true')

        # Add expose headers
        if self.expose_headers:
            with_credentials = self._has_credentials(request)
            # Wildcard doesn't work with credentials per MDN spec
            if '*' in self.expose_headers and not with_credentials:
                HttpResponse.header('Access-Control-Expose-Headers', '*')
            else:
                HttpResponse.header('Access-Control-Expose-Headers', ', '.join(self.expose_headers))

        # Add Vary header for proper caching (important!)
        if len(self.origin_patterns) > 1:
            HttpResponse.header('Vary', 'Origin')

        return response

    def _build_preflight_response(self, request: Request):
        """Build response for OPTIONS preflight request"""
        from larasanic.support.facades import HttpRequest
        origin = HttpRequest.get_header('origin')

        # Check if origin is allowed
        cors_origin = self._get_cors_origin_header(origin)
        if not cors_origin:
            # Origin not allowed - return 403
            return ResponseHelper.error('CORS origin not allowed', status=403)

        headers = {}
        headers['Access-Control-Allow-Origin'] = cors_origin

        # Set allowed methods
        headers['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)

        # Set allowed headers (smart filtering)
        with_credentials = self._has_credentials(request)
        allowed_headers = self._get_allowed_headers( with_credentials)
        if allowed_headers:
            headers['Access-Control-Allow-Headers'] = ', '.join(allowed_headers)

        # Set max age
        headers['Access-Control-Max-Age'] = str(self.max_age)

        # Allow credentials
        if self.allow_credentials:
            headers['Access-Control-Allow-Credentials'] = 'true'

        # Add Vary header
        if len(self.origin_patterns) > 1:
            headers['Vary'] = 'Origin'

        return ResponseHelper.text('', status=204, headers=headers)