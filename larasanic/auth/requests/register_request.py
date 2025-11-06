"""
Register Request
Validates user registration data
"""
from larasanic.validation import FormRequest


class RegisterRequest(FormRequest):
    """Validation for user registration"""

    def rules(self):
        """
        Define validation rules for registration

        Returns:
            Dictionary of validation rules
        """
        return {
            'name': 'required|string|min:2|max:255',
            'email': 'required|email|unique:users,email',
            'password': 'required|string|min:8'
        }

    def messages(self):
        """
        Define custom error messages

        Returns:
            Dictionary of custom error messages
        """
        return {
            'name.required': 'Name is required',
            'name.min': 'Name must be at least 2 characters',
            'email.required': 'Email is required',
            'email.email': 'Invalid email format',
            'email.unique': 'Email already exists',
            'password.required': 'Password is required',
            'password.min': 'Password must be at least 8 characters'
        }

    def attributes(self):
        """
        Define custom attribute names for error messages

        Returns:
            Dictionary of custom attribute names
        """
        return {
            'name': 'name',
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
