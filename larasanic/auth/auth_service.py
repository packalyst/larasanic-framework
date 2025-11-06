"""
Auth Service
Handles user authentication, registration, token management, and cryptographic operations
"""
from typing import Optional
from larasanic.support import Crypto, Config
from larasanic.support.facades import HttpRequest
from larasanic.auth.models import User,AccessToken

class AuthService:

    def __init__(self):
        from larasanic.defaults import DEFAULT_TOKEN_LIFETIME_SECONDS

        self.token_lifetime_seconds = Config.get('security.TOKEN_LIFETIME_SECONDS',DEFAULT_TOKEN_LIFETIME_SECONDS)

    async def create_token_for_user(self,user_id: int) -> str:
        """
        Create a new token for user (called on login)
        """
        plain_token, token_record = await AccessToken.create_for_user(
            user_id=user_id,
            name=Config.get('security.TOKEN_TYPE_ACCESS'),
            expires_in_seconds=self.token_lifetime_seconds
        )

        from larasanic.support.facades import HttpResponse
        HttpResponse.add_cookie(                                                                       
            Config.get('security.COOKIE_ACCESS_TOKEN_NAME'),                                                                  
            plain_token,                                                                              
            max_age=self.token_lifetime_seconds,                                                                   
            httponly=True,                                                                             
            secure=Config.get('session.COOKIE_SECURE', False),                                                                 
            samesite='Lax'                                                                             
        ) 
        return plain_token

    async def verify_token(self, token_to_verify) -> Optional[int]:
        """
        Verify token and return user ID
        """
        if not token_to_verify:
            return None
        
        # Lookup token in database
        token_record = await AccessToken.find_by_token(token_to_verify)
        if not token_record:
            return None

        return token_record.user_id
    
    async def get_user_from_token(self) -> Optional[User]:
        """
        Get user from token
        """
        access_token = HttpRequest.get_cookie(Config.get('security.COOKIE_ACCESS_TOKEN_NAME'))
        if not access_token:
            return None
        
        user_id = await self.verify_token(access_token)

        if not user_id:
            return None

        try:
            return await User.get(id=user_id)
        except Exception:
            return None
        
    async def revoke_token(self) -> bool:
        """
        Revoke (delete) a token (called on logout)
        """
        access_token = HttpRequest.get_cookie(Config.get('security.COOKIE_ACCESS_TOKEN_NAME'))
        return await AccessToken.revoke_by_token(access_token)

    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """
        Revoke all tokens for a user
        Returns:
            Number of tokens revoked
        """
        return await AccessToken.revoke_all_for_user(user_id)
    

    # ========================================================================
    # Authentication & User Management
    # ========================================================================

    async def register_user(self, data: dict) -> Optional[any]:
        """
        Register a new user

        Args:
            data: Dictionary with user data (name, email, password)
        """
        # Check if user already exists
        existing_user = await User.find_by_email(data['email'])
        if existing_user:
            return None

        # Hash password (use async version to avoid blocking event loop)
        password_hash = await Crypto.hash_password_async(data['password'])

        # Build user data with hashed password
        user_data = {**data}
        user_data.pop('password', None)  # Remove plain password
        user_data['password_hash'] = password_hash

        # Create user
        user = await User.create(**user_data)

        # Generate tokens
        await self.create_token_for_user(user_id=user.id)

        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[any]:
        # Find user by email
        user = await User.filter(email=email).first()
        
        # Use dummy hash if user not found (prevents timing attack)
        password_hash = user.password_hash if user else Crypto._DUMMY_HASH

        # Always verify password (constant time whether user exists or not)
        # Use async version to avoid blocking event loop
        if not await Crypto.verify_password_async(password, password_hash):
            return None
        if not user:
            return None
        
        # Generate tokens
        await self.create_token_for_user(user_id=user.id)

        # Return user only if it exists (after password check)
        return user

    # ========================================================================
    # Laravel-like Helper Methods
    # ========================================================================

    def check(self) -> bool:
        """
        Determine if the current user is authenticated (Laravel: Auth::check())

        Returns:
            bool: True if user is authenticated, False otherwise
        """
        try:
            user = HttpRequest.get_user()
            return user is not None
        except Exception:
            return False

    def guest(self) -> bool:
        """
        Determine if the current user is a guest (not authenticated) (Laravel: Auth::guest())

        Returns:
            bool: True if user is NOT authenticated, False if authenticated
        """
        return not self.check()

    def user(self) -> Optional[User]:
        """
        Get the currently authenticated user (Laravel: Auth::user())

        Returns:
            User instance or None
        """
        try:
            return HttpRequest.get_user()
        except Exception:
            return None

    def id(self) -> Optional[int]:
        """
        Get the ID of the currently authenticated user (Laravel: Auth::id())

        Returns:
            User ID or None
        """
        user = self.user()
        return user.id if user else None


    def user_as_json(self) -> str:
        """
        Get user data as JSON string (for embedding in templates)
        Uses the model's to_dict() method which respects the 'hidden' attribute.
        Returns properly formatted JSON with JavaScript-compatible booleans and nulls.
        """
        import json

        try:
            user = HttpRequest.get_user()
            if not user:
                result = {"isAuthenticated": False, "user": None}
            else:
                result = {
                    "isAuthenticated": True,"user": user.to_dict()
                }
        except Exception:
            result = {"isAuthenticated": False, "user": None}

        return json.dumps(result)