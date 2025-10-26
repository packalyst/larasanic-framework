"""
Validation Helpers
Quick validation functions for common use cases
"""
from typing import Dict, Any, Union, List, Optional
from larasanic.validation import Validator, ValidationException


async def quick_validate(
    data: Dict[str, Any],
    rules: Dict[str, Union[str, List[str]]],
    messages: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Quick validation helper that returns validated data or raises exception

    Args:
        data: Data to validate
        rules: Validation rules
        messages: Custom error messages

    Returns:
        Validated data

    Raises:
        ValidationException: If validation fails

    Usage:
        try:
            validated = await quick_validate(
                data=request.json,
                rules={'email': 'required|email', 'age': 'required|integer|min:18'}
            )
        except ValidationException as e:
            return json({'errors': e.get_errors()}, status=422)
    """
    validator = Validator(data, rules, messages)
    return await validator.validate()


async def check_validation(
    data: Dict[str, Any],
    rules: Dict[str, Union[str, List[str]]],
    messages: Optional[Dict[str, str]] = None
) -> tuple[bool, Dict[str, List[str]], Dict[str, Any]]:
    """
    Check validation without raising exception

    Args:
        data: Data to validate
        rules: Validation rules
        messages: Custom error messages

    Returns:
        Tuple of (passes, errors, validated_data)

    Usage:
        passes, errors, validated = await check_validation(
            data=request.json,
            rules={'email': 'required|email'}
        )

        if not passes:
            return json({'errors': errors}, status=422)

        # Use validated data
        email = validated['email']
    """
    validator = Validator(data, rules, messages)
    await validator.run()

    return (
        await validator.passes(),
        validator.errors(),
        validator.validated()
    )


async def validate_field(
    field: str,
    value: Any,
    rules: Union[str, List[str]],
    data: Optional[Dict[str, Any]] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate a single field

    Args:
        field: Field name
        value: Field value
        rules: Validation rules
        data: Full data dict (for rules like 'confirmed' that need other fields)

    Returns:
        Tuple of (is_valid, error_message)

    Usage:
        is_valid, error = await validate_field(
            'email',
            'test@example.com',
            'required|email'
        )

        if not is_valid:
            return json({'error': error}, status=422)
    """
    validator = Validator(
        data={field: value, **(data or {})},
        rules={field: rules}
    )
    await validator.run()

    if await validator.fails():
        return False, validator.get_first_error(field)

    return True, None


async def validate_email(email: str) -> bool:
    """
    Quick email validation

    Args:
        email: Email address to validate

    Returns:
        True if valid

    Usage:
        if await validate_email(user_input):
            # Email is valid
            pass
    """
    is_valid, _ = await validate_field('email', email, 'email')
    return is_valid


async def validate_password(password: str, min_length: int = 8) -> tuple[bool, Optional[str]]:
    """
    Quick password validation

    Args:
        password: Password to validate
        min_length: Minimum password length

    Returns:
        Tuple of (is_valid, error_message)

    Usage:
        is_valid, error = await validate_password(request.json['password'])
        if not is_valid:
            return json({'error': error}, status=422)
    """
    return await validate_field(
        'password',
        password,
        f'required|string|min:{min_length}'
    )


async def validate_url(url: str) -> bool:
    """
    Quick URL validation

    Args:
        url: URL to validate

    Returns:
        True if valid

    Usage:
        if await validate_url(user_input):
            # URL is valid
            pass
    """
    is_valid, _ = await validate_field('url', url, 'url')
    return is_valid


async def validate_username(
    username: str,
    min_length: int = 3,
    max_length: int = 20
) -> tuple[bool, Optional[str]]:
    """
    Quick username validation (alphanumeric with underscores/dashes)

    Args:
        username: Username to validate
        min_length: Minimum length
        max_length: Maximum length

    Returns:
        Tuple of (is_valid, error_message)

    Usage:
        is_valid, error = await validate_username('john_doe')
        if not is_valid:
            return json({'error': error}, status=422)
    """
    return await validate_field(
        'username',
        username,
        f'required|alpha_dash|min:{min_length}|max:{max_length}'
    )


async def validate_phone(phone: str, pattern: str = None) -> tuple[bool, Optional[str]]:
    """
    Quick phone number validation

    Args:
        phone: Phone number to validate
        pattern: Optional regex pattern (default: basic numeric check)

    Returns:
        Tuple of (is_valid, error_message)

    Usage:
        # Basic validation
        is_valid, error = await validate_phone('+1234567890')

        # With custom pattern
        is_valid, error = await validate_phone(
            phone=user_input,
            pattern=r'^\+?1?\d{9,15}$'
        )
    """
    if pattern:
        return await validate_field('phone', phone, f'required|regex:{pattern}')
    else:
        return await validate_field('phone', phone, 'required|numeric|min:9|max:15')


async def validate_required_fields(
    data: Dict[str, Any],
    *fields: str
) -> tuple[bool, List[str]]:
    """
    Check if required fields are present

    Args:
        data: Data dictionary
        *fields: Required field names

    Returns:
        Tuple of (all_present, missing_fields)

    Usage:
        all_present, missing = await validate_required_fields(
            request.json,
            'email', 'password', 'name'
        )

        if not all_present:
            return json({'error': f'Missing fields: {", ".join(missing)}'}, status=422)
    """
    rules = {field: 'required' for field in fields}
    validator = Validator(data, rules)
    await validator.run()

    if await validator.passes():
        return True, []

    missing = [field for field in fields if field in validator.errors()]
    return False, missing


async def validate_pagination(
    data: Dict[str, Any],
    max_per_page: int = 100
) -> tuple[bool, Dict[str, List[str]], Dict[str, Any]]:
    """
    Validate pagination parameters

    Args:
        data: Request data containing page/per_page
        max_per_page: Maximum items per page

    Returns:
        Tuple of (is_valid, errors, validated_data)

    Usage:
        is_valid, errors, validated = await validate_pagination(request.args)

        if not is_valid:
            return json({'errors': errors}, status=422)

        page = validated.get('page', 1)
        per_page = validated.get('per_page', 20)
    """
    rules = {
        'page': 'integer|min:1',
        'per_page': f'integer|min:1|max:{max_per_page}'
    }

    return await check_validation(data, rules)


async def validate_date_range(
    data: Dict[str, Any],
    start_field: str = 'start_date',
    end_field: str = 'end_date'
) -> tuple[bool, Dict[str, List[str]], Dict[str, Any]]:
    """
    Validate date range parameters

    Args:
        data: Request data
        start_field: Start date field name
        end_field: End date field name

    Returns:
        Tuple of (is_valid, errors, validated_data)

    Usage:
        is_valid, errors, validated = await validate_date_range(request.json)

        if not is_valid:
            return json({'errors': errors}, status=422)
    """
    rules = {
        start_field: 'required|date',
        end_field: 'required|date'
    }

    return await check_validation(data, rules)


async def validate_search_query(
    data: Dict[str, Any],
    min_length: int = 2,
    max_length: int = 100
) -> tuple[bool, Optional[str]]:
    """
    Validate search query parameter

    Args:
        data: Request data
        min_length: Minimum query length
        max_length: Maximum query length

    Returns:
        Tuple of (is_valid, error_message)

    Usage:
        is_valid, error = await validate_search_query(request.args)

        if not is_valid:
            return json({'error': error}, status=422)
    """
    query = data.get('q', data.get('query', ''))

    is_valid, error = await validate_field(
        'query',
        query,
        f'required|string|min:{min_length}|max:{max_length}'
    )

    return is_valid, error
