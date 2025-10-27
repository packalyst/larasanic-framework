"""
WebSocket Guard
Handles WebSocket authentication using JWT tokens from cookies
"""
from sanic import Request
from typing import Optional
from larasanic.support import Config


class WebSocketGuard:
    """WebSocket authentication guard"""

    def __init__(self, auth_service):
        """
        Initialize WebSocket guard

        Args:
            auth_service: AuthService instance for token verification
        """
        self.auth_service = auth_service

    async def authenticate_websocket(self, request: Request, ws) -> Optional[int]:
        from larasanic.support.facades import HttpRequest
        try:
            # Extract JWT from cookies
            access_token = HttpRequest.get_cookie(Config.get('security.COOKIE_ACCESS_TOKEN_NAME'))

            if not access_token:
                await ws.close(code=Config.get('security.WS_AUTH_CLOSE_CODE'), reason="Authentication failed")
                return None

            # Verify token and extract user_id
            user_id = self.auth_service.extract_user_id_from_token(
                access_token,
                token_type=Config.get('security.TOKEN_TYPE_ACCESS')
            )

            if not user_id:
                await ws.close(code=Config.get('security.WS_AUTH_CLOSE_CODE'), reason="Authentication failed")
                return None

            return user_id

        except Exception as e:
            await ws.close(code=Config.get('security.WS_AUTH_CLOSE_CODE'), reason="Authentication failed")
            return None
