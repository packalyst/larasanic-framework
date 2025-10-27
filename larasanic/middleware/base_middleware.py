"""
Base Middleware Class
Abstract base class for all middlewares
"""
from abc import ABC, abstractmethod
from sanic import Request, response
from typing import Optional, Dict, Any

class Middleware(ABC):
    """
    Base middleware class

    Middlewares can:
    - Inspect/modify requests before they reach routes
    - Inspect/modify responses before they're sent
    - Short-circuit requests (return response early)

    Configuration:
    Subclasses can set these class variables for automatic configuration:
    - ENABLED_CONFIG_KEY: Config key to check if middleware is enabled
    - CONFIG_MAPPING: Dict mapping constructor params to config keys
    - DEFAULT_ENABLED: Default enabled state if config key not found
    - STATIC_PARAMS: Static parameters that don't come from config
    """

    # Configuration class variables (subclasses can override)
    ENABLED_CONFIG_KEY: str = None
    CONFIG_MAPPING: Dict[str, tuple] = {}
    DEFAULT_ENABLED: bool = True
    STATIC_PARAMS: Dict[str, Any] = {}

    @classmethod
    def _is_enabled(cls) -> bool:
        """
        Hook for custom enabled check logic

        Override this method to implement custom enabled logic.
        By default, checks ENABLED_CONFIG_KEY from config.

        Returns:
            True if middleware should be enabled
        """
        from larasanic.support import Config

        if cls.ENABLED_CONFIG_KEY:
            return Config.get(cls.ENABLED_CONFIG_KEY, cls.DEFAULT_ENABLED)

        return cls.DEFAULT_ENABLED

    @classmethod
    def _register_middleware(cls) -> Optional['Middleware']:
        """
        Factory method to create middleware instance from configuration

        Default implementation:
        1. Check if it should be enabled (via _is_enabled hook)
        2. Load configuration parameters from CONFIG_MAPPING
        3. Return configured instance or None if disabled

        To customize enabled logic, override _is_enabled() instead of this method.

        Returns:
            Middleware instance if enabled, None otherwise
        """
        from larasanic.support import Config

        # Check if middleware is enabled (use hook for custom logic)
        if not cls._is_enabled():
            return None

        # Load configuration parameters
        config_params = {}
        if cls.CONFIG_MAPPING:
            for param_name, (config_key, default_value) in cls.CONFIG_MAPPING.items():
                config_params[param_name] = Config.get(config_key, default_value)

        # Merge with static parameters
        all_params = {**config_params, **cls.STATIC_PARAMS}

        # Instantiate middleware
        return cls(**all_params)

    @abstractmethod
    async def before_request(self, request: Request):
        """
        Called before the request reaches the route handler

        Args:
            request: The Sanic request object

        Returns:
            None: Continue to next middleware/route
            HTTPResponse: Short-circuit and return response immediately
        """
        pass

    async def after_response(self, request: Request, response):
        """
        Called after the route handler, before sending response

        Args:
            request: The Sanic request object
            response: The response object

        Returns:
            response: Modified or original response
        """
        return response
