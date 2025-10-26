"""
Cache Facade
Laravel-style cache facade with automatic driver switching
"""
from larasanic.support.facades.facade import Facade


class Cache(Facade):
    """
    Cache Facade

    Provides static-like access to cache manager

    Usage:
        # Get/Put
        await Cache.get('key')
        await Cache.put('key', value, ttl=3600)

        # Remember pattern
        value = await Cache.remember('key', 3600, fetch_data)

        # Forget/Flush
        await Cache.forget('key')
        await Cache.flush()

        # Check existence
        if await Cache.has('key'):
            ...

        # Increment/Decrement (Redis only)
        await Cache.increment('counter')
        await Cache.decrement('counter')
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'cache_manager'
