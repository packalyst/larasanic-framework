"""
Response Helpers
Standardized response utilities for consistent API responses
All methods return ResponseBuilder for fluent interface
"""
from sanic.response import (
    file as sanic_file,
    file_stream as sanic_file_stream,
)
from typing import Any, Dict, Optional, Union, AsyncIterable
from pathlib import Path

class ResponseHelper:
    """
    Response helper for consistent JSON and HTML responses

    All methods return ResponseBuilder for fluent interface and method chaining.
    Supports both JSON API responses and HTML web responses with consistent structure.

    Example:
        # Success response with chaining
        return ResponseHelper.success({'user': user_data}) \
            .header('X-Custom', 'value') \
            .cookie('session', 'abc123')

        # Error response with chaining
        return ResponseHelper.error('Validation failed', {'email': 'Invalid'}, 422) \
            .header('X-Error-Code', 'VALIDATION_ERROR')

        # Redirect with cookie clearing
        return ResponseHelper.redirect('/dashboard') \
            .without_cookie('temp_token')

        # HTML with headers
        return ResponseHelper.html('<h1>Hello</h1>') \
            .header('X-Powered-By', 'MyFramework')
    """

    @staticmethod
    def success(
        data: Any = None,
        message: Optional[str] = None,
        status: int = 200,
        meta: Optional[Dict[str, Any]] = None
    ):
        """
        Return success response builder (chainable)

        Args:
            data: Response data
            message: Success message
            status: HTTP status code (default 200)
            meta: Additional metadata

        Returns:
            ResponseBuilder for chaining

        Example:
            return ResponseHelper.success({'user': user}, 'User created', 201) \
                .header('X-Resource-Id', str(user.id)) \
                .cookie('session', session_id)
        """
        from larasanic.support.facades.http_response import ResponseBuilder

        return ResponseBuilder(data) \
            .with_meta('success', True) \
            .with_meta('message', message) \
            .with_meta('meta', meta) \
            .status(status)

    @staticmethod
    def error(
        message: str,
        errors: Optional[Union[Dict[str, Any], list]] = None,
        status: int = 400,
        code: Optional[str] = None
    ):
        """
        Return error response builder (chainable)

        Args:
            message: Error message
            errors: Error details (dict or list)
            status: int = 400
            code: Error code for client handling

        Returns:
            ResponseBuilder for chaining

        Example:
            return ResponseHelper.error(
                'Validation failed',
                {'email': ['Email is required']},
                422
            ).header('X-Error-Code', 'VALIDATION_ERROR')
        """
        from larasanic.support.facades.http_response import ResponseBuilder

        return ResponseBuilder(message) \
            .with_meta('success', False) \
            .with_meta('errors', errors) \
            .with_meta('code', code) \
            .status(status)

    @staticmethod
    def redirect(url: str, status: int = 302):
        from larasanic.support.facades.http_response import ResponseBuilder
        return ResponseBuilder(url).type('redirect').status(status)

    @staticmethod
    def created(data: Any = None, message: str = 'Resource created successfully'):
        """
        Return 201 Created response builder

        Args:
            data: Created resource data
            message: Success message

        Returns:
            ResponseBuilder with 201 status

        Example:
            return ResponseHelper.created({'id': 1, 'name': 'John'}) \
                .header('Location', f'/users/{user.id}')
        """
        return ResponseHelper.success(data, message, status=201)

    @staticmethod
    def no_content():
        """
        Return 204 No Content response builder

        Returns:
            ResponseBuilder with 204 status

        Example:
            # After successful deletion
            return ResponseHelper.no_content()
        """
        from larasanic.support.facades.http_response import ResponseBuilder
        return ResponseBuilder({}).status(204)

    @staticmethod
    def unauthorized(message: str = 'Unauthorized'):
        """
        Return 401 Unauthorized response builder

        Args:
            message: Error message

        Returns:
            ResponseBuilder with 401 status

        Example:
            return ResponseHelper.unauthorized('Invalid credentials') \
                .header('WWW-Authenticate', 'Bearer')
        """
        return ResponseHelper.error(message, status=401, code='UNAUTHORIZED')

    @staticmethod
    def forbidden(message: str = 'Forbidden'):
        """
        Return 403 Forbidden response builder

        Args:
            message: Error message

        Returns:
            ResponseBuilder with 403 status

        Example:
            return ResponseHelper.forbidden('Insufficient permissions')
        """
        return ResponseHelper.error(message, status=403, code='FORBIDDEN')

    @staticmethod
    def limitexceded(message: str = 'Too many requests'):
        """
        Return 429 RATE_LIMIT_EXCEEDED response builder

        Args:
            message: Error message

        Returns:
            ResponseBuilder with 429 status

        Example:
            return ResponseHelper.limitexceded() \
                .header('Retry-After', '3600')
        """
        return ResponseHelper.error(message, status=429, code='RATE_LIMIT_EXCEEDED')

    @staticmethod
    def bad_request(message: str = 'Bad Request'):
        """
        Return 400 BAD_REQUEST response builder

        Args:
            message: Error message

        Returns:
            ResponseBuilder with 400 status

        Example:
            return ResponseHelper.bad_request('Invalid request format')
        """
        return ResponseHelper.error(message, status=400, code='BAD_REQUEST')

    @staticmethod
    def not_found(message: str = 'Resource not found'):
        """
        Return 404 Not Found response builder

        Args:
            message: Error message

        Returns:
            ResponseBuilder with 404 status

        Example:
            return ResponseHelper.not_found('User not found')
        """
        return ResponseHelper.error(message, status=404, code='NOT_FOUND')

    @staticmethod
    def validation_error(errors: Dict[str, Any], message: str = 'Validation failed'):
        """
        Return 422 Validation Error response builder

        Args:
            errors: Validation errors dictionary
            message: Error message

        Returns:
            ResponseBuilder with 422 status

        Example:
            return ResponseHelper.validation_error({
                'email': ['Email is required'],
                'password': ['Password must be at least 8 characters']
            })
        """
        return ResponseHelper.error(message, errors, status=422, code='VALIDATION_ERROR')

    @staticmethod
    def server_error(message: str = 'Internal server error'):
        """
        Return 500 Server Error response builder

        Args:
            message: Error message

        Returns:
            ResponseBuilder with 500 status

        Example:
            return ResponseHelper.server_error('Database connection failed')
        """
        return ResponseHelper.error(message, status=500, code='SERVER_ERROR')

    @staticmethod
    def paginated(
        data: list,
        total: int,
        page: int = 1,
        per_page: int = 15,
        message: Optional[str] = None
    ):
        """
        Return paginated response builder with metadata

        Args:
            data: List of items for current page
            total: Total number of items
            page: Current page number
            per_page: Items per page
            message: Optional success message

        Returns:
            ResponseBuilder with pagination metadata

        Example:
            users = await User.all().limit(15).offset(0)
            total = await User.all().count()
            return ResponseHelper.paginated(users, total, page=1, per_page=15)
        """
        total_pages = (total + per_page - 1) // per_page

        meta = {
            'pagination': {
                'total': total,
                'per_page': per_page,
                'current_page': page,
                'total_pages': total_pages,
                'has_more': page < total_pages,
            }
        }

        return ResponseHelper.success(data, message, meta=meta)

    # ============================================================================
    # HTML, Text, and Raw Responses
    # ============================================================================

    @staticmethod
    def html(
        body: str,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Return HTML response builder (chainable)

        Args:
            body: HTML content
            status: HTTP status code
            headers: Additional headers

        Returns:
            ResponseBuilder for chaining

        Example:
            return ResponseHelper.html('<h1>Hello World</h1>') \
                .header('X-Custom', 'value') \
                .cookie('visited', 'true')
        """
        from larasanic.support.facades.http_response import ResponseBuilder

        builder = ResponseBuilder(body).type('html').status(status)
        if headers:
            builder.headers(headers)
        return builder

    @staticmethod
    def text(
        body: str,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Return plain text response builder (chainable)

        Args:
            body: Text content
            status: HTTP status code
            headers: Additional headers

        Returns:
            ResponseBuilder for chaining

        Example:
            return ResponseHelper.text('Hello World') \
                .cookie('visited', 'true')
        """
        from larasanic.support.facades.http_response import ResponseBuilder

        builder = ResponseBuilder(body).type('text').status(status)
        if headers:
            builder.headers(headers)
        return builder

    @staticmethod
    def raw(
        body: bytes,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content_type: str = 'application/octet-stream'
    ):
        """
        Return raw bytes response builder (chainable)

        Args:
            body: Raw bytes content
            status: HTTP status code
            headers: Additional headers
            content_type: Content-Type header

        Returns:
            ResponseBuilder for chaining

        Example:
            return ResponseHelper.raw(b'Binary data', content_type='application/pdf') \
                .header('Content-Disposition', 'attachment')
        """
        from larasanic.support.facades.http_response import ResponseBuilder

        builder = ResponseBuilder(body).type('raw').status(status).header('Content-Type', content_type)
        if headers:
            builder.headers(headers)
        return builder

    @staticmethod
    def empty(status: int = 204, headers: Optional[Dict[str, str]] = None):
        """
        Return empty response builder (no content)

        Args:
            status: HTTP status code (default 204)
            headers: Additional headers

        Returns:
            ResponseBuilder for chaining

        Example:
            return ResponseHelper.empty() \
                .header('X-Request-Id', request_id)
        """
        from larasanic.support.facades.http_response import ResponseBuilder

        builder = ResponseBuilder('').type('text').status(status)
        if headers:
            builder.headers(headers)
        return builder

    # ============================================================================
    # File Responses (Direct HTTPResponse - not chainable)
    # ============================================================================

    # Note: File responses return direct HTTPResponse because they need special handling
    # and file operations are not typically chained with cookies/headers in the same way

    @staticmethod
    async def file(
        location: Union[str, Path],
        status: int = 200,
        mime_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        filename: Optional[str] = None,
        request_headers: Optional[Any] = None
    ):
        """
        Return file download response (direct HTTPResponse)

        Automatically handles HTTP Range requests for seeking in audio/video files.

        Args:
            location: Path to file
            status: HTTP status code
            mime_type: MIME type (auto-detected if None)
            headers: Additional headers
            filename: Download filename (uses file name if None)
            request_headers: Request headers (for Range request support)

        Returns:
            Sanic file response (supports Range requests)

        Example:
            return await ResponseHelper.file('/path/to/file.pdf')
            return await ResponseHelper.file('/path/to/audio.mp3', request_headers=request.headers)
        """
        return await sanic_file(
            location=str(location),
            status=status,
            mime_type=mime_type,
            headers=headers,
            filename=filename,
            request_headers=request_headers
        )

    @staticmethod
    async def download(
        location: Union[str, Path],
        filename: Optional[str] = None,
        mime_type: Optional[str] = None
    ):
        """
        Return file download response with forced download (direct HTTPResponse)

        Args:
            location: Path to file
            filename: Download filename
            mime_type: MIME type

        Returns:
            Sanic file response with Content-Disposition: attachment

        Example:
            return await ResponseHelper.download('/path/to/file.pdf', 'report.pdf')
        """
        headers = {
            'Content-Disposition': f'attachment; filename="{filename or Path(location).name}"'
        }

        return await sanic_file(
            location=str(location),
            mime_type=mime_type,
            headers=headers
        )

    @staticmethod
    async def stream(
        streaming_fn: AsyncIterable,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content_type: str = 'text/plain; charset=utf-8'
    ):
        """
        Return streaming response (direct HTTPResponse)

        Args:
            streaming_fn: Async generator that yields chunks
            status: HTTP status code
            headers: Additional headers
            content_type: Content-Type header

        Returns:
            Sanic streaming response

        Example:
            async def generate():
                for i in range(10):
                    yield f"Line {i}\n".encode()
                    await asyncio.sleep(0.1)

            return await ResponseHelper.stream(generate())
        """
        return await sanic_file_stream(
            streaming_fn,
            status=status,
            headers=headers,
            content_type=content_type
        )