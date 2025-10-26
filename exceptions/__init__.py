"""
Exceptions Package
Centralized error handling and reporting
"""
from larasanic.exceptions.error_handler import ErrorHandler
from larasanic.exceptions.cli_formatter import CliColors, CliBox, _colorize, _box_line, _format_traceback
from larasanic.exceptions.cli_exception import install_cli_error_handler, handle_cli_exceptions
from larasanic.exceptions.custom import (
    FrameworkException,
    ValidationException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    BadRequestException,
    ConflictException,
    TooManyRequestsException,
    ServiceUnavailableException,
)

__all__ = [
    # Error handling
    'ErrorHandler',

    # CLI formatting
    'CliColors',
    'CliBox',
    '_colorize',
    '_box_line',
    '_format_traceback',
    'install_cli_error_handler',
    'handle_cli_exceptions',

    # Custom exceptions
    'FrameworkException',
    'ValidationException',
    'NotFoundException',
    'UnauthorizedException',
    'ForbiddenException',
    'BadRequestException',
    'ConflictException',
    'TooManyRequestsException',
    'ServiceUnavailableException',
]
