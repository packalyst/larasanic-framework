"""
WebSocket Guard
Handles WebSocket authentication using JWT tokens from cookies
"""
from sanic import Request
from typing import Optional
from larasanic.support import Config


class WebSocketGuard:
    """WebSocket authentication guard"""

    def __init__(self):
        pass

    async def authenticate_websocket(self, request: Request, ws) -> Optional[int]:
        from larasanic.support.facades import HttpRequest
        try:
            user = HttpRequest.get_user()
            if not user:
                await ws.close(code=Config.get('security.WS_AUTH_CLOSE_CODE'), reason="Authentication failed")
                return None

            if not user.id:
                await ws.close(code=Config.get('security.WS_AUTH_CLOSE_CODE'), reason="Authentication failed")
                return None

            return user.id

        except Exception as e:
            await ws.close(code=Config.get('security.WS_AUTH_CLOSE_CODE'), reason="Authentication failed")
            return None
