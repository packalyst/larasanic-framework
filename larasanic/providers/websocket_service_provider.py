"""
WebSocket Service Provider
Registers WebSocket services and routes
"""
from larasanic.service_provider import ServiceProvider
from larasanic.websocket import WebSocketManager,WebSocketGuard
from larasanic.support import Config
from larasanic.support.facades import App


class WebSocketServiceProvider(ServiceProvider):
    """Service provider for WebSocket functionality"""

    def register(self):
        # Check if WebSocket is enabled
        if not Config.get('app.WS_ENABLED', True):
            return False
        
        ws_guard = WebSocketGuard()

        # Create WebSocket manager
        ws_manager = WebSocketManager(ws_guard)

        # Register in container
        App.singleton('ws_guard', ws_guard)
        App.singleton('ws_manager', ws_manager)

    def boot(self):
        # Get WebSocket configuration
        ws_manager = App.make('ws_manager')

        from larasanic.defaults import DEFAULT_WS_PATH
        @self.app.sanic_app.websocket(Config.get('app.WS_PATH', DEFAULT_WS_PATH))
        async def websocket_handler(request, ws):
            await ws_manager.connect(request, ws)