"""
Validation Rules
Built-in validation rules (Laravel-style)
"""
import re
from typing import Any, Optional, List
from datetime import datetime
import mimetypes


class ValidationRule:
    """Base class for validation rules"""

    def __init__(self, *args):
        """Initialize rule with parameters"""
        self.parameters = args

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        """
        Validate the value

        Args:
            field: Field name
            value: Value to validate
            data: All form data

        Returns:
            Tuple of (is_valid, error_message)
        """
        raise NotImplementedError("Subclasses must implement validate()")

    def message(self, field: str) -> str:
        """
        Get error message

        Args:
            field: Field name

        Returns:
            Error message
        """
        return f"The {field} field is invalid."


class Required(ValidationRule):
    """Field is required"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '' or (isinstance(value, (list, dict)) and len(value) == 0):
            return False, self.message(field)
        return True, None

    def message(self, field: str) -> str:
        return f"The {field} field is required."


class Email(ValidationRule):
    """Field must be a valid email"""

    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None  # Use 'required' rule for required fields

        if not isinstance(value, str):
            return False, self.message(field)

        if not self.EMAIL_REGEX.match(value):
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must be a valid email address."


class Min(ValidationRule):
    """Field must be at least N (string length or numeric value)"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        min_val = self.parameters[0]

        if isinstance(value, str):
            if len(value) < min_val:
                return False, self.message(field)
        elif isinstance(value, (int, float)):
            if value < min_val:
                return False, self.message(field)
        elif isinstance(value, (list, dict)):
            if len(value) < min_val:
                return False, self.message(field)
        else:
            return False, f"The {field} field must be a string, number, list, or dict."

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must be at least {self.parameters[0]}."


class Max(ValidationRule):
    """Field must be at most N (string length or numeric value)"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        max_val = self.parameters[0]

        if isinstance(value, str):
            if len(value) > max_val:
                return False, self.message(field)
        elif isinstance(value, (int, float)):
            if value > max_val:
                return False, self.message(field)
        elif isinstance(value, (list, dict)):
            if len(value) > max_val:
                return False, self.message(field)
        else:
            return False, f"The {field} field must be a string, number, list, or dict."

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must not be greater than {self.parameters[0]}."


class String(ValidationRule):
    """Field must be a string"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if not isinstance(value, str):
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must be a string."


class Integer(ValidationRule):
    """Field must be an integer"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if isinstance(value, bool):
            return False, self.message(field)

        if isinstance(value, int):
            return True, None

        if isinstance(value, str):
            try:
                int(value)
                return True, None
            except ValueError:
                return False, self.message(field)

        return False, self.message(field)

    def message(self, field: str) -> str:
        return f"The {field} must be an integer."


class Numeric(ValidationRule):
    """Field must be numeric (int or float)"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if isinstance(value, bool):
            return False, self.message(field)

        if isinstance(value, (int, float)):
            return True, None

        if isinstance(value, str):
            try:
                float(value)
                return True, None
            except ValueError:
                return False, self.message(field)

        return False, self.message(field)

    def message(self, field: str) -> str:
        return f"The {field} must be a number."


class Boolean(ValidationRule):
    """Field must be boolean (or boolean-like)"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if isinstance(value, bool):
            return True, None

        if isinstance(value, str):
            if value.lower() in ('true', 'false', '1', '0', 'yes', 'no'):
                return True, None

        if isinstance(value, int):
            if value in (0, 1):
                return True, None

        return False, self.message(field)

    def message(self, field: str) -> str:
        return f"The {field} must be true or false."


class Regex(ValidationRule):
    """Field must match regex pattern"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if not isinstance(value, str):
            return False, f"The {field} must be a string to match pattern."

        pattern = self.parameters[0]
        if not re.match(pattern, value):
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} format is invalid."


class In(ValidationRule):
    """Field must be in list of allowed values"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        allowed = self.parameters
        if value not in allowed:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        allowed_str = ', '.join(str(v) for v in self.parameters)
        return f"The {field} must be one of: {allowed_str}."


class NotIn(ValidationRule):
    """Field must not be in list of disallowed values"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        disallowed = self.parameters
        if value in disallowed:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        disallowed_str = ', '.join(str(v) for v in self.parameters)
        return f"The {field} must not be one of: {disallowed_str}."


class Confirmed(ValidationRule):
    """Field must have matching confirmation field (e.g., password_confirmation)"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        confirmation_field = f"{field}_confirmation"
        confirmation_value = data.get(confirmation_field)

        if value != confirmation_value:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} confirmation does not match."


class Same(ValidationRule):
    """Field must match another field"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        other_field = self.parameters[0]
        other_value = data.get(other_field)

        if value != other_value:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must match {self.parameters[0]}."


class Different(ValidationRule):
    """Field must be different from another field"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        other_field = self.parameters[0]
        other_value = data.get(other_field)

        if value == other_value:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must be different from {self.parameters[0]}."


class Url(ValidationRule):
    """Field must be a valid URL"""

    URL_REGEX = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if not isinstance(value, str):
            return False, self.message(field)

        if not self.URL_REGEX.match(value):
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must be a valid URL."


class Date(ValidationRule):
    """Field must be a valid date"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if isinstance(value, datetime):
            return True, None

        if isinstance(value, str):
            try:
                # Try ISO format first
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True, None
            except ValueError:
                # Try common formats
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']:
                    try:
                        datetime.strptime(value, fmt)
                        return True, None
                    except ValueError:
                        continue

        return False, self.message(field)

    def message(self, field: str) -> str:
        return f"The {field} must be a valid date."


class Alpha(ValidationRule):
    """Field must contain only alphabetic characters"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if not isinstance(value, str):
            return False, self.message(field)

        if not value.isalpha():
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must contain only letters."


class AlphaNum(ValidationRule):
    """Field must contain only alphanumeric characters"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if not isinstance(value, str):
            return False, self.message(field)

        if not value.isalnum():
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must contain only letters and numbers."


class AlphaDash(ValidationRule):
    """Field must contain only alpha-numeric characters, dashes, and underscores"""

    PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if not isinstance(value, str):
            return False, self.message(field)

        if not self.PATTERN.match(value):
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must contain only letters, numbers, dashes, and underscores."


class Array(ValidationRule):
    """Field must be an array/list"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if not isinstance(value, (list, tuple)):
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must be an array."


class Json(ValidationRule):
    """Field must be valid JSON"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        if isinstance(value, str):
            try:
                import json
                json.loads(value)
                return True, None
            except json.JSONDecodeError:
                return False, self.message(field)

        return False, self.message(field)

    def message(self, field: str) -> str:
        return f"The {field} must be valid JSON."


# Import database and file rules
from larasanic.validation.database_rules import Unique, Exists
from larasanic.validation.file_rules import (
    File, Image, Mimes, MimeTypes,
    MaxFileSize, MinFileSize, Dimensions
)

# Map of rule names to rule classes
RULE_MAP = {
    # Basic rules
    'required': Required,
    'email': Email,
    'min': Min,
    'max': Max,
    'string': String,
    'integer': Integer,
    'numeric': Numeric,
    'boolean': Boolean,
    'regex': Regex,
    'in': In,
    'not_in': NotIn,
    'confirmed': Confirmed,
    'same': Same,
    'different': Different,
    'url': Url,
    'date': Date,
    'alpha': Alpha,
    'alpha_num': AlphaNum,
    'alpha_dash': AlphaDash,
    'array': Array,
    'json': Json,
    # Database rules
    'unique': Unique,
    'exists': Exists,
    # File rules
    'file': File,
    'image': Image,
    'mimes': Mimes,
    'mimetypes': MimeTypes,
    'max_file_size': MaxFileSize,
    'min_file_size': MinFileSize,
    'dimensions': Dimensions,
}
