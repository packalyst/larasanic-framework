"""
Custom Exception Classes
Framework-specific exceptions with HTTP status codes
"""
from typing import Optional, Dict, Any


class FrameworkException(Exception):
    """Base exception for all framework exceptions"""
    status_code = 500
    message = "An error occurred"

    def __init__(self, message: Optional[str] = None, status_code: Optional[int] = None):
        self.message = message or self.__class__.message
        self.status_code = status_code or self.__class__.status_code
        super().__init__(self.message)


class ValidationException(FrameworkException):
    """
    Validation error exception

    Raised when request validation fails

    Example:
        raise ValidationException("Email is required", errors={'email': 'required'})
    """
    status_code = 422
    message = "Validation failed"

    def __init__(
        self,
        message: Optional[str] = None,
        errors: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None
    ):
        super().__init__(message, status_code)
        self.errors = errors or {}


class NotFoundException(FrameworkException):
    """
    Resource not found exception

    Raised when a requested resource doesn't exist

    Example:
        raise NotFoundException("User not found")
    """
    status_code = 404
    message = "Resource not found"


class UnauthorizedException(FrameworkException):
    """
    Unauthorized exception

    Raised when authentication is required but not provided

    Example:
        raise UnauthorizedException("Please log in")
    """
    status_code = 401
    message = "Authentication required"


class ForbiddenException(FrameworkException):
    """
    Forbidden exception

    Raised when user doesn't have permission to access resource

    Example:
        raise ForbiddenException("You don't have permission to edit this resource")
    """
    status_code = 403
    message = "Access forbidden"


class BadRequestException(FrameworkException):
    """
    Bad request exception

    Raised when request is malformed or invalid

    Example:
        raise BadRequestException("Invalid JSON payload")
    """
    status_code = 400
    message = "Bad request"


class ConflictException(FrameworkException):
    """
    Conflict exception

    Raised when request conflicts with current state

    Example:
        raise ConflictException("Email already exists")
    """
    status_code = 409
    message = "Resource conflict"


class TooManyRequestsException(FrameworkException):
    """
    Too many requests exception

    Raised when rate limit is exceeded

    Example:
        raise TooManyRequestsException("Rate limit exceeded, try again later")
    """
    status_code = 429
    message = "Too many requests"


class ServiceUnavailableException(FrameworkException):
    """
    Service unavailable exception

    Raised when service is temporarily unavailable

    Example:
        raise ServiceUnavailableException("Database connection lost")
    """
    status_code = 503
    message = "Service temporarily unavailable"