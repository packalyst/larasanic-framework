"""
Auth Service
Handles user authentication, registration, token management, and cryptographic operations
"""
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sanic import Request
from larasanic.support import Crypto, Config
from larasanic.support.facades import HttpRequest

class AuthService:

    def __init__(self, private_key: str, public_key: str, algorithm: str,
                 access_ttl: int, refresh_ttl: int, cookie_secure: bool, user_model):
        """
        Initialize auth service
        """
        # JWT configuration
        self.private_key = private_key
        self.public_key = public_key
        self.algorithm = algorithm
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
        
        self.cookie_secure = cookie_secure

        # Database model
        self.user_model = user_model

        # User cache: {user_id: (user, expiry_datetime)}
        from larasanic.defaults import DEFAULT_USER_CACHE_TTL
        self._user_cache = {}
        self._cache_ttl = DEFAULT_USER_CACHE_TTL

    # ========================================================================
    # Cryptographic Operations
    # ========================================================================

    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt
        """
        return Crypto.hash_password(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify password against bcrypt hash
        Returns:
            True if password matches
        """
        return Crypto.verify_password(password, hashed)

    async def generate_access_token(self, user_id: int) -> str:
        """
        Generate access token
        """
        return await Crypto.generate_jwt_token(
            user_id=user_id,
            private_key=self.private_key,
            algorithm=self.algorithm,
            ttl_seconds=self.access_ttl,
            token_type=Config.get('security.TOKEN_TYPE_ACCESS')
        )

    async def generate_refresh_token(self, user_id: int) -> str:
        """
        Generate refresh token
        """
        return await Crypto.generate_jwt_token(
            user_id=user_id,
            private_key=self.private_key,
            algorithm=self.algorithm,
            ttl_seconds=self.refresh_ttl,
            token_type=Config.get('security.TOKEN_TYPE_REFRESH')
        )

    def verify_token(self, token: str, token_type: str = None) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token
        """
        return Crypto.verify_jwt_token(
            token=token,
            public_key=self.public_key,
            algorithm=self.algorithm,
            expected_type=token_type
        )

    def extract_user_id_from_token(self, token: str, token_type: str = None) -> Optional[int]:
        """
        Extract user ID from token
        """
        return Crypto.extract_jwt_user_id(
            token=token,
            public_key=self.public_key,
            algorithm=self.algorithm,
            expected_type=token_type
        )

    # ========================================================================
    # Authentication & User Management
    # ========================================================================

    async def register_user(self, email: str, password: str) -> Optional[any]:
        """
        Register a new user
        Returns:
            User instance if successful, None if email exists
        """
        # Check if user already exists
        existing_user = await self.user_model.find_by_email(email)
        if existing_user:
            return None

        # Hash password (use async version to avoid blocking event loop)
        password_hash = await Crypto.hash_password_async(password)

        # Create user
        user = await self.user_model.create(email=email,password_hash=password_hash)
        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[any]:
        """
        Authenticate user with email and password (timing-attack resistant)
        """
        # Find user by email
        user = await self.user_model.filter(email=email).first()
        
        # Use dummy hash if user not found (prevents timing attack)
        password_hash = user.password_hash if user else Crypto._DUMMY_HASH

        # Always verify password (constant time whether user exists or not)
        # Use async version to avoid blocking event loop
        if not await Crypto.verify_password_async(password, password_hash):
            return None

        # Return user only if it exists (after password check)
        return user if user else None

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


    async def generate_tokens(self, user_id: int = None, refresh_token: str = None) -> bool:
        """
        Generate/refresh tokens and set auth cookies.
        Args:
            user_id: For new token generation.
            refresh_token: For token refresh.
        Returns:
            Tuple of (access_token, refresh_token)
        Usage:
            # New tokens
            auth_service.authenticate_and_set_cookies(user_id=user.id)

            # Refresh tokens
            auth_service.authenticate_and_set_cookies(refresh_token=token)
        """
        from larasanic.support.facades import HttpResponse

        # Mode 1: generate new tokens for user_id
        if user_id:
            access_token = await self.generate_access_token(user_id)
            refresh_token_new = await self.generate_refresh_token(user_id)
            tokens = access_token, refresh_token_new
        # Mode 2: refresh tokens using existing refresh_token
        elif refresh_token:
            tokens = await self.refresh_access_token(refresh_token)
        
        if not tokens:
            return None
        
        access_token, refresh_token = tokens

        HttpResponse.add_cookie(                                                                       
            Config.get('security.COOKIE_ACCESS_TOKEN_NAME'),                                                                  
            access_token,                                                                              
            max_age=self.access_ttl,                                                                   
            httponly=True,                                                                             
            secure=self.cookie_secure,                                                                 
            samesite='Lax'                                                                             
        ) 
        HttpResponse.add_cookie(
            Config.get('security.COOKIE_REFRESH_TOKEN_NAME'),
            refresh_token,
            httponly=True,
            secure=self.cookie_secure,
            samesite='Lax',
            max_age=self.refresh_ttl
        )
        return access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """
        Refresh access token using refresh token (optimized - no DB query)
        Returns:
            Tuple of (new_access_token, same_refresh_token) if valid, None otherwise
        """
        # Extract and verify user_id from refresh token
        user_id = self.extract_user_id_from_token(refresh_token, "refresh")
        if not user_id:
            return None

        # No need to query DB - trust the refresh token's signature
        # Only generate new access token, reuse refresh token
        new_access_token = await self.generate_access_token(user_id)

        return new_access_token, refresh_token

    async def get_user_from_request(self, request: Request) -> Optional[any]:
        from larasanic.support.facades import HttpRequest
        access_token = HttpRequest.get_cookie(Config.get('security.COOKIE_ACCESS_TOKEN_NAME'))
        if not access_token:
            return None

        user_id = self.extract_user_id_from_token(access_token, "access")
        if not user_id:
            return None

        # Check cache first
        if user_id in self._user_cache:
            user, expiry = self._user_cache[user_id]
            if datetime.now() < expiry:
                return user
            else:
                # Cache expired, remove it
                del self._user_cache[user_id]

        # Cache miss or expired - query database
        user = await self.user_model.get_or_none(id=user_id)
        if user:
            # Cache the user with expiry time
            self._user_cache[user_id] = (user, datetime.now() + timedelta(seconds=self._cache_ttl))

        return user

    def invalidate_user_cache(self, user_id: int) -> None:
        """
        Invalidate cached user data for a specific user
        Example:
            auth_service.invalidate_user_cache(user.id)
        """
        if user_id in self._user_cache:
            del self._user_cache[user_id]

    def clear_user_cache(self) -> None:
        """
        Clear all cached user data
        Useful for testing or when many users are updated at once
        """
        self._user_cache.clear()
    
    def _set_auth_cookies(self, resp, access_token: str, refresh_token: str):
        """
        Set auth cookies on response

        Args:
            resp: ResponseBuilder or HTTPResponse
            access_token: JWT access token
            refresh_token: JWT refresh token

        Returns:
            Response with cookies set
        """
        # Use fluent cookie API
        return resp \
            .with_cookie(
                Config.get('security.COOKIE_ACCESS_TOKEN_NAME'),
                access_token,
                httponly=True,
                secure=self.cookie_secure,
                samesite="Lax",
                max_age=self.access_ttl
            ) \
            .with_cookie(
                Config.get('security.COOKIE_REFRESH_TOKEN_NAME'),
                refresh_token,
                httponly=True,
                secure=self.cookie_secure,
                samesite="Lax",
                max_age=self.refresh_ttl
            )