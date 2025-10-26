"""
Auth Facade
Provides static access to authentication service
"""
from larasanic.support.facades.facade import Facade


class Auth(Facade):
    """
    Authentication Facade

    Provides static access to authentication service.

    Example:
        # Get current user
        user = await Auth.get_user_by_id(123)

        # Authenticate user
        user = await Auth.authenticate_user('test@example.com', 'password')

        # Generate tokens
        access, refresh = Auth.generate_tokens(user_id=123)

        # Verify token
        payload = Auth.verify_token(token)

        # Register user
        user = await Auth.register_user('test@example.com', 'password')

        # Get user from cache
        user = await Auth.get_cached_user(user_id=123)
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'auth_service'
