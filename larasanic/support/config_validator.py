"""
Configuration Validator
Validates configuration files on startup to catch misconfigurations early
"""
import os
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails"""
    pass


class ConfigValidator:
    """
    Validates configuration values

    Ensures required config values exist and are valid before app starts
    """

    def __init__(self):
        """Initialize validator"""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_required(self, key: str, value: Any, message: Optional[str] = None) -> bool:
        """
        Validate that a required config value exists

        Args:
            key: Config key
            value: Config value
            message: Custom error message

        Returns:
            bool: True if valid
        """
        if value is None or value == '':
            error_msg = message or f"Required config '{key}' is missing or empty"
            self.errors.append(error_msg)
            return False
        return True

    def validate_type(self, key: str, value: Any, expected_type: type, message: Optional[str] = None) -> bool:
        """
        Validate value type

        Args:
            key: Config key
            value: Config value
            expected_type: Expected type
            message: Custom error message

        Returns:
            bool: True if valid
        """
        if value is not None and not isinstance(value, expected_type):
            error_msg = message or f"Config '{key}' must be {expected_type.__name__}, got {type(value).__name__}"
            self.errors.append(error_msg)
            return False
        return True

    def validate_in_choices(self, key: str, value: Any, choices: List[Any], message: Optional[str] = None) -> bool:
        """
        Validate value is in allowed choices

        Args:
            key: Config key
            value: Config value
            choices: List of allowed values
            message: Custom error message

        Returns:
            bool: True if valid
        """
        if value is not None and value not in choices:
            error_msg = message or f"Config '{key}' must be one of {choices}, got '{value}'"
            self.errors.append(error_msg)
            return False
        return True

    def validate_path_exists(self, key: str, value: Any, must_be_file: bool = False, message: Optional[str] = None) -> bool:
        """
        Validate path exists

        Args:
            key: Config key
            value: Path value
            must_be_file: If True, path must be a file (not directory)
            message: Custom error message

        Returns:
            bool: True if valid
        """
        if value is None:
            return True  # Optional paths

        path = Path(value)
        if not path.exists():
            error_msg = message or f"Config '{key}' path does not exist: {value}"
            self.errors.append(error_msg)
            return False

        if must_be_file and not path.is_file():
            error_msg = message or f"Config '{key}' must be a file: {value}"
            self.errors.append(error_msg)
            return False

        return True

    def validate_custom(self, key: str, value: Any, validator: Callable[[Any], bool], message: str) -> bool:
        """
        Custom validation function

        Args:
            key: Config key
            value: Config value
            validator: Function that returns True if valid
            message: Error message if validation fails

        Returns:
            bool: True if valid
        """
        if value is not None and not validator(value):
            self.errors.append(f"Config '{key}': {message}")
            return False
        return True

    def warn_if(self, condition: bool, message: str):
        """
        Add a warning if condition is True

        Args:
            condition: Condition to check
            message: Warning message
        """
        if condition:
            self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if validation has errors"""
        return len(self.errors) > 0

    def get_errors(self) -> List[str]:
        """Get all validation errors"""
        return self.errors

    def get_warnings(self) -> List[str]:
        """Get all validation warnings"""
        return self.warnings

    def raise_if_invalid(self):
        """Raise ConfigValidationError if validation failed"""
        if self.has_errors():
            error_message = "\n".join([
                "Configuration validation failed:",
                *[f"  - {error}" for error in self.errors]
            ])
            raise ConfigValidationError(error_message)


def validate_app_config(config) -> ConfigValidator:
    """
    Validate app configuration

    Args:
        config: App config module

    Returns:
        ConfigValidator with validation results
    """
    validator = ConfigValidator()

    # Required fields
    validator.validate_required('app.APP_NAME', getattr(config, 'APP_NAME', None))
    validator.validate_required('app.APP_ENV', getattr(config, 'APP_ENV', None))

    # Type validation
    app_debug = getattr(config, 'APP_DEBUG', None)
    validator.validate_type('app.APP_DEBUG', app_debug, bool)

    # Environment validation
    app_env = getattr(config, 'APP_ENV', None)
    validator.validate_in_choices('app.APP_ENV', app_env, ['production', 'staging', 'development', 'testing', 'local'])

    # Warnings
    if app_env == 'production' and app_debug:
        validator.warn_if(True, "DEBUG mode is enabled in production (security risk)")

    return validator


def validate_database_config(config) -> ConfigValidator:
    """
    Validate database configuration

    Args:
        config: Database config module

    Returns:
        ConfigValidator with validation results
    """
    validator = ConfigValidator()

    # Database URL
    db_url = getattr(config, 'DATABASE_URL', None)
    validator.validate_required('database.DATABASE_URL', db_url)

    # Type validation
    validator.validate_type('database.DATABASE_URL', db_url, str)

    return validator


def validate_security_config(config) -> ConfigValidator:
    """
    Validate security configuration

    Args:
        config: Security config module

    Returns:
        ConfigValidator with validation results
    """
    validator = ConfigValidator()

    # Secret key (check SECRET_KEY or CSRF_SECRET)
    secret_key = getattr(config, 'SECRET_KEY', None)
    csrf_secret = getattr(config, 'CSRF_SECRET', None)

    # At least one secret should be configured
    if not secret_key and not csrf_secret:
        validator.errors.append("Either SECRET_KEY or CSRF_SECRET must be configured")

    # Validate SECRET_KEY if it exists
    if secret_key:
        validator.validate_type('security.SECRET_KEY', secret_key, str)
        validator.validate_custom(
            'security.SECRET_KEY',
            secret_key,
            lambda v: len(v) >= 32,
            "SECRET_KEY must be at least 32 characters"
        )

    # Validate CSRF_SECRET if it exists
    if csrf_secret:
        validator.validate_type('security.CSRF_SECRET', csrf_secret, str)
        validator.validate_custom(
            'security.CSRF_SECRET',
            csrf_secret,
            lambda v: len(v) >= 32,
            "CSRF_SECRET must be at least 32 characters"
        )

    # JWT keys
    jwt_private_key = getattr(config, 'JWT_PRIVATE_KEY_PATH', None)
    jwt_public_key = getattr(config, 'JWT_PUBLIC_KEY_PATH', None)

    if jwt_private_key:
        validator.validate_path_exists('security.JWT_PRIVATE_KEY_PATH', jwt_private_key, must_be_file=True)

    if jwt_public_key:
        validator.validate_path_exists('security.JWT_PUBLIC_KEY_PATH', jwt_public_key, must_be_file=True)

    # JWT algorithm
    jwt_algorithm = getattr(config, 'JWT_ALGORITHM', None)
    if jwt_algorithm:
        validator.validate_in_choices(
            'security.JWT_ALGORITHM',
            jwt_algorithm,
            ['RS256', 'RS384', 'RS512', 'HS256', 'HS384', 'HS512']
        )

    # Warnings
    app_env = os.getenv('APP_ENV', 'development')
    if app_env == 'production':
        if secret_key and secret_key == 'change-this-in-production':
            validator.warn_if(True, "SECRET_KEY appears to be a default value in production")
        if csrf_secret and csrf_secret == 'change-this-in-production':
            validator.warn_if(True, "CSRF_SECRET appears to be a default value in production")

    return validator


def validate_session_config(config) -> ConfigValidator:
    """
    Validate session configuration

    Args:
        config: Session config module

    Returns:
        ConfigValidator with validation results
    """
    validator = ConfigValidator()

    # Session lifetime
    lifetime = getattr(config, 'SESSION_LIFETIME', None)
    if lifetime:
        validator.validate_type('session.SESSION_LIFETIME', lifetime, int)
        validator.validate_custom(
            'session.SESSION_LIFETIME',
            lifetime,
            lambda v: v > 0,
            "SESSION_LIFETIME must be positive"
        )

    # Session driver
    driver = getattr(config, 'SESSION_DRIVER', None)
    if driver:
        validator.validate_in_choices(
            'session.SESSION_DRIVER',
            driver,
            ['cookie', 'file', 'redis', 'database']
        )

    return validator


# ============================================================================
# Configuration Validation
# ============================================================================

def validate_template_config():
    """Validate template configuration"""
    errors = []
    warnings = []

    # Validate SPA layout
    if BLADE_SPA_ENABLED and not BLADE_SPA_LAYOUT:
        errors.append("BLADE_SPA_LAYOUT cannot be empty when BLADE_SPA_ENABLED is True")

    if not BLADE_SPA_CONTENT_VARIABLE:
        errors.append("BLADE_SPA_CONTENT_VARIABLE cannot be empty")

    # Validate cache settings
    if BLADE_CACHE_STORAGE_TYPE not in ('disk', 'memory'):
        errors.append(f"BLADE_CACHE_STORAGE_TYPE must be 'disk' or 'memory', got '{BLADE_CACHE_STORAGE_TYPE}'")

    if BLADE_CACHE_MAX_SIZE < 1:
        errors.append(f"BLADE_CACHE_MAX_SIZE must be at least 1, got {BLADE_CACHE_MAX_SIZE}")

    if BLADE_CACHE_TTL < 0:
        errors.append(f"BLADE_CACHE_TTL must be non-negative, got {BLADE_CACHE_TTL}")

    # Validate file extension
    if BLADE_FILE_EXTENSION not in ('.html', '.blade.php'):
        warnings.append(f"BLADE_FILE_EXTENSION is '{BLADE_FILE_EXTENSION}', typically '.html' or '.blade.php'")

    # Security warnings
    if BLADE_ALLOW_PYTHON_BLOCKS:
        warnings.append("BLADE_ALLOW_PYTHON_BLOCKS is enabled - this may be a security risk")

    # Performance warnings
    if not BLADE_CACHE_ENABLED:
        warnings.append("BLADE_CACHE_ENABLED is False - this will significantly impact performance")

    if BLADE_CACHE_ENABLED and APP_ENV == 'production' and BLADE_CACHE_STORAGE_TYPE == 'memory':
        warnings.append("Using memory cache in production - consider disk cache for persistence")

    return errors, warnings

def validate_all_configs() -> Dict[str, ConfigValidator]:
    """
    Validate all configuration files

    Returns:
        Dict of config_name -> ConfigValidator

    Raises:
        ConfigValidationError: If any validation fails
    """
    from larasanic.support.config import Config

    validators = {}

    # Validate app config
    app_config = Config.all('app')
    if app_config:
        validators['app'] = validate_app_config(app_config)

    # Validate database config
    db_config = Config.all('database')
    if db_config:
        validators['database'] = validate_database_config(db_config)

    # Validate security config
    security_config = Config.all('security')
    if security_config:
        validators['security'] = validate_security_config(security_config)

    # Validate session config
    session_config = Config.all('session')
    if session_config:
        validators['session'] = validate_session_config(session_config)

    # Check for errors
    all_errors = []
    all_warnings = []

    for config_name, validator in validators.items():
        if validator.has_errors():
            all_errors.extend([f"[{config_name}] {error}" for error in validator.get_errors()])
        all_warnings.extend([f"[{config_name}] {warning}" for warning in validator.get_warnings()])

    # Raise if any errors
    if all_errors:
        error_message = "\n".join([
            "Configuration validation failed:",
            *[f"  - {error}" for error in all_errors]
        ])
        raise ConfigValidationError(error_message)

    # Log warnings
    if all_warnings:
        from larasanic.logging import getLogger
        logger = getLogger('config_validator')
        for warning in all_warnings:
            logger.warning(f"Config warning: {warning}")

    return validators
