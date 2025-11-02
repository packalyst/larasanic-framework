"""
Auth Controller
Handles authentication endpoints: login, register, logout, refresh, me
"""
from larasanic.support.facades import Auth,HttpRequest
from larasanic.support import Config
from larasanic.http import ResponseHelper
from larasanic.validation import ValidationException
from larasanic.auth.requests import RegisterRequest, LoginRequest

class AuthController:
 
    async def register(self, request: HttpRequest):
        # Validate request using FormRequest
        form = RegisterRequest(request)

        try:
            validated = await form.validate()
        except ValidationException as e:
            return ResponseHelper.validation_error(e.get_errors())

        # Register user with validated data
        user = await Auth.register_user(
            validated['email'],validated['password']
        )

        if not user:
            return ResponseHelper.bad_request("Email already exists")

        # Return auth state
        auth_state = {
            "isAuthenticated": True,"user": user.to_dict(),
        }

        return ResponseHelper.created(auth_state, "Registration successful")

    async def login(self, request: HttpRequest):
        # Validate request using FormRequest
        form = LoginRequest(request)

        try:
            validated = await form.validate()
        except ValidationException as e:
            return ResponseHelper.validation_error(e.get_errors())

        # Authenticate user with validated data
        user = await Auth.authenticate_user(validated['email'],validated['password'])

        if not user:
            return ResponseHelper.unauthorized("Undefined auth error")

        user = user.to_dict()
        # Return auth state
        auth_state = {"isAuthenticated": True,"user": user,}
        return ResponseHelper.success(auth_state, "Login successful")

    async def logout(self, request:HttpRequest):
        """
        Logout user
        """
        # Delete token from database
        await Auth.revoke_token()
        
        # Return logged out state
        auth_state = {
            "isAuthenticated": False,"user": None,
        }

        # Clear auth cookies using fluent API
        return ResponseHelper.success(auth_state, "Logout successful") \
            .without_cookie(Config.get('security.COOKIE_ACCESS_TOKEN_NAME')) \
            .without_cookie(Config.get('security.COOKIE_REFRESH_TOKEN_NAME'))


    async def me(self, request: HttpRequest):
        user = HttpRequest.get_user()
        if not user:
            return ResponseHelper.unauthorized("Not authenticated")

        return ResponseHelper.success(user.to_dict())