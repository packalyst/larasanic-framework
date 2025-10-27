"""
EnvHelper - Read/Write .env files programmatically
Laravel-style environment variable management
"""

import os
import threading
from typing import Optional, Any, Dict, TYPE_CHECKING
from dotenv import load_dotenv, set_key, unset_key

if TYPE_CHECKING:
    from pathlib import Path

class EnvHelper:
    """
    Environment variable manager with .env file read/write support

    Usage:
        # Read
        value = EnvHelper.get('APP_NAME', 'Default App')

        # Write
        EnvHelper.set('APP_NAME', 'My App')

        # Check
        if EnvHelper.has('DATABASE_URL'):
            ...

        # Load
        EnvHelper.load('/path/to/.env')
    """

    _lock = threading.Lock()
    _env_path = None
    _loaded: bool = False

    @classmethod
    def initialize(cls, env_path=None):
        """
        Initialize EnvHelper

        Args:
            env_path: Path to .env file (defaults to .env in project root)
        """
        if env_path is None:
            from larasanic.support.storage import Storage
            env_path = Storage.base('.env')

        cls._env_path = env_path

    @classmethod
    def load(cls, env_path=None, override: bool = False):
        """
        Load .env file into environment

        Args:
            env_path: Path to .env file (defaults to initialized path)
            override: Whether to override existing environment variables

        Returns:
            bool: True if loaded successfully
        """
        with cls._lock:
            if env_path:
                cls._env_path = env_path

            if cls._env_path is None:
                cls.initialize()

            if not cls._env_path.exists():
                # Create empty .env if it doesn't exist
                cls._env_path.touch()

            load_dotenv(cls._env_path, override=override)
            cls._loaded = True
            return True

    @classmethod
    def get(cls, key: str, default: Any = None) -> Optional[str]:
        """
        Get environment variable value

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Variable value or default

        Example:
            app_name = Env.get('APP_NAME', 'Framework')
        """
        if not cls._loaded:
            cls.load()

        return os.getenv(key, default)

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        """
        Get boolean environment variable

        Args:
            key: Environment variable name
            default: Default value

        Returns:
            Boolean value

        Example:
            debug = Env.get_bool('APP_DEBUG', False)
        """
        value = cls.get(key)
        if value is None:
            return default

        return value.lower() in ('true', '1', 'yes', 'on')

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        """
        Get integer environment variable

        Args:
            key: Environment variable name
            default: Default value

        Returns:
            Integer value
        """
        value = cls.get(key)
        if value is None:
            return default

        try:
            return int(value)
        except ValueError:
            return default

    @classmethod
    def set(cls, key: str, value: Any, quote_mode: str = 'auto') -> bool:
        """
        Set environment variable and write to .env file

        Args:
            key: Environment variable name
            value: Value to set
            quote_mode: Quote mode ('auto', 'always', 'never')

        Returns:
            bool: True if set successfully

        Example:
            Env.set('APP_NAME', 'My App')
        """
        with cls._lock:
            if cls._env_path is None:
                cls.initialize()

            # Ensure .env file exists
            if not cls._env_path.exists():
                cls._env_path.touch()

            # Convert value to string
            str_value = str(value) if not isinstance(value, str) else value

            # Write to .env file
            result = set_key(str(cls._env_path), key, str_value, quote_mode=quote_mode)

            # Update current environment
            os.environ[key] = str_value

            return result is not None

    @classmethod
    def has(cls, key: str) -> bool:
        """
        Check if environment variable exists

        Args:
            key: Environment variable name

        Returns:
            bool: True if exists

        Example:
            if Env.has('DATABASE_URL'):
                ...
        """
        if not cls._loaded:
            cls.load()

        return key in os.environ

    @classmethod
    def remove(cls, key: str) -> bool:
        """
        Remove environment variable from .env file

        Args:
            key: Environment variable name

        Returns:
            bool: True if removed successfully
        """
        with cls._lock:
            if cls._env_path is None:
                cls.initialize()

            if not cls._env_path.exists():
                return False

            # Remove from .env file
            result = unset_key(str(cls._env_path), key)

            # Remove from current environment
            if key in os.environ:
                del os.environ[key]

            return result is not None

    @classmethod
    def all(cls) -> Dict[str, str]:
        """
        Get all environment variables

        Returns:
            Dict of all environment variables
        """
        if not cls._loaded:
            cls.load()

        return dict(os.environ)

    @classmethod
    def path(cls) -> Optional['Path']:
        """
        Get .env file path

        Returns:
            Path to .env file
        """
        if cls._env_path is None:
            cls.initialize()

        return cls._env_path


# Auto-load .env on import
EnvHelper.load()
