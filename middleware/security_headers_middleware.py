"""
Security Headers Middleware
Adds comprehensive security headers to all responses
"""
from larasanic.middleware.base_middleware import Middleware
from sanic import Request
from typing import Dict, Optional


class SecurityHeadersMiddleware(Middleware):
    """
    Middleware for adding security headers to responses

    Implements OWASP recommended security headers:
    - X-Frame-Options: Prevents clickjacking
    - X-Content-Type-Options: Prevents MIME sniffing
    - Content-Security-Policy: Controls resource loading
    - Strict-Transport-Security: Enforces HTTPS
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    """

    # Configuration mapping for MiddlewareConfigMixin
    CONFIG_MAPPING = {
        'x_frame_options': ('security.X_FRAME_OPTIONS', 'DENY'),
        'x_content_type_options': ('security.X_CONTENT_TYPE_OPTIONS', 'nosniff'),
        'content_security_policy': ('security.CSP_POLICY', None),
        'enable_csp': ('security.CSP_ENABLED', True),
        'enable_hsts': ('security.HSTS_ENABLED', False),
        'hsts_max_age': ('security.HSTS_MAX_AGE', None),  # Will use DEFAULT_HSTS_MAX_AGE
        'hsts_include_subdomains': ('security.HSTS_INCLUDE_SUBDOMAINS', True),
        'hsts_preload': ('security.HSTS_PRELOAD', False),
        'referrer_policy': ('security.REFERRER_POLICY', 'strict-origin-when-cross-origin'),
        'permissions_policy': ('security.PERMISSIONS_POLICY', None),
        'x_xss_protection': ('security.X_XSS_PROTECTION', '1; mode=block'),
    }
    DEFAULT_ENABLED = True  # Always enabled for security

    def __init__(
        self,
        # X-Frame-Options
        x_frame_options: str = "DENY",

        # X-Content-Type-Options
        x_content_type_options: str = "nosniff",

        # Content-Security-Policy
        content_security_policy: Optional[str] = None,

        # Strict-Transport-Security
        strict_transport_security: Optional[str] = None,
        hsts_max_age: int = None,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,

        # Referrer-Policy
        referrer_policy: str = "strict-origin-when-cross-origin",

        # Permissions-Policy (formerly Feature-Policy)
        permissions_policy: Optional[str] = None,

        # X-XSS-Protection (legacy, for older browsers)
        x_xss_protection: str = "1; mode=block",

        # Custom headers
        custom_headers: Optional[Dict[str, str]] = None,

        # Feature flags
        enable_hsts: bool = False,  # Disabled by default (requires HTTPS)
        enable_csp: bool = True,
    ):
        """
        Initialize security headers middleware
        """
        from larasanic.defaults import DEFAULT_HSTS_MAX_AGE
        if hsts_max_age is None:
            hsts_max_age = DEFAULT_HSTS_MAX_AGE
        self.x_frame_options = x_frame_options
        self.x_content_type_options = x_content_type_options
        self.content_security_policy = content_security_policy
        self.strict_transport_security = strict_transport_security
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy
        self.x_xss_protection = x_xss_protection
        self.custom_headers = custom_headers or {}
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp

    async def before_request(self, request: Request):
        """No request processing needed"""
        return None

    async def after_response(self, request: Request, response):
        """Add security headers to response"""
        from larasanic.support.facades import HttpResponse

        # X-Frame-Options: Prevent clickjacking
        if self.x_frame_options:
            HttpResponse.header('X-Frame-Options', self.x_frame_options)

        # X-Content-Type-Options: Prevent MIME sniffing
        if self.x_content_type_options:
            HttpResponse.header('X-Content-Type-Options', self.x_content_type_options)

        # X-XSS-Protection: Legacy XSS protection for older browsers
        if self.x_xss_protection:
            HttpResponse.header('X-XSS-Protection', self.x_xss_protection)

        # Content-Security-Policy: Control resource loading
        if self.enable_csp:
            csp = self.content_security_policy or self._get_default_csp()
            if csp:
                HttpResponse.header('Content-Security-Policy', csp)

        # Strict-Transport-Security: Force HTTPS
        if self.enable_hsts:
            hsts = self.strict_transport_security or self._build_hsts_header()
            if hsts:
                HttpResponse.header('Strict-Transport-Security', hsts)

        # Referrer-Policy: Control referrer information leakage
        if self.referrer_policy:
            HttpResponse.header('Referrer-Policy', self.referrer_policy)

        # Permissions-Policy: Control browser features
        if self.permissions_policy:
            HttpResponse.header('Permissions-Policy', self.permissions_policy)
        elif self.permissions_policy is None:
            # Use default restrictive policy
            HttpResponse.header('Permissions-Policy', self._get_default_permissions_policy())

        # Custom headers
        HttpResponse.headers(self.custom_headers)

        return response

    def _get_default_csp(self) -> str:
        """
        Get default Content Security Policy

        NOTE: Includes 'unsafe-eval' and 'unsafe-inline' for Alpine.js/Vue.js
        For production, consider using nonces or hashes instead

        Returns:
            Secure default CSP policy
        """
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' 'unsafe-inline'; "  # Alpine.js needs both
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    def _build_hsts_header(self) -> str:
        """
        Build Strict-Transport-Security header
        """
        hsts = f"max-age={self.hsts_max_age}"

        if self.hsts_include_subdomains:
            hsts += "; includeSubDomains"

        if self.hsts_preload:
            hsts += "; preload"

        return hsts

    def _get_default_permissions_policy(self) -> str:
        """
        Get default Permissions Policy (restrictive)

        Returns:
            Permissions-Policy header value
        """
        return (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
