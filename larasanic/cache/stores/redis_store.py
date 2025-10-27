"""
Redis Cache Store
High-performance in-memory caching (10-50x faster than file)
"""
import json
from typing import Any, Optional
import aioredis
from larasanic.cache.cache_interface import CacheStoreInterface


class RedisStore(CacheStoreInterface):

    def __init__(self, redis_url: str = None):
        """
        Initialize Redis cache store

        Args:
            redis_url: Redis connection URL
        """
        if redis_url is None:
            from larasanic.defaults import DEFAULT_REDIS_URL
            redis_url = DEFAULT_REDIS_URL
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False

    async def _ensure_connected(self):
        """Ensure connection to Redis"""
        if not self._connected:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True
            )
            self._connected = True

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self._connected = False

    async def get(self, key: str, default: Any = None) -> Any:
        """Get cached value"""
        await self._ensure_connected()

        try:
            value = await self.redis.get(key)

            if value is None:
                return default

            # Deserialize JSON
            return json.loads(value)
        except Exception:
            return default

    async def put(self, key: str, value: Any, ttl: int = None) -> bool:
        """Put value in cache"""
        if ttl is None:
            from larasanic.defaults import DEFAULT_CACHE_TTL
            ttl = DEFAULT_CACHE_TTL
        await self._ensure_connected()

        try:
            # Serialize to JSON
            serialized = json.dumps(value, ensure_ascii=False)

            if ttl > 0:
                # Set with expiration
                await self.redis.setex(key, ttl, serialized)
            else:
                # Set without expiration
                await self.redis.set(key, serialized)

            return True
        except Exception:
            return False

    async def has(self, key: str) -> bool:
        """Check if key exists in cache"""
        await self._ensure_connected()

        try:
            return await self.redis.exists(key) > 0
        except Exception:
            return False

    async def forget(self, key: str) -> bool:
        """Remove key from cache"""
        await self._ensure_connected()

        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False

    async def flush(self) -> bool:
        """Clear all cache"""
        await self._ensure_connected()

        try:
            await self.redis.flushdb()
            return True
        except Exception:
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a value (Redis native support)

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value
        """
        await self._ensure_connected()
        return await self.redis.incrby(key, amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement a value (Redis native support)

        Args:
            key: Cache key
            amount: Amount to decrement

        Returns:
            New value
        """
        await self._ensure_connected()
        return await self.redis.decrby(key, amount)

    async def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key

        Args:
            key: Cache key

        Returns:
            Remaining seconds (-1 if no expiry, -2 if key doesn't exist)
        """
        await self._ensure_connected()
        return await self.redis.ttl(key)
