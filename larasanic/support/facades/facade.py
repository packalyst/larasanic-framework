"""
Facade System
Laravel-style facade pattern for static-like access to services
"""
from typing import  Any, Optional
from contextvars import ContextVar
from sanic.request import Request

# Global application instance storage
_app_instance: Optional[Any] = None

# Context-aware request storage (thread-safe for async)
_current_request: ContextVar[Optional[Any]] = ContextVar('current_request', default=None)


class FacadeMeta(type):
    """Metaclass for Facade to enable __class_getattr__ and __class_setattr__"""

    def __getattr__(cls, name: str) -> Any:
        """
        Magic method to proxy attribute/method access to the facade root

        Args:
            name: Attribute/method name

        Returns:
            Attribute or method from underlying instance
        """
        instance = cls.get_facade_root()
        return getattr(instance, name)

    def __setattr__(cls, name: str, value: Any) -> None:
        """
        Magic method to proxy attribute setting to the facade root

        If the attribute exists on the underlying instance, set it there.
        Otherwise, set it on the facade class itself.

        Args:
            name: Attribute name
            value: Value to set
        """
        # Don't proxy class-level methods (but allow private attributes like _current_route)
        if name in ('get_facade_accessor', 'get_facade_root',
                    'get_app', 'set_app', 'get_current_request',
                    'set_current_request', 'clear_current_request', 'get_sanic'):
            type.__setattr__(cls, name, value)
            return

        try:
            instance = cls.get_facade_root()
            # Check if attribute exists on instance
            if hasattr(instance, name):
                setattr(instance, name, value)
            else:
                # Set on facade class itself
                type.__setattr__(cls, name, value)
        except (RuntimeError, NotImplementedError):
            # If we can't get facade root, set on class
            type.__setattr__(cls, name, value)


class Facade(metaclass=FacadeMeta):
    """
    Base Facade class

    Provides Laravel-style static access to underlying service instances.
    Subclasses must implement get_facade_accessor() to specify which
    service to resolve from the application container.

    Example:
        class Auth(Facade):
            @classmethod
            def get_facade_accessor(cls):
                return 'auth_service'

        # Usage:
        user = await Auth.get_user_by_id(1)
        token = Auth.generate_token(user_id)
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        """
        Get the accessor name for the facade

        Returns:
            Service name to resolve from container

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError(
            f"Facade {cls.__name__} does not implement get_facade_accessor()"
        )

    @classmethod
    def get_facade_root(cls) -> Any:
        """
        Get the root object behind the facade

        Returns:
            The underlying service instance

        Raises:
            RuntimeError: If application is not set
        """
        accessor = cls.get_facade_accessor()

        # Get application instance
        app = cls.get_app()

        if not app:
            raise RuntimeError(
                f"Facade {cls.__name__} cannot access application. "
                "Make sure to call Facade.set_app(app) during bootstrap."
            )

        # Resolve from container
        return app.make(accessor)
    
    @classmethod
    def get_app(cls):
        """
        Get the application instance

        Returns:
            Application instance or None
        """
        return _app_instance
    
    @classmethod
    def set_app(cls, app):
        """
        Set the application instance (called during bootstrap)

        Args:
            app: Application instance
        """
        global _app_instance
        _app_instance = app
        from larasanic.package_manager import PackageManager
        package_manager = PackageManager()
        package_manager.discover()
        app.singleton('package_manager', package_manager)
        

    @classmethod
    def get_current_request(cls):
        """
        Get the current request from context

        Returns:
            Current request or None
        """
        return _current_request.get()

    @classmethod
    async def set_current_request(cls, request: Request):
        """
        Set the current request in context (for request-scoped data)
        Args:
            request: Sanic request object
        """
        if not request or not isinstance(request, Request):
            raise RuntimeError(
                "No active request context or invalid request type."
            )

        _current_request.set(request)

        # Analyze request and store in ctx for access via HttpRequest facade
        # Import here to avoid circular dependency
        from larasanic.support.facades import HttpRequest,Route,Auth
        from larasanic.support import Config,Str

        request.ctx._request_analysis = HttpRequest._handle_spa_request()

        # Check if route exists (it's None for 404 errors)
        if request.route and request.route.name:
            route_name = request.route.name.replace(f"{Str.snake(Config.get('app.app_name'))}.", '')
            route_obj = Route.routes.get_by_name(route_name)
        else:
            route_obj = None

        if route_obj:
            # Set in Route facade for global access
            Route._current_route = route_obj
            
            # Set in request context via HttpRequest facade
            HttpRequest.set('route', route_obj)
            HttpRequest.set('route_name', route_obj.get_name())

        if route_obj.get_blueprint() != 'static':
            user = await Auth.get_user_from_token()
            
            HttpRequest.set_user(user)

    @classmethod
    def clear_current_request(cls):
        """Clear the current request from context"""
        _current_request.set(None)