"""
File Cache Store
File-based caching implementation (current implementation)
"""
import json
import time
import threading
from typing import Any, Optional
from pathlib import Path
from larasanic.cache.cache_interface import CacheStoreInterface


class FileStore(CacheStoreInterface):

    def __init__(self, cache_dir: Path = None):
        """
        Initialize file cache store

        Args:
            cache_dir: Directory for cache files
        """
        if cache_dir is None:
            from larasanic.support.storage import Storage
            cache_dir = Storage.cache_data()

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key"""
        # Sanitize key for filesystem
        safe_key = key.replace('/', '_').replace('\\', '_').replace(':', '_')
        return self.cache_dir / f"{safe_key}.cache"

    def _is_expired(self, cache_data: dict) -> bool:
        """Check if cache data is expired"""
        if cache_data.get('ttl') == 0 or cache_data.get('ttl') == -1:
            return False  # Never expires

        expires_at = cache_data.get('expires_at', 0)
        return time.time() > expires_at

    async def get(self, key: str, default: Any = None) -> Any:
        """Get cached value"""
        with self._lock:
            cache_file = self._get_cache_file(key)

            if not cache_file.exists():
                return default

            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                if self._is_expired(cache_data):
                    # Remove expired cache
                    cache_file.unlink()
                    return default

                return cache_data['value']

            except Exception:
                return default

    async def put(self, key: str, value: Any, ttl: int = None) -> bool:
        """Put value in cache"""
        if ttl is None:
            from larasanic.defaults import DEFAULT_CACHE_TTL
            ttl = DEFAULT_CACHE_TTL
        with self._lock:
            cache_file = self._get_cache_file(key)

            cache_data = {
                'value': value,
                'ttl': ttl,
                'expires_at': time.time() + ttl if ttl > 0 else -1,
                'created_at': time.time()
            }

            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
                return True
            except Exception:
                return False

    async def has(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        result = await self.get(key)
        return result is not None

    async def forget(self, key: str) -> bool:
        """Remove key from cache"""
        with self._lock:
            cache_file = self._get_cache_file(key)

            if cache_file.exists():
                try:
                    cache_file.unlink()
                    return True
                except Exception:
                    return False

            return False

    async def flush(self) -> bool:
        """Clear all cache in this store"""
        with self._lock:
            try:
                for cache_file in self.cache_dir.glob('*.cache'):
                    cache_file.unlink()
                return True
            except Exception:
                return False
