"""
Guest Middleware
Laravel-style guest-only middleware - redirect if already authenticated
"""
from larasanic.middleware.base_middleware import Middleware
from larasanic.http import ResponseHelper
from sanic import Request
from typing import Optional
from larasanic.support.facades import Auth

class GuestMiddleware(Middleware):
    """
    Guest middleware - only allow non-authenticated users

    Laravel equivalent: app/Http/Middleware/RedirectIfAuthenticated.php

    Behavior:
    - If user is NOT authenticated (guest): Continue to next middleware/handler
    - If user IS authenticated: Redirect to dashboard/home

    Use case: Login and register pages should only be accessible to guests

    Usage in routes:
        Route.get('/login', handler).middleware('guest')
        Route.get('/register', handler).middleware('guest')

        # Or group routes
        Route.middleware('guest').group(lambda: [
            Route.get('/login', login_handler),
            Route.get('/register', register_handler),
        ])
    """

    def __init__(self, redirect_to: str = None):
        self.redirect_to = redirect_to

    @classmethod
    def _register_middleware(cls) -> Optional['GuestMiddleware']:
        """
        Factory method to create middleware instance from configuration
        """
        from larasanic.support import Config

        return cls(redirect_to=Config.get('auth.HOME_URL', '/dashboard'))

    async def before_request(self, request: Request):
        """
        Check if user is NOT authenticated (guest)
        """
        try:
            # Try to get user from request
            user = await Auth.get_user_from_request(request)
            if user:
                # Already authenticated - redirect away from guest pages
                # STOP HERE, return response
                return ResponseHelper.redirect(self.redirect_to)
            # Not authenticated (guest) - continue to login/register page
            return None

        except Exception:
            # If auth service fails, treat as guest (allow access)
            return None

    async def after_response(self, request: Request, response):
        """
        Returns:
            response: Unmodified response
        """
        return response
