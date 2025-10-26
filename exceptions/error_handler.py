"""
Centralized Error Handler
"""
from larasanic.logging import getLogger
from larasanic.http import ResponseHelper
import traceback
from typing import Optional, Dict, Any
from sanic import Request
from sanic.exceptions import SanicException

class ErrorHandler:
    """
    Provides standardized JSON error responses and error reporting
    """
    def __init__(self,debug: bool = False,include_trace: bool = False):
        """
        Initialize error handler
        Args:
            debug: Enable debug mode (include stack traces)
            include_trace: Include stack trace in error response (only in debug)
        """
        self.debug = debug
        self.include_trace = include_trace and debug
        self.logger = getLogger('application')

    async def handle_error(self,request: Request,error: Exception):
        """
        Handle error and return consistent JSON response
        """
        # Build error response
        response_data = self._build_error_response(error, request)

        # Determine status code
        status_code = self._get_status_code(error)

        # Log error
        self._log_error(error, request, status_code)

        try:
            from larasanic.helpers import view
            from larasanic.support import Config
            from larasanic.support.facades import TemplateBlade

            error_view = f"{Config.get('template.BLADE_VIEW_CONFIG.error_template_prefix')}.{status_code}"
            if TemplateBlade.view_exists(error_view):
                # Return view response builder for errors page
                return view(error_view, {
                    'message': response_data['error']['message'],
                    'path': request.path
                }).status(status_code)
            else:
                # Return standardized error response
                return ResponseHelper.error(
                    message=response_data['error']['message'],
                    errors=response_data.get('error', {}).get('errors'),
                    status=status_code,
                    code=response_data.get('error', {}).get('code')
                )
        except Exception:
            pass

        # Return standardized error response
        return ResponseHelper.error(
            message=response_data['error']['message'],
            errors=response_data.get('error', {}).get('errors'),
            status=status_code,
            code=response_data.get('error', {}).get('code')
        )

    def _build_error_response(
        self,
        error: Exception,
        request: Request
    ) -> Dict[str, Any]:
        """
        Build standardized error response
        Returns:
            Error response dictionary
        """
        error_type = error.__class__.__name__

        # Base response
        response = {
            'error': {
                'type': error_type,
                'message': self._get_error_message(error),
            }
        }

        # Add error code if available
        if hasattr(error, 'error_code'):
            response['error']['code'] = error.error_code

        # Add validation errors if available
        if hasattr(error, 'errors'):
            response['error']['errors'] = error.errors

        # Add stack trace in debug mode
        if self.include_trace:
            response['error']['trace'] = traceback.format_exc().split('\n')

        # Add request info in debug mode
        if self.debug:
            response['debug'] = {
                'path': request.path,
                'method': request.method,
                'url': str(request.url),
            }

        return response

    def _get_error_message(self, error: Exception) -> str:
        """
        Get user-friendly error message
        """
        # For Sanic exceptions, use their message
        if isinstance(error, SanicException):
            return str(error)

        # For validation exceptions
        if hasattr(error, 'message'):
            return error.message

        # Default message in production (don't expose internals)
        if not self.debug:
            return "An error occurred while processing your request"

        # In debug, show actual error
        return str(error)

    def _get_status_code(self, error: Exception) -> int:
        """
        Determine HTTP status code from error
        """
        # Sanic exceptions have status_code
        if isinstance(error, SanicException):
            return error.status_code

        # Custom exceptions with status_code attribute
        if hasattr(error, 'status_code'):
            return error.status_code

        # Validation errors
        if error.__class__.__name__ == 'ValidationException':
            return 422

        # Authentication/Authorization errors
        if error.__class__.__name__ in ['Unauthorized', 'AuthenticationException']:
            return 401

        if error.__class__.__name__ in ['Forbidden', 'AuthorizationException']:
            return 403

        # Not found errors
        if error.__class__.__name__ in ['NotFound', 'NotFoundException']:
            return 404

        # Default to 500 Internal Server Error
        return 500

    def _log_error(
        self,
        error: Exception,
        request: Request,
        status_code: int
    ):
        """
        Log error with context
        """
        log_data = {
            'error_type': error.__class__.__name__,
            'error_message': str(error),
            'status_code': status_code,
            'method': request.method,
            'path': request.path,
            'url': str(request.url),
        }

        # Log at appropriate level
        if status_code >= 500:
            self.logger.error(
                f"{status_code} Error: {error.__class__.__name__}",
                extra=log_data,
                exc_info=True
            )
        elif status_code >= 400:
            self.logger.warning(
                f"{status_code} Error: {error.__class__.__name__}",
                extra=log_data
            )
        else:
            self.logger.info(
                f"{status_code} Response",
                extra=log_data
            )
