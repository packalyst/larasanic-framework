"""
Compression Middleware
Compresses responses with gzip and minifies HTML
"""
from larasanic.middleware.base_middleware import Middleware
from sanic import Request
import gzip
import re
from io import BytesIO
from typing import Optional


class CompressionMiddleware(Middleware):
    """Middleware to compress responses with gzip and minify HTML"""

    # Configuration mapping for MiddlewareConfigMixin
    ENABLED_CONFIG_KEY = 'app.COMPRESSION_ENABLED'
    @staticmethod
    def _get_config_defaults():
        from larasanic.defaults import DEFAULT_COMPRESSION_MIN_SIZE, DEFAULT_COMPRESSION_LEVEL, DEFAULT_MINIFY_HTML
        return {
            'min_size': ('app.COMPRESSION_MIN_SIZE', DEFAULT_COMPRESSION_MIN_SIZE),
            'compression_level': ('app.COMPRESSION_LEVEL', DEFAULT_COMPRESSION_LEVEL),
            'minify_html': ('app.MINIFY_HTML', DEFAULT_MINIFY_HTML),
        }
    CONFIG_MAPPING = _get_config_defaults.__func__()
    DEFAULT_ENABLED = True

    def __init__(self, min_size: int = None, compression_level: int = None, minify_html: bool = None):
        """
        Initialize compression middleware
        """
        from larasanic.defaults import DEFAULT_COMPRESSION_MIN_SIZE, DEFAULT_COMPRESSION_LEVEL, DEFAULT_MINIFY_HTML
        self.min_size = min_size if min_size is not None else DEFAULT_COMPRESSION_MIN_SIZE
        self.compression_level = compression_level if compression_level is not None else DEFAULT_COMPRESSION_LEVEL
        self.minify_html = minify_html if minify_html is not None else DEFAULT_MINIFY_HTML

    async def before_request(self, request: Request):
        """No action needed before request"""
        return None

    async def after_response(self, request: Request, response):
        """No compression here - wait for after_build()"""
        return response

    async def after_build(self, request: Request, response):
        """Compress response AFTER ResponseBuilder is built"""
        # Now response is guaranteed to be HTTPResponse
        if not self._should_compress(request, response):
            return response

        content_type = self._get_content_type(response)

        # Get body as bytes
        body = self._get_body_bytes(response, content_type)
        if not body:
            return response

        # Minify HTML if applicable
        if self.minify_html and 'text/html' in content_type:
            try:
                html_str = body.decode('utf-8')
                html_str = self._minify_html(html_str)
                body = html_str.encode('utf-8')
            except (UnicodeDecodeError, AttributeError):
                pass  # Use original bytes

        # Compress with gzip
        compressed_body = self._compress_gzip(body)

        # Only use compression if it reduces size
        if len(compressed_body) < len(body):
            response.body = compressed_body
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Vary'] = 'Accept-Encoding'

            if 'Content-Length' in response.headers:
                response.headers['Content-Length'] = str(len(compressed_body))

        return response

    def _should_compress(self, request: Request, response) -> bool:
        """Determine if response should be compressed"""
        from larasanic.support.facades import HttpRequest
        # Check if client accepts gzip
        accept_encoding = HttpRequest.get_header('Accept-Encoding', '')
        if 'gzip' not in accept_encoding:
            return False

        # Don't compress if already compressed
        if response.headers.get('Content-Encoding'):
            return False

        content_type = self._get_content_type(response)

        compressible_types = [
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/json',
            'text/plain',
            'text/xml',
            'application/xml',
            'application/xhtml+xml',
            'image/svg+xml'
        ]

        if not any(ct in content_type for ct in compressible_types):
            return False

        # Check size
        if hasattr(response, 'body'):
            body_size = len(response.body) if isinstance(response.body, bytes) else len(str(response.body).encode('utf-8'))
            return body_size >= self.min_size

        return False

    def _get_content_type(self, response) -> str:
        """Extract content type from response"""
        content_type = response.headers.get('Content-Type', '')
        if not content_type:
            content_type = response.headers.get('content-type', '')

        # Extract just the MIME type
        if ';' in content_type:
            content_type = content_type.split(';')[0].strip()

        return content_type

    def _get_body_bytes(self, response, content_type: str) -> bytes:
        """Get response body as bytes"""
        if isinstance(response.body, bytes):
            return response.body
        elif isinstance(response.body, str):
            return response.body.encode('utf-8')
        return b''

    def _compress_gzip(self, body: bytes) -> bytes:
        """Compress body with gzip"""
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=self.compression_level) as gz:
            gz.write(body)
        return buffer.getvalue()

    def _minify_html(self, html: str) -> str:
        """Minify HTML to reduce size"""
        try:
            # Try using htmlmin if available
            import htmlmin
            return htmlmin.minify(
                html,
                remove_comments=True,
                remove_empty_space=True,
                reduce_empty_attributes=True,
                reduce_boolean_attributes=True,
                keep_pre=True,
            )
        except ImportError:
            # Fallback to regex minification
            # Remove HTML comments
            html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

            # Remove excess whitespace
            html = re.sub(r'[\n\r\t]+', ' ', html)
            html = re.sub(r'\s{2,}', ' ', html)
            html = re.sub(r'>\s+<', '><', html)

            # Remove whitespace around =
            html = re.sub(r'\s*=\s*', '=', html)

            return html.strip()
