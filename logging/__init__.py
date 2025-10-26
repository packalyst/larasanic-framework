"""
Logging Package
Structured logging with security features

Provides drop-in replacement for standard logging that uses
structured JSON logging with sensitive data filtering.
"""
from larasanic.logging.logger_config import (
    LoggerConfig,
    JSONFormatter,
    SensitiveDataFilter
)
import logging
from typing import Optional

__all__ = [
    'LoggerConfig',
    'JSONFormatter',
    'SensitiveDataFilter',
    'getLogger',
    'INFO',
    'DEBUG',
    'WARNING',
    'ERROR',
    'CRITICAL',
]

# Export logging levels for convenience
INFO = logging.INFO
DEBUG = logging.DEBUG
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


def getLogger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance (drop-in replacement for logging.getLogger)

    Uses structured logging automatically if the logger has been
    configured by LoggingServiceProvider. Falls back gracefully
    to standard logging if not yet initialized.

    Only allows logger names that are:
    - None (root logger)
    - Configured in ALLOWED_LOGGING_HANDLERS (e.g., 'application', 'security', 'malformed')
    - Module-based names (containing '.') like 'app.services.analysis'

    Args:
        name: Logger name (uses calling module if None)

    Returns:
        Logger instance with structured logging if configured

    Example:
        # Instead of:
        import logging
        logger = logging.getLogger(__name__)

        # Use:
        from larasanic.logging import getLogger
        logger = getLogger(__name__)

        # Both work the same way:
        logger.info("Something happened")
        logger.error("Error occurred", exc_info=True)
        logger.warning("Warning message", extra={'user_id': 123})
    """
    # Allow Sanic's own loggers to bypass our restriction
    if name and name.startswith('sanic.'):
        return logging.getLogger(name)

    # Allow None (root logger) or module-based names (containing '.')
    if name is not None and '.' not in name:
        # Check if it's a specially allowed logger name
        from larasanic.support import Config
        allowed_handlers = Config.get('app.ALLOWED_LOGGING_HANDLERS', {})

        # Extract allowed logger names (excluding root which is None)
        allowed_names = [
            handler_config.get('name')
            for handler_config in allowed_handlers.values()
            if handler_config.get('name') is not None
        ]

        if name not in allowed_names:
            # Force arbitrary names to use root logger
            name = None

    # Use standard logging.getLogger
    # If LoggingServiceProvider configured it, it will have our handlers
    # If not configured yet, it will use root logger (graceful fallback)
    return logging.getLogger(name)