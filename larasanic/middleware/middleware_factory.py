"""
Middleware Factory
Centralized middleware configuration loading to eliminate duplication
"""
from typing import Optional, Dict, Any, Type
from larasanic.middleware.base_middleware import Middleware
from larasanic.support import Config


class MiddlewareFactory:
    """
    Factory for creating middleware instances with configuration
    Eliminates repetitive _register_middleware() boilerplate
    """

    @staticmethod
    def create_from_config(
        middleware_class: Type[Middleware],
        enabled_config_key: str = None,
        config_mapping: Dict[str, tuple] = None,
        default_enabled: bool = True,
        **static_params
    ) -> Optional[Middleware]:
        """
        Create middleware instance from configuration with zero boilerplate

        Args:
            middleware_class: The middleware class to instantiate
            enabled_config_key: Config key to check if middleware is enabled
                               (e.g., 'security.CORS_ENABLED')
            config_mapping: Maps constructor params to config keys
                          Format: {'param_name': ('config.KEY', default_value)}
            default_enabled: Default enabled state if config key not found
            **static_params: Static parameters that don't come from config

        Returns:
            Middleware instance if enabled, None otherwise

        Example:
            # Instead of writing _register_middleware() for each middleware:
            return MiddlewareFactory.create_from_config(
                CorsMiddleware,
                enabled_config_key='security.CORS_ENABLED',
                config_mapping={
                    'allowed_origins': ('security.ALLOWED_ORIGINS', ['*']),
                    'max_age': ('security.CORS_MAX_AGE', 3600),
                },
                allow_credentials=True  # Static param
            )
        """
        # Check if middleware is enabled
        if enabled_config_key:
            enabled = Config.get(enabled_config_key, default_enabled)
            if not enabled:
                return None

        # Load configuration parameters
        config_params = {}
        if config_mapping:
            for param_name, (config_key, default_value) in config_mapping.items():
                config_params[param_name] = Config.get(config_key, default_value)

        # Merge with static parameters
        all_params = {**config_params, **static_params}

        # Instantiate middleware
        return middleware_class(**all_params)

    @staticmethod
    def create_with_validator(
        middleware_class: Type[Middleware],
        enabled_check: callable = None,
        config_loader: callable = None
    ) -> Optional[Middleware]:
        """
        Create middleware with custom validation and config loading
        For complex cases that need more than simple key-value mapping

        Args:
            middleware_class: The middleware class to instantiate
            enabled_check: Function that returns True if middleware should be enabled
            config_loader: Function that returns dict of constructor parameters

        Returns:
            Middleware instance if enabled, None otherwise

        Example:
            return MiddlewareFactory.create_with_validator(
                CustomMiddleware,
                enabled_check=lambda: Config.get('app.DEBUG') or Config.get('custom.ENABLED'),
                config_loader=lambda: {
                    'setting1': complex_logic_to_get_setting(),
                    'setting2': Config.get('custom.SETTING2'),
                }
            )
        """
        # Check if enabled
        if enabled_check and not enabled_check():
            return None

        # Load configuration
        params = config_loader() if config_loader else {}

        # Instantiate
        return middleware_class(**params)
