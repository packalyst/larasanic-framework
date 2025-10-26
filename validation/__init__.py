"""
Validation Package
Laravel-style validation for Sanic framework
"""
from larasanic.validation.validator import Validator, validate
from larasanic.validation.validate_app import ValidateApp
from larasanic.validation.exceptions import ValidationException
from larasanic.validation.form_request import FormRequest
from larasanic.validation.rules import (
    ValidationRule,
    Required, Email, Min, Max, String, Integer, Numeric, Boolean,
    Regex, In, NotIn, Confirmed, Same, Different, Url, Date,
    Alpha, AlphaNum, AlphaDash, Array, Json
)
from larasanic.validation.database_rules import Unique, Exists
from larasanic.validation.file_rules import (
    File, Image, Mimes, MimeTypes,
    MaxFileSize, MinFileSize, Dimensions
)
# Import helpers
from larasanic.validation.helpers import (
    quick_validate, check_validation, validate_field,
    validate_email, validate_password, validate_url, validate_username,
    validate_phone, validate_required_fields,
    validate_pagination, validate_date_range, validate_search_query
)

__all__ = [
    # Core
    'Validator',
    'validate',
    'ValidationException',
    'FormRequest',
    'ValidateApp',
    # Base
    'ValidationRule',
    # Basic rules
    'Required',
    'Email',
    'Min',
    'Max',
    'String',
    'Integer',
    'Numeric',
    'Boolean',
    'Regex',
    'In',
    'NotIn',
    'Confirmed',
    'Same',
    'Different',
    'Url',
    'Date',
    'Alpha',
    'AlphaNum',
    'AlphaDash',
    'Array',
    'Json',
    # Database rules
    'Unique',
    'Exists',
    # File rules
    'File',
    'Image',
    'Mimes',
    'MimeTypes',
    'MaxFileSize',
    'MinFileSize',
    'Dimensions',
    # Helpers
    'quick_validate',
    'check_validation',
    'validate_field',
    'validate_email',
    'validate_password',
    'validate_url',
    'validate_username',
    'validate_phone',
    'validate_required_fields',
    'validate_pagination',
    'validate_date_range',
    'validate_search_query',
]
