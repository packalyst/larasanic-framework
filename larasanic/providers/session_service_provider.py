"""
Session Service Provider
Registers session middleware and services
"""
from larasanic.service_provider import ServiceProvider
from larasanic.middleware.session_middleware import SessionMiddleware
from larasanic.support.facades import App


class SessionServiceProvider(ServiceProvider):
    """Service provider for session management"""
    def register(self):
        """Register session services"""
        # Session middleware will be registered in boot
        pass

    def boot(self):
        """Bootstrap session services"""
        # Register session middleware using App facade
        middleware_manager = App.make('middleware_manager')

        middleware_manager.add(SessionMiddleware())
