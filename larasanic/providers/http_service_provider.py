"""
HTTP Service Provider
Registers HTTP layer services including middleware and HTTP client
"""
from larasanic.service_provider import ServiceProvider
from larasanic.service_middleware import ServiceMiddleware
from larasanic.support.facades import App

class HttpServiceProvider(ServiceProvider):
    """HTTP layer service provider"""

    def register(self):
        """Register HTTP services"""
        # Create middleware manager
        middleware_manager = ServiceMiddleware(self.app)
        App.singleton('middleware_manager', middleware_manager)

        # Register HTTP client (async by default)
        from larasanic.http.http_client import AsyncHTTPClient, SecurityLevel

        def make_http_client():
            """Factory for creating HTTP client instances"""
            from larasanic.support import Config

            # Get config with defaults
            from larasanic.defaults import DEFAULT_HTTP_TIMEOUT, DEFAULT_HTTP_MAX_REDIRECTS
            config = {
                'security_level': SecurityLevel[Config.get('http.security_level', 'BALANCED')],
                'timeout': Config.get('http.timeout', DEFAULT_HTTP_TIMEOUT),
                'max_retries': Config.get('http.max_retries', 1),
                'verify_ssl': Config.get('http.verify_ssl', True),
                'follow_redirects': Config.get('http.follow_redirects', True),
                'max_redirects': Config.get('http.max_redirects', DEFAULT_HTTP_MAX_REDIRECTS),
                'proxy': Config.get('http.proxy', None),
                'rate_limit': Config.get('http.rate_limit', None),
            }

            return AsyncHTTPClient(**config)

        App.singleton('http_client', make_http_client)

    def boot(self):
        """Bootstrap HTTP services"""
        self.register_default_middlewares()

    def register_default_middlewares(self):
        from larasanic.support import ClassLoader, Config

        middleware_manager = App.make('middleware_manager')
        global_middleware = Config.get('middleware.GLOBAL_MIDDLEWARE', {})

        for name, middleware_path in global_middleware.items():
            try:
                middleware_cls = ClassLoader.load(middleware_path)

                # Pass the CLASS - add() will handle registration and config loading
                middleware_manager.add(middleware_cls, name=name)
            except Exception as e:
                # print(f"❌ Failed to load global middleware '{name}': {e}")
                pass