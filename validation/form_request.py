"""
Form Request
Laravel-style Form Request for validation
"""
from typing import Dict, List, Any, Optional, Union
from larasanic.validation.validator import Validator
from larasanic.validation.exceptions import ValidationException


class FormRequest:
    """
    Laravel-style Form Request base class

    Example:
        class CreateUserRequest(FormRequest):
            def rules(self) -> Dict[str, Union[str, List[str]]]:
                return {
                    'email': 'required|email|unique:users',
                    'password': 'required|min:8|confirmed',
                    'name': 'required|string|max:255',
                    'age': 'required|integer|min:18'
                }

            def messages(self) -> Dict[str, str]:
                return {
                    'email.required': 'We need your email address!',
                    'password.min': 'Password must be at least 8 characters.'
                }

            def attributes(self) -> Dict[str, str]:
                return {
                    'email': 'email address',
                    'password': 'password'
                }

        # In route handler:
        @app.post('/users')
        async def create_user(request):
            form = CreateUserRequest(request)
            validated = await form.validate()
            # Use validated data
            return json(validated)
    """

    def __init__(self, request):
        """
        Initialize form request

        Args:
            request: Sanic request object
        """
        self.request = request
        self._validator: Optional[Validator] = None
        self._validated_data: Dict[str, Any] = {}

    def rules(self) -> Dict[str, Union[str, List[str]]]:
        """
        Define validation rules

        Returns:
            Dictionary of validation rules

        Example:
            return {
                'email': 'required|email',
                'password': 'required|min:8|confirmed'
            }
        """
        return {}

    def messages(self) -> Dict[str, str]:
        """
        Define custom error messages

        Returns:
            Dictionary of custom messages

        Example:
            return {
                'email.required': 'Please provide your email.',
                'password.min': 'Password must be at least 8 characters.'
            }
        """
        return {}

    def attributes(self) -> Dict[str, str]:
        """
        Define custom attribute names for error messages

        Returns:
            Dictionary of custom attribute names

        Example:
            return {
                'email': 'email address',
                'dob': 'date of birth'
            }
        """
        return {}

    def get_data(self) -> Dict[str, Any]:
        """
        Get data to validate (can be overridden)

        Returns:
            Data dictionary

        Default behavior: Merges JSON body, form data, and query params
        """
        data = {}

        # Add query parameters
        for key, value in self.request.args.items():
            if isinstance(value, list) and len(value) == 1:
                data[key] = value[0]
            else:
                data[key] = value

        # Add form data
        if self.request.form:
            for key, value in self.request.form.items():
                if isinstance(value, list) and len(value) == 1:
                    data[key] = value[0]
                else:
                    data[key] = value

        # Add file uploads
        if self.request.files:
            for key, value in self.request.files.items():
                if isinstance(value, list) and len(value) == 1:
                    data[key] = value[0]
                else:
                    data[key] = value

        # Add JSON data (takes precedence)
        if self.request.json:
            data.update(self.request.json)

        return data

    def get_validator(self) -> Validator:
        """
        Get validator instance

        Returns:
            Validator instance
        """
        if not self._validator:
            self._validator = Validator(
                data=self.get_data(),
                rules=self.rules(),
                messages=self.messages(),
                custom_attributes=self.attributes()
            )
        return self._validator

    async def validate(self) -> Dict[str, Any]:
        """
        Validate the request data

        Returns:
            Validated data

        Raises:
            ValidationException: If validation fails

        Example:
            try:
                validated = await form.validate()
            except ValidationException as e:
                return json({'errors': e.get_errors()}, status=422)
        """
        validator = self.get_validator()
        self._validated_data = await validator.validate()
        return self._validated_data

    async def validate_or_fail(self) -> Dict[str, Any]:
        """
        Alias for validate() (Laravel compatibility)

        Returns:
            Validated data

        Raises:
            ValidationException: If validation fails
        """
        return await self.validate()

    async def passes(self) -> bool:
        """
        Check if validation passes without raising exception

        Returns:
            True if passes

        Example:
            if await form.passes():
                # Process data
            else:
                errors = form.errors()
        """
        validator = self.get_validator()
        return await validator.passes()

    async def fails(self) -> bool:
        """
        Check if validation fails

        Returns:
            True if fails
        """
        return not await self.passes()

    def errors(self) -> Dict[str, List[str]]:
        """
        Get validation errors

        Returns:
            Dictionary of errors
        """
        if not self._validator:
            raise RuntimeError("Validation has not been run yet")
        return self._validator.errors()

    def validated(self) -> Dict[str, Any]:
        """
        Get validated data

        Returns:
            Validated data dictionary
        """
        return self._validated_data

    def safe(self) -> Dict[str, Any]:
        """
        Alias for validated() (Laravel compatibility)

        Returns:
            Validated data
        """
        return self._validated_data

    def only(self, *keys) -> Dict[str, Any]:
        """
        Get only specific keys from validated data

        Args:
            *keys: Keys to retrieve

        Returns:
            Dictionary with only specified keys

        Example:
            data = form.only('email', 'name')
        """
        return {key: self._validated_data.get(key) for key in keys if key in self._validated_data}

    def except_keys(self, *keys) -> Dict[str, Any]:
        """
        Get validated data except specific keys

        Args:
            *keys: Keys to exclude

        Returns:
            Dictionary without specified keys

        Example:
            data = form.except_keys('password', 'password_confirmation')
        """
        return {key: value for key, value in self._validated_data.items() if key not in keys}

    def authorize(self) -> bool:
        """
        Determine if user is authorized to make this request

        Override this method to add authorization logic

        Returns:
            True if authorized (default: True)

        Example:
            def authorize(self) -> bool:
                user = self.request.ctx.user
                return user and user.is_admin
        """
        return True

    async def handle(self):
        """
        Handle the form request validation

        Returns:
            Validated data

        Raises:
            ValidationException: If validation fails
            PermissionError: If not authorized

        This is the main entry point that checks both authorization and validation
        """
        # Check authorization
        if not self.authorize():
            raise PermissionError("Unauthorized")

        # Validate
        return await self.validate()
