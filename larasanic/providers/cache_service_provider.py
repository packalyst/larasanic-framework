"""
Cache Service Provider
Registers cache manager with the application container
"""
from larasanic.service_provider import ServiceProvider
from larasanic.support.facades import App
from larasanic.cache import CacheManager


class CacheServiceProvider(ServiceProvider):
    def register(self):
        """Register cache services"""
        # Register CacheManager as singleton
        App.singleton('cache_manager', lambda app: self._create_cache_manager())

    def _create_cache_manager(self):
        """Create cache manager instance with config"""
        # Import config
        from larasanic.support import Config
        try:
            # Try to get custom cache config from app
            from config.cache import get_default_store
            config = get_default_store()
        except ImportError:
            # Fallback to config or default file driver
            driver = Config.get('cache.default_driver', 'file')
            config = {'driver': driver, 'path': None}

        return CacheManager(driver=driver, config=config)

    def boot(self):
        """Bootstrap cache services"""
        # Initialize cache at startup
        pass
