"""
Route Middleware Registry
Laravel-style route middleware management system
"""
from typing import Callable, List, Optional, Dict
from functools import wraps
from larasanic.middleware.base_middleware import Middleware

class RouteMiddlewareRegistry:
    def __init__(self):
        """Initialize empty registry"""
        self._middleware: Dict[str, Middleware] = {}

    def register(self, name: str, middleware_instance: Middleware):
        self._middleware[name] = middleware_instance

    def get(self, name: str) -> Optional[Middleware]:
        return self._middleware.get(name)

    def has(self, name: str) -> bool:
        return name in self._middleware

    def wrap_handler(self, handler: Callable, middleware_names: List[str]) -> Callable:
        if not middleware_names:
            return handler

        # Apply in reverse order so execution order matches list order
        # ['auth', 'verified'] becomes: auth(verified(handler))
        # When executed: auth runs first, then verified, then handler
        wrapped = handler
        for name in reversed(middleware_names):
            middleware = self.get(name)
            if middleware:
                wrapped = self._create_wrapper(wrapped, middleware, name)
            else:
                print(f"⚠️  Warning: Route middleware '{name}' not found in registry")

        return wrapped

    def _create_wrapper(self, handler: Callable, middleware: Middleware, name: str) -> Callable:
        @wraps(handler)
        async def wrapper(request, *args, **kwargs):
            # Call middleware's before_request hook
            result = await middleware.before_request(request)

            if result is not None:
                # Middleware returned a response early (auth failed, etc.)
                # STOP the pipeline here - don't call next handler
                return result

            # Middleware passed - continue to next middleware/handler
            response = await handler(request, *args, **kwargs)

            # Call middleware's after_response hook
            # Allows middleware to modify the response
            response = await middleware.after_response(request, response)

            return response

        # Add metadata for debugging
        wrapper._middleware_name = name
        return wrapper

    def get_registered(self) -> List[str]:
        return list(self._middleware.keys())
