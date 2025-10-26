"""
Logging Service Provider
Initializes application-wide structured logging
"""
import logging
from larasanic.service_provider import ServiceProvider
from larasanic.logging.logger_config import LoggerConfig
from larasanic.support import Config

class LoggingServiceProvider(ServiceProvider):
    """Logging service provider - sets up structured logging"""

    def register(self):
        """Register logging services"""
        self.setup_application_logger()
        pass

    def boot(self):
        """Bootstrap logging services"""
        pass

    def setup_application_logger(self):
        """
        Setup application-wide structured logger from config
        """
        # Get allowed logging handlers from config
        allowed_handlers = Config.get('app.ALLOWED_LOGGING_HANDLERS', {})

        # Setup each configured logger
        for handler_key, handler_config in allowed_handlers.items():
            LoggerConfig.setup_logger(
                name=handler_config.get('name'),
                filter_sensitive=handler_config.get('filter_sensitive', True),
                file_name=handler_config.get('file_name')
            )

        # Prevent Sanic's loggers from propagating to our root logger
        # This preserves Sanic's nice console output
        import logging
        sanic_loggers = ['sanic.root', 'sanic.error', 'sanic.access', 'sanic.server']
        for logger_name in sanic_loggers:
            logger = logging.getLogger(logger_name)
            logger.propagate = False