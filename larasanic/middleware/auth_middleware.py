"""
Auth Middleware
Laravel-style authentication middleware - requires user to be logged in
"""
from larasanic.middleware.base_middleware import Middleware
from larasanic.http import ResponseHelper
from sanic import Request
from typing import Optional
from larasanic.support.facades import Auth, HttpRequest

class AuthMiddleware(Middleware):
    """
    Authentication middleware - requires user to be logged in

    Laravel equivalent: app/Http/Middleware/Authenticate.php

    Behavior:
    - If user is authenticated: Continue to next middleware/handler
    - If user is NOT authenticated:
        - API routes (/api/*): Return 401 JSON response
        - Web routes: Redirect to login page

    Usage in routes:
        Route.get('/dashboard', handler).middleware('auth')
        Route.get('/profile', handler).middleware(['auth', 'verified'])
    """

    def __init__(self, redirect_to: str = '/login'):
        """
        Initialize auth middleware

        Args:
            redirect_to: URL to redirect to if not authenticated (default: /login)
        """
        self.redirect_to = redirect_to

    @classmethod
    def _register_middleware(cls) -> Optional['AuthMiddleware']:
        """
        Factory method to create middleware instance from configuration

        Returns:
            AuthMiddleware instance if enabled, None otherwise
        """
        from larasanic.support import Config

        # Get redirect URL from config
        redirect_to = Config.get('auth.LOGIN_URL', '/login')

        return cls(redirect_to=redirect_to)

    async def before_request(self, request: Request):
        """
        Check if user is authenticated before handler executes

        Args:
            request: Sanic request object

        Returns:
            None: User authenticated, continue to next middleware/handler
            HTTPResponse: User not authenticated, return early (stops pipeline)
        """
        try:
            # Try to get user from request (JWT token or session)
            user = await Auth.get_user_from_request(request)

            if not user:
                # Not authenticated - STOP HERE, return response
                return self._handle_unauthenticated(request)

            # Authenticated - add user to request context for use in handlers
            HttpRequest.set_user(user)

            # Continue to next middleware/handler
            return None

        except Exception as e:
            # If auth service fails, treat as unauthenticated
            print(f"⚠️  Auth middleware error: {e}")
            return self._handle_unauthenticated(request)

    async def after_response(self, request: Request, response):
        """
        Optional: Modify response after handler (not used for auth)

        Args:
            request: Sanic request object
            response: Response from handler

        Returns:
            response: Unmodified response
        """
        return response

    def _handle_unauthenticated(self, request: Request):
        """
        Handle unauthenticated request

        Args:
            request: Sanic request object

        Returns:
            HTTPResponse: 401 JSON for API, redirect for web
        """
        # Use HttpRequest facade for consistent request type detection
        if HttpRequest.wants_json():
            return ResponseHelper.unauthorized("Authentication required")
        else:
            return ResponseHelper.redirect(self.redirect_to)
