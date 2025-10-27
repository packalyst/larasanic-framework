"""
Auth Controller
Handles authentication endpoints: login, register, logout, refresh, me
"""
from larasanic.support.facades import HttpRequest as Request
from larasanic.support import Config
from sanic import response
from larasanic.http import ResponseHelper
from larasanic.validation import ValidationException
from larasanic.auth.requests import RegisterRequest, LoginRequest

class AuthController:
    def __init__(self, auth_service):
        """
        Initialize auth controller
        """
        self.auth_service = auth_service

    async def register(self, request: Request):
        """
        Register new user
        """
        # Validate request using FormRequest
        form = RegisterRequest(request)

        try:
            validated = await form.validate()
        except ValidationException as e:
            return ResponseHelper.validation_error(e.get_errors())

        # Register user with validated data
        user = await self.auth_service.register_user(
            validated['email'],
            validated['password']
        )

        if not user:
            return ResponseHelper.bad_request("Email already exists")

        # Generate tokens
        access_token, refresh_token = await self.auth_service.generate_tokens(user.id)

        # Return auth state
        auth_state = {
            "isAuthenticated": True,
            "user": await user.to_dict(),
            "token": access_token
        }

        return ResponseHelper.created(auth_state, "Registration successful")

    async def login(self, request: Request):
        """
        Login user
        """
        # Validate request using FormRequest
        form = LoginRequest(request)

        try:
            validated = await form.validate()
        except ValidationException as e:
            return ResponseHelper.validation_error(e.get_errors())

        # Authenticate user with validated data
        user = await self.auth_service.authenticate_user(
            validated['email'],
            validated['password']
        )

        if not user:
            return ResponseHelper.unauthorized("Undefined auth error")

        # Generate tokens
        access_token, refresh_token = await self.auth_service.generate_tokens(user.id)
        user = user.to_dict()
        # Return auth state
        auth_state = {"isAuthenticated": True,"user": user,}
        return ResponseHelper.success(auth_state, "Login successful")

    async def logout(self, request: Request):
        """
        Logout user
        """
        # Return logged out state
        auth_state = {"isAuthenticated": False,"user": None,}

        # Clear auth cookies using fluent API
        return ResponseHelper.success(auth_state, "Logout successful") \
            .without_cookie(Config.get('security.COOKIE_ACCESS_TOKEN_NAME')) \
            .without_cookie(Config.get('security.COOKIE_REFRESH_TOKEN_NAME'))

    async def refresh(self, request: Request):
        """
        Refresh access token
        """
        from larasanic.support.facades import HttpRequest

        refresh_token = HttpRequest.get_cookie(Config.get('security.COOKIE_REFRESH_TOKEN_NAME'))
        if not refresh_token:
            return ResponseHelper.unauthorized("Refresh token missing")

        tokens = await self.auth_service.generate_tokens(refresh_token)
        if not tokens:
            return ResponseHelper.unauthorized("Invalid refresh token")

        return ResponseHelper.success(None, "Token refreshed")

    async def me(self, request: Request):
        from larasanic.support.facades import HttpRequest
        user = HttpRequest.get_user()
        if not user:
            return ResponseHelper.unauthorized("Not authenticated")

        return ResponseHelper.success(await user.to_dict())