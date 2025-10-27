"""
CSRF Protection Middleware
Protects against Cross-Site Request Forgery attacks
"""
from larasanic.middleware.base_middleware import Middleware
from larasanic.support import Crypto,Config
from larasanic.http import ResponseHelper
from sanic import Request
from typing import Optional
from larasanic.support.facades import HttpRequest,Route

class CsrfMiddleware(Middleware):
    """CSRF token validation middleware"""

    # Configuration mapping for MiddlewareConfigMixin
    ENABLED_CONFIG_KEY = 'security.CSRF_ENABLED'
    CONFIG_MAPPING = {
        'secret_key': ('security.CSRF_SECRET', None),
    }
    DEFAULT_ENABLED = False

    def __init__(self, secret_key: str = None):
        from larasanic.defaults import DEFAULT_CSRF_TOKEN_LENGTH
        self.secret_key = secret_key or Crypto.generate_secret(DEFAULT_CSRF_TOKEN_LENGTH)
        # Load header/cookie names from config
        self.CSRF_HEADER_NAME = Config.get('security.CSRF_HEADER_NAME', 'X-CSRF-Token')
        self.CSRF_COOKIE_NAME = Config.get('security.CSRF_COOKIE_NAME', 'csrf_token')

    async def before_request(self, request: Request):
        """
        CSRF Protection with Token Rotation (Laravel-style)

        Flow:
        1. Validate OLD token/cookie (if POST/PUT/DELETE/PATCH)
        2. Generate NEW token/cookie for next request (rotation)
        3. Store new values for after_response to set cookie
        """
    
        # Step 1: Validate CSRF token on state-changing requests (using OLD values)
        if self._requires_csrf_protection(request):
            # Get CSRF token from multiple sources (Laravel-style)
            csrf_token = self._get_csrf_token_from_request(request)
            csrf_cookie = HttpRequest.get_cookie(self.CSRF_COOKIE_NAME)

            if not csrf_token or not csrf_cookie:
                return ResponseHelper.forbidden('CSRF token missing')

            if not self._verify_csrf_token(csrf_token, csrf_cookie):
                return ResponseHelper.forbidden('CSRF token invalid')

        # Step 2: Generate NEW token/cookie for next request (rotation)
        # Always rotate on every request for better security
        token, cookie = self.generate_csrf_token()
        HttpRequest.set('csrf_token',token)
        HttpRequest.set('csrf_cookie',cookie)

        return None

    async def after_response(self, request, response):
        """
        Set CSRF cookie in response (rotated token)

        IMPORTANT: Cookie settings for CSRF are different from session:
        - httponly=False: JavaScript MUST be able to read this for AJAX requests
        - samesite='Strict': CSRF protection requires strict same-site policy
        """
        from larasanic.support.facades import HttpResponse

        if HttpRequest.has('csrf_cookie'):
            HttpResponse.add_cookie(
                self.CSRF_COOKIE_NAME,
                HttpRequest.get('csrf_cookie'),
                httponly=False,  # JavaScript needs to read this for AJAX
                secure=Config.get('session.COOKIE_SECURE'),
                samesite='Strict',  # CSRF requires Strict (not Lax)
            )
        return response

    def _get_csrf_token_from_request(self, request: Request) -> Optional[str]:
        """
        Returns:
            CSRF token string or None
        """
        # Check header first (AJAX requests)
        token = HttpRequest.get_header(self.CSRF_HEADER_NAME)
        if token:
            return token
        # Check form data (regular form submissions)
        token = HttpRequest.input('_csrf_token') or HttpRequest.input('csrf_token')
        if token:
            return token

        return None

    def _requires_csrf_protection(self, request: Request) -> bool:
        """Check if request needs CSRF protection"""
        # Only protect state-changing operations
        protected_methods = ["POST", "PUT", "DELETE", "PATCH"]
        if HttpRequest.method() not in protected_methods:
            return False

        # Skip CSRF for auth endpoints (they use different protection)
        if Route.has_prefix('auth'):
            return False

        # Protect all other API endpoints
        return Route.is_api()

    def _verify_csrf_token(self, token: str, cookie: str) -> bool:
        """Verify CSRF token matches cookie"""
        return Crypto.verify_csrf_token(token, cookie, self.secret_key)

    def generate_csrf_token(self) -> tuple[str, str]:
        """
        Returns:
            tuple: (token, cookie)
        """
        return Crypto.generate_csrf_token(self.secret_key)
