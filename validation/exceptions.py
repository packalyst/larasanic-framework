"""
Validation Exceptions
Exception classes for validation errors
"""
from typing import Dict, List, Any


class ValidationException(Exception):
    """Exception raised when validation fails"""

    def __init__(self, errors: Dict[str, List[str]], message: str = "The given data was invalid."):
        """
        Initialize validation exception

        Args:
            errors: Dictionary of field errors
            message: Error message
        """
        self.errors = errors
        self.message = message
        super().__init__(message)

    def get_errors(self) -> Dict[str, List[str]]:
        """
        Get validation errors

        Returns:
            Dictionary of field errors
        """
        return self.errors

    def get_first_error(self, field: str = None) -> str:
        """
        Get first error message

        Args:
            field: Specific field (if None, returns first error from any field)

        Returns:
            First error message
        """
        if field:
            return self.errors.get(field, [''])[0]

        for field_errors in self.errors.values():
            if field_errors:
                return field_errors[0]
        return ''

    def has_error(self, field: str) -> bool:
        """
        Check if field has errors

        Args:
            field: Field name

        Returns:
            True if field has errors
        """
        return field in self.errors and len(self.errors[field]) > 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary

        Returns:
            Dictionary representation
        """
        return {
            'message': self.message,
            'errors': self.errors
        }
