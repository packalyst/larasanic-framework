"""
Cache Manager
Laravel-style cache manager with swappable drivers
"""
from typing import Any, Optional, Callable, Dict
from larasanic.cache.cache_interface import CacheStoreInterface
from larasanic.cache.stores.file_store import FileStore
from larasanic.cache.stores.redis_store import RedisStore


class CacheManager:
    """
    Cache Manager - manages multiple cache stores

    Usage:
        # Initialize with driver from config
        manager = CacheManager(driver='redis', config=CACHE_CONFIG)

        # Use cache
        await manager.get('key')
        await manager.put('key', value, ttl=3600)
        await manager.remember('key', 3600, callback)
    """

    def __init__(self, driver: str = 'file', config: Dict = None):
        """
        Initialize cache manager
        """
        self.driver_name = driver
        self.config = config or {}
        self._store: Optional[CacheStoreInterface] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazy initialization of cache store"""
        if not self._initialized:
            self._store = self._create_store(self.driver_name, self.config)
            self._initialized = True

    def _create_store(self, driver: str, config: Dict) -> CacheStoreInterface:
        """
        Create cache store instance based on driver
        """
        if driver == 'file':
            cache_dir = config.get('path')
            return FileStore(cache_dir=cache_dir)

        elif driver == 'redis':
            from larasanic.defaults import DEFAULT_REDIS_URL
            redis_url = config.get('url', DEFAULT_REDIS_URL)
            return RedisStore(redis_url=redis_url)

        else:
            raise ValueError(f"Unknown cache driver: {driver}")

    def store(self, name: str = None) -> 'CacheManager':
        """
        Get a different cache store
        """
        # For now, just return self
        # Could be extended to support multiple stores
        return self

    async def get(self, key: str, default: Any = None) -> Any:
        """Get cached value"""
        await self._ensure_initialized()
        return await self._store.get(key, default)

    async def put(self, key: str, value: Any, ttl: int = None) -> bool:
        """Put value in cache"""
        if ttl is None:
            from larasanic.defaults import DEFAULT_CACHE_TTL
            ttl = DEFAULT_CACHE_TTL
        await self._ensure_initialized()
        return await self._store.put(key, value, ttl)

    async def has(self, key: str) -> bool:
        """Check if key exists"""
        await self._ensure_initialized()
        return await self._store.has(key)

    async def forget(self, key: str) -> bool:
        """Remove key from cache"""
        await self._ensure_initialized()
        return await self._store.forget(key)

    async def flush(self) -> bool:
        """Clear all cache"""
        await self._ensure_initialized()
        return await self._store.flush()

    async def remember(self, key: str, ttl: int, callback: Callable) -> Any:
        """Get cached value or compute and cache it"""
        await self._ensure_initialized()
        return await self._store.remember(key, ttl, callback)

    async def remember_forever(self, key: str, callback: Callable) -> Any:
        """Get cached value or compute and cache it forever"""
        await self._ensure_initialized()
        return await self._store.remember_forever(key, callback)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a value"""
        await self._ensure_initialized()
        return await self._store.increment(key, amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a value"""
        await self._ensure_initialized()
        return await self._store.decrement(key, amount)

    # Synchronous fallback methods for backward compatibility
    # (These will be deprecated in favor of async)

    def get_sync(self, key: str, default: Any = None) -> Any:
        """Synchronous get (for backward compatibility)"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is running, we can't use it
                # This shouldn't happen in production
                raise RuntimeError("Cannot use sync methods in async context")
            return loop.run_until_complete(self.get(key, default))
        except Exception:
            return default

    def put_sync(self, key: str, value: Any, ttl: int = None) -> bool:
        """Synchronous put (for backward compatibility)"""
        if ttl is None:
            from larasanic.defaults import DEFAULT_CACHE_TTL
            ttl = DEFAULT_CACHE_TTL
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot use sync methods in async context")
            return loop.run_until_complete(self.put(key, value, ttl))
        except Exception:
            return False

    def forget_sync(self, key: str) -> bool:
        """Synchronous forget (for backward compatibility)"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot use sync methods in async context")
            return loop.run_until_complete(self.forget(key))
        except Exception:
            return False

    def flush_sync(self) -> bool:
        """Synchronous flush (for backward compatibility)"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot use sync methods in async context")
            return loop.run_until_complete(self.flush())
        except Exception:
            return False