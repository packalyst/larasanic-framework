"""
Rate Limiting Middleware
Prevents abuse by limiting requests per time window
"""
from larasanic.middleware.base_middleware import Middleware
from larasanic.http import ResponseHelper
from larasanic.support.facades import HttpRequest,Route

from sanic import Request
import time
from collections import defaultdict, deque
from typing import Tuple, Optional


class RateLimitMiddleware(Middleware):
    """Rate limiting middleware using sliding window algorithm"""

    # Configuration mapping for MiddlewareConfigMixin
    @staticmethod
    def _get_config_defaults():
        from larasanic.defaults import DEFAULT_RATE_LIMIT, DEFAULT_RATE_LIMIT_WINDOW
        return {
            'default_limit': ('app.RATE_LIMIT_DEFAULT', DEFAULT_RATE_LIMIT),
        }
    CONFIG_MAPPING = _get_config_defaults.__func__()

    @staticmethod
    def _get_static_params():
        from larasanic.defaults import DEFAULT_RATE_LIMIT_WINDOW
        return {'default_window': DEFAULT_RATE_LIMIT_WINDOW}
    STATIC_PARAMS = _get_static_params.__func__()
    DEFAULT_ENABLED = True

    def __init__(self, default_limit: int = None, default_window: int = None):
        """
        Initialize rate limiter
        """
        from larasanic.defaults import DEFAULT_RATE_LIMIT, DEFAULT_RATE_LIMIT_WINDOW, DEFAULT_AUTH_RATE_LIMIT
        self.default_limit = default_limit or DEFAULT_RATE_LIMIT
        self.default_window = default_window or DEFAULT_RATE_LIMIT_WINDOW
        self.buckets = defaultdict(lambda: defaultdict(deque))

        # Custom limits for specific routes
        self.route_limits = {
            'auth': (DEFAULT_AUTH_RATE_LIMIT, DEFAULT_RATE_LIMIT_WINDOW),
            'api': (DEFAULT_RATE_LIMIT, DEFAULT_RATE_LIMIT_WINDOW),
        }

    async def before_request(self, request: Request):
        """Check rate limit before processing request"""
        if not self._should_rate_limit():
            return None

        client_ip = HttpRequest.client_ip()
        route_key = self._get_route_key()
        bucket_key = f"{client_ip}:{route_key}"

        limit, window = self._get_limits(route_key)

        if self._is_rate_limited(bucket_key, limit, window):
            return ResponseHelper.limitexceded(f'Too many requests. Limit: {limit} requests per {window} seconds')

        return None

    def _should_rate_limit(self) -> bool:
        """Check if request should be rate limited"""
        # Rate limit all API endpoints
        return Route.is_api()

    def _get_route_key(self) -> str:
        """Determine route category for rate limiting"""
        if Route.has_prefix('auth'):
            return "auth"
        return "api"

    def _get_limits(self, route_key: str) -> Tuple[int, int]:
        """
        Get rate limit configuration for route
        """
        return self.route_limits.get(route_key, (self.default_limit, self.default_window))

    def _is_rate_limited(self, bucket_key: str, limit: int, window: int) -> bool:
        """
        Check if request exceeds rate limit
        Returns:
            bool: True if rate limited
        """
        now = time.time()
        bucket = self.buckets[bucket_key]["requests"]

        # Remove expired entries
        while bucket and bucket[0] <= now - window:
            bucket.popleft()

        # Check if limit exceeded
        if len(bucket) >= limit:
            return True

        # Add current request timestamp
        bucket.append(now)
        return False

    def set_route_limit(self, route_key: str, limit: int, window: int):
        """
        Configure custom rate limit for a route
        """
        self.route_limits[route_key] = (limit, window)
