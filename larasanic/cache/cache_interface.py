"""
Cache Store Interface
Abstract base class for all cache stores
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Callable


class CacheStoreInterface(ABC):
    """
    Interface that all cache stores must implement

    This ensures consistent API across file, redis, memory, etc.
    """

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get cached value

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        pass

    @abstractmethod
    async def put(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Put value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = use DEFAULT_CACHE_TTL, 0 = forever)

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    async def has(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            bool: True if exists
        """
        pass

    @abstractmethod
    async def forget(self, key: str) -> bool:
        """
        Remove key from cache

        Args:
            key: Cache key

        Returns:
            bool: True if removed
        """
        pass

    @abstractmethod
    async def flush(self) -> bool:
        """
        Clear all cache

        Returns:
            bool: True if successful
        """
        pass

    async def remember(self, key: str, ttl: int, callback: Callable) -> Any:
        """
        Get cached value or compute and cache it

        Args:
            key: Cache key
            ttl: Time to live in seconds
            callback: Function to call if cache miss (can be sync or async)

        Returns:
            Cached or computed value
        """
        # Try to get from cache
        value = await self.get(key)

        if value is not None:
            return value

        # Cache miss - compute value
        import asyncio
        if asyncio.iscoroutinefunction(callback):
            value = await callback()
        else:
            value = callback()

        # Cache it
        await self.put(key, value, ttl)

        return value

    async def remember_forever(self, key: str, callback: Callable) -> Any:
        """
        Get cached value or compute and cache it forever

        Args:
            key: Cache key
            callback: Function to call if cache miss

        Returns:
            Cached or computed value
        """
        return await self.remember(key, 0, callback)

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a value (optional, not all stores support this)

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value
        """
        value = await self.get(key, 0)
        new_value = int(value) + amount
        await self.put(key, new_value)
        return new_value

    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement a value (optional, not all stores support this)

        Args:
            key: Cache key
            amount: Amount to decrement

        Returns:
            New value
        """
        return await self.increment(key, -amount)