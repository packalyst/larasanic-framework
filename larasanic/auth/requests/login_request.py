"""
Login Request
Validates user login credentials
"""
from larasanic.validation import FormRequest


class LoginRequest(FormRequest):
    """Validation for user login"""

    def rules(self):
        """
        Define validation rules for login

        Returns:
            Dictionary of validation rules
        """
        return {
            'email': 'required|email',
            'password': 'required|string'
        }

    def messages(self):
        """
        Define custom error messages

        Returns:
            Dictionary of custom error messages
        """
        return {
            'email.required': 'Email is required',
            'email.email': 'Invalid email format',
            'password.required': 'Password is required'
        }

    def attributes(self):
        """
        Define custom attribute names for error messages

        Returns:
            Dictionary of custom attribute names
        """
        return {
            'email': 'email address',
            'password': 'password'
        }

    def get_data(self):
        """
        Get and normalize data from request

        Automatically converts email to lowercase and strips whitespace

        Returns:
            Normalized data dictionary
        """
        data = super().get_data()

        # Normalize email to lowercase and strip whitespace
        if 'email' in data and data['email']:
            data['email'] = str(data['email']).strip().lower()

        return data
