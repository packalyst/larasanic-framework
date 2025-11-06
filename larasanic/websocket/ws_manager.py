"""
WebSocket Manager
Manages WebSocket connections, message handling, and broadcasting

Supports Redis pub/sub for horizontal scaling across multiple processes
"""
import json
import asyncio
from typing import Dict, Set, Any, Optional
from datetime import datetime
from sanic import Request

# Redis for inter-process communication
try:
    from redis import asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting

    Features:
    - Single-process: Broadcasts to connections in memory
    - Multi-process: Uses Redis pub/sub to broadcast across processes
    """

    def __init__(self, ws_guard):
        """
        Initialize WebSocket manager

        Args:
            ws_guard: WebSocketGuard instance for authentication
        """
        self.connections: Dict[int, Set[Any]] = {}
        self.guard = ws_guard

        # Redis for multi-process support
        self.redis_client: Optional[Any] = None
        self.redis_pubsub: Optional[Any] = None
        self.subscriber_task: Optional[asyncio.Task] = None

    async def _init_redis(self):
        """Initialize Redis client for pub/sub (lazy initialization)"""
        if not REDIS_AVAILABLE or self.redis_client:
            return

        try:
            from larasanic.support import EnvHelper
            from larasanic.defaults import DEFAULT_REDIS_URL
            redis_url = EnvHelper.get('REDIS_URL', DEFAULT_REDIS_URL)

            self.redis_client = aioredis.from_url(
                redis_url,
                encoding='utf-8',
                decode_responses=True
            )
            self.redis_pubsub = self.redis_client.pubsub()
            print(f"[WebSocket] Redis connected: {redis_url}")
        except Exception as e:
            print(f"[WebSocket] Redis connection failed: {e}")
            self.redis_client = None

    async def _start_redis_subscriber(self):
        """Start Redis subscriber task (auto-start on first WebSocket connection)"""
        if self.subscriber_task or not REDIS_AVAILABLE:
            return

        await self._init_redis()
        if not self.redis_client:
            return

        async def subscriber():
            """Listen to Redis pub/sub and broadcast to local connections"""
            try:
                await self.redis_pubsub.subscribe('ws:broadcast')
                print("[WebSocket] Redis subscriber started")

                async for message in self.redis_pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            channel = data.get('channel')
                            payload = data.get('data')

                            # Broadcast to all local WebSocket connections
                            await self.broadcast_to_all(channel, payload)
                        except Exception as e:
                            print(f"[WebSocket] Subscriber error: {e}")
            except Exception as e:
                print(f"[WebSocket] Subscriber failed: {e}")

        self.subscriber_task = asyncio.create_task(subscriber())

    async def _publish_to_redis(self, channel: str, data: Any) -> bool:
        """
        Publish message to Redis (for multi-process broadcasting)

        Args:
            channel: Message channel
            data: Message data

        Returns:
            True if published successfully
        """
        if not REDIS_AVAILABLE:
            return False

        await self._init_redis()
        if not self.redis_client:
            return False

        try:
            message = json.dumps({'channel': channel, 'data': data})
            await self.redis_client.publish('ws:broadcast', message)
            return True
        except Exception as e:
            print(f"[WebSocket] Redis publish failed: {e}")
            return False

    async def connect(self, request: Request, ws):
        """
        Handle new WebSocket connection

        Args:
            request: Sanic request object
            ws: WebSocket connection object
        """
        # Authenticate user
        user_id = await self.guard.authenticate_websocket(request, ws)
        if not user_id:
            return
        
        # Register connection
        if user_id not in self.connections:
            self.connections[user_id] = set()

        self.connections[user_id].add(ws)

        # Start Redis subscriber on first connection (for multi-process support)
        if len(self.connections) == 1:
            await self._start_redis_subscriber()

        try:
            # Keep connection alive and handle messages
            async for message in ws:
                await self._handle_message(user_id, ws, message)

        except Exception as e:
            print(f"WebSocket error for user {user_id}: {e}")
        finally:
            await self._disconnect(user_id, ws)

    async def _handle_message(self, user_id: int, ws, message: str):
        """
        Handle incoming WebSocket message

        Args:
            user_id: User ID
            ws: WebSocket connection
            message: Raw message string
        """
        try:
            data = json.loads(message)
            action = data.get("action")

            if action == "ping":
                # Respond to ping with pong
                await self._send_to_websocket(
                    ws,
                    "pong",
                    {"timestamp": datetime.utcnow().isoformat()}
                )
            elif action == "subscribe":
                # Handle channel subscription
                channel = data.get("channel")
                await self._send_to_websocket(
                    ws,
                    "subscribed",
                    {"channel": channel}
                )

        except json.JSONDecodeError:
            await self._send_to_websocket(
                ws,
                "error",
                {"message": "Invalid JSON"}
            )
        except Exception as e:
            await self._send_to_websocket(
                ws,
                "error",
                {"message": str(e)}
            )

    async def _disconnect(self, user_id: int, ws):
        """
        Disconnect WebSocket and cleanup

        Args:
            user_id: User ID
            ws: WebSocket connection
        """
        if user_id in self.connections:
            self.connections[user_id].discard(ws)
            if not self.connections[user_id]:
                del self.connections[user_id]

    async def _send_to_websocket(self, ws, channel: str, data: Any):
        """
        Send message to a specific WebSocket

        Args:
            ws: WebSocket connection
            channel: Message channel
            data: Message data
        """
        try:
            message = json.dumps({
                "channel": channel,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            })
            await ws.send(message)
        except Exception:
            # Connection might be closed
            pass

    async def broadcast_to_user(self, user_id: int, channel: str, data: Any):
        """
        Broadcast message to all connections for a specific user

        Args:
            user_id: User ID
            channel: Message channel
            data: Message data
        """
        if user_id not in self.connections:
            return

        dead_connections = set()

        for ws in self.connections[user_id].copy():
            try:
                await self._send_to_websocket(ws, channel, data)
            except Exception:
                dead_connections.add(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.connections[user_id].discard(ws)

    async def broadcast_to_all(self, channel: str, data: Any):
        """
        Broadcast message to all connected users

        Args:
            channel: Message channel
            data: Message data
        """
        print(f"Broadcasting to {len(self.connections)} users")
        tasks = []

        for user_id in self.connections:
            tasks.append(self.broadcast_to_user(user_id, channel, data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            print("No WebSocket connections to broadcast to")