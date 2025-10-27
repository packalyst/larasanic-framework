"""
Config Manager - Laravel-style configuration access
Access config files using dot notation
"""

import importlib
import threading
from typing import Any, Optional, Dict


class Config:
    """
    Configuration manager with dot notation access

    Usage:
        # Get config value
        app_name = Config.get('app.name')
        db_host = Config.get('database.connections.default.host')

        # With default
        debug = Config.get('app.debug', False)

        # Set runtime value
        Config.set('app.debug', True)

        # Check existence
        if Config.has('services.stripe.key'):
            ...

    Config files should be in config/ directory:
        config/
        ├── app.py
        ├── database.py
        ├── auth.py
        └── services.py
    """

    _lock = threading.Lock()
    _loaded: Dict[str, Any] = {}
    _runtime_overrides: Dict[str, Any] = {}
    _caching_enabled: bool = False
    _cache: Dict[str, Any] = {}

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation (case-insensitive)

        Args:
            key: Config key in dot notation (e.g., 'app.name', 'database.host')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            app_name = Config.get('app.name', 'Framework')
            app_name = Config.get('app.NAME', 'Framework')  # Same result
            app_name = Config.get('APP.Name', 'Framework')  # Same result
        """
        # Convert key to lowercase for case-insensitive lookup
        key_lower = key.lower()

        # Check cache first if caching is enabled
        if cls._caching_enabled and key_lower in cls._cache:
            return cls._cache[key_lower]

        # Check runtime overrides first
        if key_lower in cls._runtime_overrides:
            return cls._runtime_overrides[key_lower]

        # Parse dot notation
        parts = key_lower.split('.')
        file_name = parts[0]
        path = parts[1:]

        # Load config file if not already loaded
        if file_name not in cls._loaded:
            cls._load_config_file(file_name)

        # Navigate through the config structure
        value = cls._loaded.get(file_name)

        if value is None:
            return default

        # Navigate nested attributes (case-insensitive)
        for part in path:
            # Try case-insensitive attribute lookup
            if hasattr(value, '__dict__'):
                # Module or object with attributes
                attr_found = False
                for attr_name in dir(value):
                    if attr_name.lower() == part:
                        value = getattr(value, attr_name)
                        attr_found = True
                        break
                if not attr_found:
                    # Try as dict if attribute not found
                    if isinstance(value, dict):
                        dict_found = False
                        for dict_key in value.keys():
                            if dict_key.lower() == part:
                                value = value[dict_key]
                                dict_found = True
                                break
                        if not dict_found:
                            return default
                    else:
                        return default
            elif isinstance(value, dict):
                # Dict lookup (case-insensitive)
                dict_found = False
                for dict_key in value.keys():
                    if dict_key.lower() == part:
                        value = value[dict_key]
                        dict_found = True
                        break
                if not dict_found:
                    return default
            else:
                return default

        # Cache the value if caching is enabled
        if cls._caching_enabled:
            cls._cache[key_lower] = value

        return value

    @classmethod
    def _load_config_file(cls, file_name: str):
        """
        Load a config file from config/ directory

        Args:
            file_name: Config file name (without .py extension)
        """
        with cls._lock:
            if file_name in cls._loaded:
                return

            try:
                # Import the config module
                module = importlib.import_module(f'config.{file_name}')
                cls._loaded[file_name] = module
            except ImportError:
                # Config file doesn't exist
                cls._loaded[file_name] = None

    @classmethod
    def set(cls, key: str, value: Any):
        """
        Set configuration value at runtime (does not persist to file)

        Args:
            key: Config key in dot notation (case-insensitive)
            value: Value to set

        Example:
            Config.set('app.debug', True)
            Config.set('APP.DEBUG', True)  # Same result
        """
        # Convert key to lowercase for case-insensitive storage
        cls._runtime_overrides[key.lower()] = value

    @classmethod
    def has(cls, key: str) -> bool:
        """
        Check if configuration key exists

        Args:
            key: Config key in dot notation

        Returns:
            bool: True if exists

        Example:
            if Config.has('services.stripe'):
                ...
        """
        return cls.get(key) is not None

    @classmethod
    def all(cls, file_name: str) -> Optional[Any]:
        """
        Get all configuration from a file

        Args:
            file_name: Config file name

        Returns:
            Config module or None

        Example:
            app_config = Config.all('app')
            print(app_config.APP_NAME)
        """
        if file_name not in cls._loaded:
            cls._load_config_file(file_name)

        return cls._loaded.get(file_name)

    @classmethod
    def reload(cls, file_name: Optional[str] = None):
        """
        Reload configuration file(s)

        Args:
            file_name: Specific file to reload, or None to reload all
        """
        with cls._lock:
            if file_name:
                if file_name in cls._loaded:
                    del cls._loaded[file_name]
                    cls._load_config_file(file_name)
            else:
                # Reload all loaded configs
                loaded_files = list(cls._loaded.keys())
                cls._loaded.clear()
                for file in loaded_files:
                    cls._load_config_file(file)

    @classmethod
    def clear_runtime_overrides(cls):
        """Clear all runtime configuration overrides"""
        cls._runtime_overrides.clear()

    @classmethod
    def enable_caching(cls, enabled: bool = True):
        """
        Enable or disable config value caching for production performance

        Args:
            enabled: True to enable caching, False to disable

        Example:
            # Enable caching in production
            if os.getenv('APP_ENV') == 'production':
                Config.enable_caching(True)
        """
        cls._caching_enabled = enabled
        if not enabled:
            cls.clear_cache()

    @classmethod
    def clear_cache(cls):
        """
        Clear the config value cache

        Example:
            Config.clear_cache()
        """
        cls._cache.clear()

    @classmethod
    def is_caching_enabled(cls) -> bool:
        """
        Check if config caching is enabled

        Returns:
            bool: True if caching is enabled
        """
        return cls._caching_enabled

    @classmethod
    def as_object(cls, key: str, default: Any = None) -> Any:
        """
        Get configuration as an object with attribute access

        Converts dict configs to simple objects where you can access
        keys as attributes (e.g., obj.spa_enabled instead of dict['spa_enabled'])

        Args:
            key: Config key in dot notation
            default: Default value if key not found

        Returns:
            ConfigObject with attribute access, or default

        Example:
            # Instead of:
            config = Config.get('template.BLADE_VIEW_CONFIG', {})
            spa_enabled = config['spa_enabled']

            # Use:
            config = Config.as_object('template.BLADE_VIEW_CONFIG')
            spa_enabled = config.spa_enabled
        """
        value = cls.get(key, default)

        # If it's a dict, convert to ConfigObject
        if isinstance(value, dict):
            return ConfigObject(**value)

        # If it's already an object, return as-is
        return value

    @classmethod
    def asObject(cls, key: str, default: Any = None) -> Any:
        """
        Deprecated: Use as_object() instead (PEP 8 naming)
        """
        return cls.as_object(key, default)


class ConfigObject:
    """
    Simple object wrapper for dict configs
    Allows attribute access to config values
    """

    def __init__(self, **kwargs):
        """Initialize with keyword arguments as attributes"""
        for key, value in kwargs.items():
            # Recursively convert nested dicts to ConfigObjects
            if isinstance(value, dict):
                setattr(self, key, ConfigObject(**value))
            else:
                setattr(self, key, value)

    def __repr__(self):
        """String representation"""
        attrs = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'ConfigObject({attrs})'

    def __getattr__(self, name):
        """Fallback for missing attributes"""
        raise AttributeError(f"Config has no attribute '{name}'")
