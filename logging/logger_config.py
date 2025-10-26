"""
Logging Configuration
Provides structured logging with security features
"""
import logging
import logging.handlers
import json
import re
from typing import Dict, List, Optional
from datetime import datetime


class SensitiveDataFilter(logging.Filter):
    """
    Filter to redact sensitive data from logs
    Prevents password, token, API key, and other sensitive data leakage
    """

    SENSITIVE_PATTERNS = {
        # Password fields
        'password': r'("password"\s*:\s*)"[^"]*"',
        'passwd': r'("passwd"\s*:\s*)"[^"]*"',
        'pwd': r'("pwd"\s*:\s*)"[^"]*"',
        'password_hash': r'("password_hash"\s*:\s*)"[^"]*"',
        'password_confirmation': r'("password_confirmation"\s*:\s*)"[^"]*"',

        # API keys and tokens
        'api_key': r'("api_key"\s*:\s*)"[^"]*"',
        'api_secret': r'("api_secret"\s*:\s*)"[^"]*"',
        'token': r'("token"\s*:\s*)"[^"]*"',
        'access_token': r'("access_token"\s*:\s*)"[^"]*"',
        'refresh_token': r'("refresh_token"\s*:\s*)"[^"]*"',
        'bearer_token': r'("bearer_token"\s*:\s*)"[^"]*"',
        'jwt': r'("jwt"\s*:\s*)"[^"]*"',
        'secret': r'("secret"\s*:\s*)"[^"]*"',
        'secret_key': r'("secret_key"\s*:\s*)"[^"]*"',

        # Credit card numbers (basic pattern)
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',

        # SSN (US Social Security Number)
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',

        # Email in sensitive contexts
        'email_password': r'(email=.*&password=)[^&]*',

        # Authorization headers
        'auth_header': r'(Authorization:\s+Bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*',

        # Private keys
        'private_key': r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[\s\S]+?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
    }

    def __init__(self, additional_patterns: Optional[Dict[str, str]] = None):
        """
        Initialize sensitive data filter
        Args:
            additional_patterns: Additional regex patterns to filter (name: pattern)
        """
        super().__init__()
        self.patterns = self.SENSITIVE_PATTERNS.copy()
        if additional_patterns:
            self.patterns.update(additional_patterns)

        # Compile all patterns
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.patterns.items()
        }

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive data
        Returns:
            True (always pass the record, but with redacted content)
        """
        # Redact sensitive data from message
        if isinstance(record.msg, str):
            record.msg = self._redact_sensitive_data(record.msg)

        # Redact from args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._redact_sensitive_data(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._redact_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True

    def _redact_sensitive_data(self, text: str) -> str:
        """
        Redact sensitive data from text

        Returns:
            Text with sensitive data redacted
        """
        redacted = text

        for name, pattern in self.compiled_patterns.items():
            if name in ['password', 'passwd', 'pwd', 'password_hash', 'password_confirmation',
                       'api_key', 'api_secret', 'token', 'access_token', 'refresh_token',
                       'bearer_token', 'jwt', 'secret', 'secret_key']:
                # JSON field redaction
                redacted = pattern.sub(r'\1"[REDACTED]"', redacted)
            elif name == 'credit_card':
                # Redact credit card, keep last 4 digits
                def redact_cc(match):
                    cc = match.group(0).replace('-', '').replace(' ', '')
                    return f"****-****-****-{cc[-4:]}"
                redacted = pattern.sub(redact_cc, redacted)
            elif name == 'ssn':
                # Redact SSN
                redacted = pattern.sub('***-**-****', redacted)
            elif name == 'email_password':
                # Redact password from query string
                redacted = pattern.sub(r'\1[REDACTED]', redacted)
            elif name == 'auth_header':
                # Redact auth header
                redacted = pattern.sub(r'\1[REDACTED]', redacted)
            elif name == 'private_key':
                # Redact private keys
                redacted = pattern.sub('[REDACTED PRIVATE KEY]', redacted)

        return redacted


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging

    Outputs logs in JSON format for easy parsing and analysis
    """

    def __init__(self, include_fields: Optional[List[str]] = None):
        """
        Initialize JSON formatter

        Args:
            include_fields: Additional fields to include in JSON output
        """
        super().__init__()
        self.include_fields = include_fields or []

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON

        Args:
            record: Log record to format

        Returns:
            JSON formatted log string
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_data['stack'] = record.stack_info

        # Add custom fields
        for field in self.include_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add extra fields from record.__dict__
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                          'getMessage', 'message']:
                log_data[key] = value

        return json.dumps(log_data)


class LoggerConfig:
    """
    Centralized logging configuration
    """
    @staticmethod
    def setup_logger(
        name: str,
        format_type: str = 'json',
        max_bytes: int = None,
        backup_count: int = None,
        filter_sensitive: bool = True,
        additional_sensitive_patterns: Optional[Dict[str, str]] = None,
        file_name: Optional[str] = None
    ) -> logging.Logger:
        from larasanic.defaults import DEFAULT_LOG_MAX_BYTES, DEFAULT_LOG_BACKUP_COUNT
        if max_bytes is None:
            max_bytes = DEFAULT_LOG_MAX_BYTES
        if backup_count is None:
            backup_count = DEFAULT_LOG_BACKUP_COUNT
        """
        Setup a logger with rotation and optional sensitive data filtering

        Args:
            name: Logger name
            format_type: Format type ('json' or 'text')
            max_bytes: Max bytes before rotation (default: 10MB)
            backup_count: Number of backup files to keep
            filter_sensitive: Enable sensitive data filtering
            additional_sensitive_patterns: Additional patterns to filter

        Returns:
            Configured logger

        Example:
            logger = LoggerConfig.setup_logger(
                'security',
                Path('logs/security.log'),
                level=logging.WARNING,
                format_type='json',
                filter_sensitive=True
            )
        """
        from larasanic.support import Config, Storage
        
        # Get configuration
        app_env = Config.get('app.APP_ENV', 'local')
        app_debug = Config.get('app.APP_DEBUG', False)

        # Determine log level based on environment
        level = LoggerConfig.get_level_by_environment(app_env)
        enable_console = app_debug

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Clear existing handlers
        logger.handlers.clear()

        # Use file_name if provided, otherwise use logger name
        log_filename = file_name if file_name else name
        log_file = Storage.logs(f"{log_filename}.log")
        Storage.ensure_directory(log_file.parent)
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )

        # Set formatter
        if format_type == 'json':
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        handler.setFormatter(formatter)

        # Add sensitive data filter
        if filter_sensitive:
            sensitive_filter = SensitiveDataFilter(additional_sensitive_patterns)
            handler.addFilter(sensitive_filter)

        logger.addHandler(handler)

        # Add console handler if requested
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            if filter_sensitive:
                console_handler.addFilter(sensitive_filter)
            logger.addHandler(console_handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

        return logger

    @staticmethod
    def get_level_by_environment(environment: str) -> int:
        """
        Get logging level based on environment

        Args:
            environment: Environment name ('production', 'development', 'testing')

        Returns:
            Logging level
        """
        levels = {
            'production': logging.WARNING,
            'staging': logging.INFO,
            'development': logging.DEBUG,
            'testing': logging.ERROR,
        }
        return levels.get(environment.lower(), logging.INFO)
