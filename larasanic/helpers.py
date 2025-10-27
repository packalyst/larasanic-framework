"""
Framework Helper Functions
Centralized user-facing helpers for easy access throughout the application
"""
from typing import Any, Optional, Dict, Union, List


# ==============================================================================
# Session Helpers
# ==============================================================================

def session(key: str = None, default: Any = None) -> Any:
    """
    Get session value or session manager

    Args:
        key: Session key (optional)
        default: Default value if key not found

    Returns:
        Session value or session manager

    Example:
        session('user_id')
        session('cart', [])
        session()
    """
    from larasanic.support.facades import HttpRequest

    sess = HttpRequest.get_session()
    if sess is None:
        raise RuntimeError("Session not available. Make sure SessionMiddleware is registered.")

    if key is None:
        return sess

    return sess.get(key, default)


# ==============================================================================
# Response Helpers
# ==============================================================================

def response(content: Any = None):
    """
    Create a fluent response builder

    Args:
        content: Response content

    Returns:
        ResponseBuilder instance

    Example:
        return response({'user': 'John'}) \\
            .header('X-Custom', 'value') \\
            .status(200)
    """
    from larasanic.support.facades.http_response import ResponseBuilder
    return ResponseBuilder(content)


def view(template: str = None, context: Optional[Dict[str, Any]] = None):
    """
    Create a view response builder

    Args:
        template: Template name
        context: Template context

    Returns:
        ViewResponseBuilder instance

    Example:
        return view('pages.home', {'data': data})
    """
    from larasanic.support.facades.http_response import ViewResponseBuilder
    return ViewResponseBuilder(template, context)


# ==============================================================================
# URL Helpers
# ==============================================================================

def route(name: str, parameters: dict = None, absolute: bool = True) -> str:
    """
    Generate URL for named route

    Args:
        name: Route name
        parameters: Route parameters
        absolute: Generate absolute URL

    Returns:
        Generated URL

    Example:
        route('users.show', {'id': 1})
    """
    from larasanic.support.facades import URL
    return URL.route(name, parameters or {}, absolute)


def url(path: str, parameters: dict = None, secure: bool = None) -> str:
    """
    Generate URL for path

    Args:
        path: URL path
        parameters: Query parameters
        secure: Use HTTPS

    Returns:
        Generated URL

    Example:
        url('/users', {'page': 2})
    """
    try:
        from larasanic.support.facades import URL
        return URL.to(path, parameters, secure)
    except Exception as e:
        # Fallback if URL generator not initialized
        if not path:
            return '/'
        path = f"/{path.lstrip('/')}"
        if parameters:
            from urllib.parse import urlencode
            query_string = urlencode(parameters)
            path = f"{path}?{query_string}"
        return path
    


def asset(path: str) -> str:
    """
    Generate URL for static asset

    Args:
        path: Asset path

    Returns:
        Asset URL

    Example:
        asset('css/app.css')
    """
    if not path:
        return ''
    return f"/static/{path.lstrip('/')}"


# ==============================================================================
# String Helpers
# ==============================================================================

def snake_case(value: str) -> str:
    """
    Convert string to snake_case

    Args:
        value: String to convert

    Returns:
        Snake cased string

    Example:
        snake_case('FrameworkApp')  # 'framework_app'
    """
    from larasanic.support import Str
    return Str.snake(value)


def camel_case(value: str) -> str:
    """
    Convert string to camelCase

    Args:
        value: String to convert

    Returns:
        Camel cased string

    Example:
        camel_case('framework_app')  # 'frameworkApp'
    """
    from larasanic.support import Str
    return Str.camel(value)


def studly_case(value: str) -> str:
    """
    Convert string to StudlyCase

    Args:
        value: String to convert

    Returns:
        Studly cased string

    Example:
        studly_case('framework_app')  # 'FrameworkApp'
    """
    from larasanic.support import Str
    return Str.studly(value)


def kebab_case(value: str) -> str:
    """
    Convert string to kebab-case

    Args:
        value: String to convert

    Returns:
        Kebab cased string

    Example:
        kebab_case('FrameworkApp')  # 'framework-app'
    """
    from larasanic.support import Str
    return Str.kebab(value)


def str_slug(value: str, separator: str = '-') -> str:
    """
    Generate URL-friendly slug

    Args:
        value: String to convert
        separator: Separator character

    Returns:
        Slug string

    Example:
        str_slug('Framework App!')  # 'framework-app'
    """
    from larasanic.support import Str
    return Str.slug(value, separator)


# ==============================================================================
# Auth Helpers
# ==============================================================================

def auth():
    """
    Get the Auth facade instance

    Returns:
        Auth facade for authentication operations

    Example:
        auth().user()
        auth().check()
        auth().id()
    """
    from larasanic.support.facades import Auth
    return Auth


# ==============================================================================
# Validation Helpers
# ==============================================================================

def make_validator(
    data: Dict[str, Any],
    rules: Dict[str, Union[str, List[str]]],
    messages: Optional[Dict[str, str]] = None
):
    """
    Create a Validator instance

    Args:
        data: Data to validate
        rules: Validation rules
        messages: Custom error messages

    Returns:
        Validator instance

    Example:
        validator = make_validator(
            data=request.json,
            rules={'email': 'required|email'}
        )
    """
    from larasanic.validation import Validator
    return Validator(data, rules, messages)


# Helper functions for broadcasting
async def notify_user(user_id: int, level: str, title: str, message: str):
    """
    Send notification to a specific user

    Args:
        ws_manager: WebSocketManager instance
        user_id: User ID
        level: Notification level (info, success, warning, error)
        title: Notification title
        message: Notification message
    """
    from larasanic.websocket.ws_channels import WSChannel
    from larasanic.support.facades import WebSocket

    notification = {
        "level": level,
        "title": title,
        "message": message
    }
    await WebSocket.broadcast_to_user(user_id, WSChannel.NOTIFY.value, notification)


# Global WebSocketManager instance for CLI context (lazy initialization)
_cli_ws_manager = None

async def broadcast_to_channel(channel: str, data: Any):
    """
    Broadcast message to WebSocket channel via Redis pub/sub

    Works in both web and CLI contexts. Tries to use facade first,
    falls back to instantiating WebSocketManager directly if facade unavailable.

    Args:
        channel: WebSocket channel
        data: Data to broadcast
    """
    try:
        # Try to use facade first (web context)
        from larasanic.support.facades import WebSocket
        redis_success = await WebSocket._publish_to_redis(channel, data)

        # Fallback to local broadcast if Redis unavailable and we have connections
        if not redis_success and len(WebSocket.connections) > 0:
            await WebSocket.broadcast_to_all(channel, data)
    except (RuntimeError, AttributeError):
        # Facade not available (CLI context) - use cached WebSocketManager instance
        global _cli_ws_manager

        if _cli_ws_manager is None:
            from larasanic.websocket.ws_manager import WebSocketManager

            # Create minimal WebSocketManager instance (ws_guard not needed for publishing)
            _cli_ws_manager = WebSocketManager(ws_guard=None)

            # Initialize Redis connection
            await _cli_ws_manager._init_redis()

        # Publish to Redis
        await _cli_ws_manager._publish_to_redis(channel, data)


