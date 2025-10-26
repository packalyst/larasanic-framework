"""
Routing Service Provider
"""
from larasanic.service_provider import ServiceProvider
from larasanic.routing import Router
from larasanic.http import UrlGenerator
from larasanic.support.facades import App

class RoutingServiceProvider(ServiceProvider):
    def register(self):
        """Register routing services"""
        # Register Router as singleton
        App.singleton('router', lambda app: Router())
        # Register URL Generator (uses Route facade for router, HttpRequest facade for context)
        App.singleton('url_generator', lambda app: UrlGenerator())
