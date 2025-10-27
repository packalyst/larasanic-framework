"""
Auth Request Classes
Form validation for authentication endpoints
"""
from larasanic.auth.requests.register_request import RegisterRequest
from larasanic.auth.requests.login_request import LoginRequest

__all__ = ['RegisterRequest', 'LoginRequest']
