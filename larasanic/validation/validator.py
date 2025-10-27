"""
Validator
Laravel-style validation engine
"""
from typing import Dict, List, Any, Optional, Union, Callable
from larasanic.validation.exceptions import ValidationException
from larasanic.validation.rules import RULE_MAP, ValidationRule
import re


class Validator:
    """
    Laravel-style validator

    Examples:
        # Simple validation
        validator = Validator(
            data={'email': 'test@test.com', 'age': 25},
            rules={'email': 'required|email', 'age': 'required|integer|min:18'}
        )
        if await validator.fails():
            errors = validator.errors()

        # With custom messages
        validator = Validator(
            data={'email': 'invalid'},
            rules={'email': 'required|email'},
            messages={'email.email': 'Please provide a valid email address.'}
        )

        # Validate or raise exception
        validated = await validator.validate()  # Raises ValidationException if fails
    """

    def __init__(
        self,
        data: Dict[str, Any],
        rules: Dict[str, Union[str, List]],
        messages: Optional[Dict[str, str]] = None,
        custom_attributes: Optional[Dict[str, str]] = None
    ):
        """
        Initialize validator

        Args:
            data: Data to validate
            rules: Validation rules (field => rule string or list)
            messages: Custom error messages (rule.field => message)
            custom_attributes: Custom field names for error messages
        """
        self.data = data
        self.rules = self._normalize_rules(rules)
        self.messages = messages or {}
        self.custom_attributes = custom_attributes or {}
        self._errors: Dict[str, List[str]] = {}
        self._validated_data: Dict[str, Any] = {}
        self._custom_rules: Dict[str, Callable] = {}

    def _normalize_rules(self, rules: Dict[str, Union[str, List]]) -> Dict[str, List[str]]:
        """
        Normalize rules to list format

        Args:
            rules: Rules dict (field => 'rule1|rule2' or ['rule1', 'rule2'])

        Returns:
            Normalized rules (field => ['rule1', 'rule2'])
        """
        normalized = {}
        for field, rule_def in rules.items():
            if isinstance(rule_def, str):
                # Split by pipe
                normalized[field] = [r.strip() for r in rule_def.split('|') if r.strip()]
            elif isinstance(rule_def, list):
                normalized[field] = rule_def
            else:
                normalized[field] = [str(rule_def)]
        return normalized

    def _parse_rule(self, rule_string: str) -> tuple[str, List[Any]]:
        """
        Parse rule string into name and parameters

        Args:
            rule_string: Rule string (e.g., 'min:5' or 'in:foo,bar,baz')

        Returns:
            Tuple of (rule_name, parameters)
        """
        if ':' not in rule_string:
            return rule_string, []

        rule_name, params_string = rule_string.split(':', 1)

        # Parse parameters
        # Handle comma-separated values, but respect quoted strings
        params = []
        current_param = ''
        in_quotes = False

        for char in params_string:
            if char == '"' or char == "'":
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                if current_param:
                    params.append(self._cast_parameter(current_param.strip()))
                current_param = ''
                continue
            current_param += char

        if current_param:
            params.append(self._cast_parameter(current_param.strip()))

        return rule_name, params

    def _cast_parameter(self, param: str) -> Any:
        """
        Cast parameter to appropriate type

        Args:
            param: Parameter string

        Returns:
            Casted parameter
        """
        # Remove quotes
        if (param.startswith('"') and param.endswith('"')) or \
           (param.startswith("'") and param.endswith("'")):
            return param[1:-1]

        # Try to cast to int
        try:
            return int(param)
        except ValueError:
            pass

        # Try to cast to float
        try:
            return float(param)
        except ValueError:
            pass

        # Return as string
        return param

    def _get_field_value(self, field: str) -> Any:
        """
        Get field value from data (supports nested fields with dot notation)

        Args:
            field: Field name (e.g., 'user.email')

        Returns:
            Field value or None
        """
        if '.' not in field:
            return self.data.get(field)

        # Handle nested fields
        keys = field.split('.')
        value = self.data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _get_field_display_name(self, field: str) -> str:
        """
        Get display name for field (uses custom attributes or field name)

        Args:
            field: Field name

        Returns:
            Display name
        """
        return self.custom_attributes.get(field, field.replace('_', ' '))

    def _get_custom_message(self, field: str, rule_name: str) -> Optional[str]:
        """
        Get custom error message

        Args:
            field: Field name
            rule_name: Rule name

        Returns:
            Custom message or None
        """
        # Check for field.rule format
        key = f"{field}.{rule_name}"
        if key in self.messages:
            return self.messages[key]

        # Check for just rule name
        if rule_name in self.messages:
            return self.messages[rule_name]

        return None

    async def _validate_field(self, field: str, rule_string: str) -> Optional[str]:
        """
        Validate field against single rule

        Args:
            field: Field name
            rule_string: Rule string (e.g., 'min:5')

        Returns:
            Error message or None if valid
        """
        rule_name, params = self._parse_rule(rule_string)
        value = self._get_field_value(field)

        # Check for custom rule
        if rule_name in self._custom_rules:
            is_valid = await self._custom_rules[rule_name](field, value, self.data, *params)
            if not is_valid:
                custom_msg = self._get_custom_message(field, rule_name)
                return custom_msg or f"The {self._get_field_display_name(field)} field failed {rule_name} validation."
            return None

        # Check for built-in rule
        if rule_name not in RULE_MAP:
            raise ValueError(f"Unknown validation rule: {rule_name}")

        # Instantiate rule class
        rule_class = RULE_MAP[rule_name]
        rule_instance = rule_class(*params)

        # Run validation
        is_valid, error_message = await rule_instance.validate(
            self._get_field_display_name(field),
            value,
            self.data
        )

        if not is_valid:
            # Check for custom message
            custom_msg = self._get_custom_message(field, rule_name)
            return custom_msg or error_message

        return None

    async def validate(self) -> Dict[str, Any]:
        """
        Validate data and return validated data

        Returns:
            Validated data

        Raises:
            ValidationException: If validation fails

        Example:
            try:
                validated = await validator.validate()
                # Use validated data
            except ValidationException as e:
                return json({'errors': e.get_errors()}, status=422)
        """
        await self.run()

        if await self.fails():
            raise ValidationException(self._errors)

        return self._validated_data

    async def run(self):
        """Run all validations"""
        self._errors = {}
        self._validated_data = {}
        
        for field, rules_list in self.rules.items():
            field_errors = []

            for rule_string in rules_list:
                error = await self._validate_field(field, rule_string)
                if error:
                    field_errors.append(error)
                    # Stop on first error for this field (Laravel behavior)
                    break

            if field_errors:
                self._errors[field] = field_errors
            else:
                # Add to validated data if no errors
                value = self._get_field_value(field)
                if value is not None:
                    self._validated_data[field] = value

    async def passes(self) -> bool:
        """
        Check if validation passes

        Returns:
            True if validation passes

        Example:
            if await validator.passes():
                # Process data
        """
        if not self._errors and not self._validated_data:
            await self.run()
        return len(self._errors) == 0

    async def fails(self) -> bool:
        """
        Check if validation fails

        Returns:
            True if validation fails

        Example:
            if await validator.fails():
                errors = validator.errors()
        """
        return not await self.passes()

    def errors(self) -> Dict[str, List[str]]:
        """
        Get validation errors

        Returns:
            Dictionary of field errors

        Example:
            errors = validator.errors()
            # {'email': ['The email must be a valid email address.']}
        """
        return self._errors

    def validated(self) -> Dict[str, Any]:
        """
        Get validated data (only fields that passed validation)

        Returns:
            Validated data

        Example:
            data = validator.validated()
        """
        return self._validated_data

    def safe(self) -> Dict[str, Any]:
        """
        Alias for validated() (Laravel compatibility)

        Returns:
            Validated data
        """
        return self._validated_data

    def add_rule(self, name: str, callback: Callable) -> 'Validator':
        """
        Add custom validation rule

        Args:
            name: Rule name
            callback: Async validation function (field, value, data, *params) -> bool

        Returns:
            Self for chaining

        Example:
            async def validate_username(field, value, data):
                # Custom validation logic
                return value not in ['admin', 'root']

            validator.add_rule('not_reserved', validate_username)
        """
        self._custom_rules[name] = callback
        return self

    def sometimes(self, field: str, rules: Union[str, List[str]], condition: Callable) -> 'Validator':
        """
        Add conditional validation rules

        Args:
            field: Field name
            rules: Rules to apply
            condition: Callable that returns bool (receives data dict)

        Returns:
            Self for chaining

        Example:
            validator.sometimes('reason', 'required|string', lambda data: data.get('status') == 'rejected')
        """
        if condition(self.data):
            if field not in self.rules:
                self.rules[field] = []

            if isinstance(rules, str):
                self.rules[field].extend([r.strip() for r in rules.split('|')])
            else:
                self.rules[field].extend(rules)

        return self

    def get_first_error(self, field: str = None) -> str:
        """
        Get first error message

        Args:
            field: Specific field (if None, returns first error from any field)

        Returns:
            First error message

        Example:
            error = validator.get_first_error('email')
        """
        if field:
            return self._errors.get(field, [''])[0]

        for field_errors in self._errors.values():
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
        return field in self._errors and len(self._errors[field]) > 0


# Global helper function
async def validate(
    data: Dict[str, Any],
    rules: Dict[str, Union[str, List]],
    messages: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Quick validation helper

    Args:
        data: Data to validate
        rules: Validation rules
        messages: Custom error messages

    Returns:
        Validated data

    Raises:
        ValidationException: If validation fails

    Example:
        validated = await validate(
            data=request.json,
            rules={'email': 'required|email', 'password': 'required|min:8'}
        )
    """
    validator = Validator(data, rules, messages)
    return await validator.validate()
