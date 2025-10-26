"""
Security Logger Middleware
Logs suspicious and malformed requests with structured logging
"""
from larasanic.middleware.base_middleware import Middleware
from larasanic.logging import LoggerConfig
from larasanic.support.facades import HttpRequest
from sanic import Request
import json
import logging
import re
from datetime import datetime
from larasanic.logging import getLogger
from typing import Optional

class SecurityLoggerMiddleware(Middleware):
    """Middleware to log suspicious and malformed requests"""

    # Configuration for automatic registration
    ENABLED_CONFIG_KEY = 'app.SECURITY_LOGGING_ENABLED'
    DEFAULT_ENABLED = True

    SUSPICIOUS_PATTERNS = [
        r'\.\./',  # Directory traversal
        r'<script',  # XSS attempts
        r'union.*select',  # SQL injection
        r'eval\(',  # Code injection
        r'base64_decode',  # Encoded payloads
        r'phpinfo',  # PHP probing
        r'wp-admin',  # WordPress scanning
        r'\.env',  # Environment file access
        r'\.git',  # Git directory access
        r'admin',  # Admin panel probing
        r'proxy',  # Proxy testing
    ]

    def __init__(self):
        """
        Initialize security logger with structured logging
        """
        self.pattern = re.compile('|'.join(self.SUSPICIOUS_PATTERNS), re.IGNORECASE)

    async def before_request(self, request: Request):
        """Check for suspicious patterns before processing"""
        return None

    async def after_response(self, request: Request, response):
        """Log suspicious requests after processing"""
        client_ip = HttpRequest.client_ip()
        full_url = str(HttpRequest.url())
        # Check for suspicious patterns
        is_suspicious = False
        matched_pattern = None

        if self.pattern.search(full_url):
            is_suspicious = True
            matched_pattern = self.pattern.search(full_url).group(0)

        # Check headers for suspicious content
        suspicious_headers = {}
        for header, value in HttpRequest.get_headers():
            if header.lower() in ['host', 'user-agent', 'referer']:
                if self.pattern.search(str(value)):
                    is_suspicious = True
                    suspicious_headers[header] = value
        
        # Log suspicious requests
        if is_suspicious:
            # JSONFormatter will handle serialization, pass message and extra data
            getLogger('security').warning(
                f"Suspicious request detected",
                extra={
                    'ip': client_ip,
                    'method': HttpRequest.method(),
                    'path': HttpRequest.path(),
                    'full_url': full_url,
                    'matched_pattern': matched_pattern,
                    'suspicious_headers': suspicious_headers,
                    'user_agent': HttpRequest.user_agent(),
                    'referer': HttpRequest.referer() or 'None',
                    'status_code': response.status if response else None
                }
            )

        # Log malformed requests (400 errors)
        if response and response.status == 400:
            getLogger('malformed').info(
                "Malformed request received",
                extra={
                    'ip': client_ip,
                    'method': HttpRequest.method(),
                    'url': full_url,
                    'user_agent': HttpRequest.user_agent(),
                    'error': 'Bad Request'
                }
            )

        return response
