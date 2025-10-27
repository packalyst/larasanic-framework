"""
Router
Main routing class that manages route registration and resolution
"""
from typing import Union, List, Dict, Optional, Callable, Any
from larasanic.routing.route import Route
from larasanic.routing.route_collection import RouteCollection

class Router:
    def __init__(self):
        """
        Initialize the Router
        """
        self.routes = RouteCollection()
        self._group_stack: List[Dict] = []
        self._patterns: Dict[str, str] = {}  # Global parameter patterns
        self._model_bindings: Dict[str, Callable] = {}  # Model bindings
        self._current_route: Optional[Route] = None

    # =========================================================================
    # Route Registration Methods
    # =========================================================================

    def get(self, uri: str, action: Union[Callable, str, Dict] = None) -> Route:
        """
        Register a GET route
        """
        return self.add_route(['GET', 'HEAD'], uri, action)

    def post(self, uri: str, action: Union[Callable, str, Dict] = None) -> Route:
        """Register a POST route"""
        return self.add_route(['POST'], uri, action)

    def put(self, uri: str, action: Union[Callable, str, Dict] = None) -> Route:
        """Register a PUT route"""
        return self.add_route(['PUT'], uri, action)

    def patch(self, uri: str, action: Union[Callable, str, Dict] = None) -> Route:
        """Register a PATCH route"""
        return self.add_route(['PATCH'], uri, action)

    def delete(self, uri: str, action: Union[Callable, str, Dict] = None) -> Route:
        """Register a DELETE route"""
        return self.add_route(['DELETE'], uri, action)

    def options(self, uri: str, action: Union[Callable, str, Dict] = None) -> Route:
        """Register an OPTIONS route"""
        return self.add_route(['OPTIONS'], uri, action)

    def any(self, uri: str, action: Union[Callable, str, Dict] = None) -> Route:
        """
        Register a route for all HTTP methods
        """
        methods = ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
        return self.add_route(methods, uri, action)

    def match(self, methods: List[str], uri: str, action: Union[Callable, str, Dict] = None) -> Route:
        """
        Register a route for specific HTTP methods
        Args:
            methods: List of HTTP methods
            uri: Route URI
            action: Handler function, controller string, or action dict
        """
        return self.add_route(methods, uri, action)

    def add_route(self, methods: List[str], uri: str, action: Union[Callable, str, Dict]) -> Route:
        """
        Add a route to the collection

        Automatically wraps ResponseBuilder/ViewResponseBuilder objects in handlers
        """
        # Auto-wrap builders if action is not callable
        if not callable(action) and not isinstance(action, (str, dict)):
            from larasanic.support.facades.http_response import ResponseBuilder, ViewResponseBuilder

            if isinstance(action, (ResponseBuilder, ViewResponseBuilder)):
                builder = action  # Capture in closure

                # Determine handler name based on type for better debugging
                handler_name = 'view_handler' if isinstance(action, ViewResponseBuilder) else 'response_handler'

                async def handler(request):
                    return builder

                # Set the function name dynamically for stack traces
                handler.__name__ = handler_name
                action = handler

        route = self.create_route(methods, uri, action)
        return self.routes.add(route)

    def create_route(self, methods: List[str], uri: str, action: Union[Callable, str, Dict]) -> Route:
        """
        Create a new Route instance with group attributes applied
        """
        # Merge action with group attributes if it's a dict
        if isinstance(action, dict):
            action = self.merge_with_last_group(action)
        elif isinstance(action, str):
            # If it's a controller string, merge with group
            action = self.merge_with_last_group({'uses': action})

        # Create the route
        route = Route(methods, uri, action)

        # Apply group attributes from ALL groups in stack (for nested groups)
        # Process from outermost to innermost to build correct middleware chain
        if self._group_stack:
            for group in self._group_stack:
                # Apply prefix
                if 'prefix' in group:
                    route.prefix(group['prefix'])

                # Apply middleware (accumulated from all nested groups)
                if 'middleware' in group:
                    middleware = group['middleware']
                    if isinstance(middleware, str):
                        middleware = [middleware]
                    route.middleware(middleware)

                # Store group name prefix on route (will be applied when .name() is called)
                if 'as' in group:
                    route._group_name_prefix = group['as']
                    # Also apply immediately if route already has a name
                    if route.get_name():
                        route.name(group['as'] + route.get_name())
                elif 'prefix' in group and not route._group_name_prefix:
                    # If no 'as' attribute but has prefix, convert prefix to dot notation
                    # e.g., '/api/auth' -> 'api.auth.'
                    prefix_name = group['prefix'].strip('/').replace('/', '.') + '.'
                    route._group_name_prefix = prefix_name

                # Apply domain
                if 'domain' in group:
                    route.domain(group['domain'])

                # Apply namespace
                if 'namespace' in group:
                    route._namespace = group['namespace']

                # Apply where constraints
                if 'where' in group:
                    route.where(group['where'])

        # Apply global parameter patterns
        for param, pattern in self._patterns.items():
            if param in route.get_parameter_names():
                if param not in route.get_wheres():  # Don't override specific constraints
                    route.where(param, pattern)

        return route

    # =========================================================================
    # Route Grouping
    # =========================================================================

    def group(self, attributes: Dict, routes: Callable):
        """
        Usage:
            Route.group({'prefix': 'admin', 'middleware': ['auth']}, lambda: [
                Route.get('/dashboard', handler)
            ])
        """
        self._group_stack.append(attributes)

        # Execute the routes callback
        if callable(routes):
            result = routes()
            # If callback returns a list, it might be route definitions
            if isinstance(result, list):
                pass  # Routes were already registered inside the callback

        self._group_stack.pop()

    def prefix(self, prefix: str):
        """
        Create a route registrar with prefix
        """
        return RouteRegistrar(self, {'prefix': prefix})

    def middleware(self, middleware: Union[str, List[str]]):
        """Create a route registrar with middleware"""
        if isinstance(middleware, str):
            middleware = [middleware]
        return RouteRegistrar(self, {'middleware': middleware})

    def name(self, name: str):
        """Create a route registrar with name prefix"""
        return RouteRegistrar(self, {'as': name})

    def domain(self, domain: str):
        """Create a route registrar with domain"""
        return RouteRegistrar(self, {'domain': domain})

    def namespace(self, namespace: str):
        """Create a route registrar with namespace"""
        return RouteRegistrar(self, {'namespace': namespace})

    def merge_with_last_group(self, action: Dict) -> Dict:
        if not self._group_stack:
            return action

        group = self._group_stack[-1].copy()

        # Merge middleware
        if 'middleware' in group and 'middleware' in action:
            group_mw = group['middleware']
            action_mw = action['middleware']
            if isinstance(group_mw, str):
                group_mw = [group_mw]
            if isinstance(action_mw, str):
                action_mw = [action_mw]
            action['middleware'] = group_mw + action_mw

        # Merge other attributes
        group.update(action)
        return group

    # =========================================================================
    # Special Route Types
    # =========================================================================

    def redirect(self, uri: str, destination: str, status: int = 302) -> Route:
        """
        Create a redirect route
        """
        from larasanic.http import ResponseHelper

        async def redirect_handler(request):
            return ResponseHelper.redirect(destination, status=status)

        route = self.get(uri, redirect_handler)
        route.name(f'redirect.{uri.replace("/", ".")}')
        return route

    def permanent_redirect(self, uri: str, destination: str) -> Route:
        """Create a permanent redirect (301)"""
        return self.redirect(uri, destination, 301)

    def view(self, uri: str, view_name: str, data: Dict = None) -> Route:
        """
        Create a route that returns a view directly
        """
        from larasanic.helpers import view as renderView

        # Use auto-wrapping - just pass the ViewResponseBuilder directly
        return self.get(uri, renderView(view_name, data or {}))

    # =========================================================================
    # Resource Routes
    # =========================================================================

    def resource(self, name: str, controller: str, **options) -> List[Route]:
        """
        Register resource routes for a controller

        Args:
            name: Resource name (e.g., 'photos')
            controller: Controller class name
            **options: only, except, names, parameters

        Returns:
            List of created routes
        """
        from larasanic.http.resource import ResourceRegistrar

        registrar = ResourceRegistrar()
        return registrar.register(name, controller, **options)

    def api_resource(self, name: str, controller: str, **options) -> List[Route]:
        """
        Register API resource routes (without create/edit)

        Args:
            name: Resource name
            controller: Controller class name
            **options: only, except, names, parameters

        Returns:
            List of created routes
        """
        options['except'] = options.get('except', []) + ['create', 'edit']
        return self.resource(name, controller, **options)

    # =========================================================================
    # Fallback Routes
    # =========================================================================

    def fallback(self, action: Union[Callable, str]) -> Route:
        """
        Register a fallback route (404 handler)
        """
        route = self.any('/<path:path>', action)
        route.name('fallback')
        route._is_fallback = True
        return route

    # =========================================================================
    # Model Binding
    # =========================================================================

    def model(self, key: str, class_name: str, callback: Callable = None):
        """
        Register a model binding

        Args:
            key: Parameter name
            class_name: Model class name
            callback: Optional custom resolution callback
        """
        self._model_bindings[key] = {
            'class': class_name,
            'callback': callback
        }

    def bind(self, key: str, binder: Callable):
        """
        Register a custom parameter binder

        Args:
            key: Parameter name
            binder: Binding callback
        """
        self._model_bindings[key] = {
            'callback': binder
        }

    # =========================================================================
    # Global Parameter Patterns
    # =========================================================================

    def pattern(self, key: str, pattern: str):
        """
        Set a global parameter pattern

        Args:
            key: Parameter name
            pattern: Regex pattern
        """
        self._patterns[key] = pattern

    def patterns(self, patterns: Dict[str, str]):
        """
        Set multiple global parameter patterns

        Args:
            patterns: Dict of parameter patterns
        """
        self._patterns.update(patterns)

    # =========================================================================
    # Route Resolution
    # =========================================================================

    def get_routes(self) -> List[Route]:
        """Get all routes as a list"""
        return self.routes.get_routes()

    def get_collection(self) -> RouteCollection:
        """Get the route collection object"""
        return self.routes

    def get_route_by_name(self, name: str) -> Optional[Route]:
        """Get a route by name"""
        return self.routes.get_by_name(name)

    def has(self, name: str) -> bool:
        """Check if a named route exists"""
        return self.routes.has_named_route(name)

    def current(self) -> Optional[Route]:
        """Get the currently matched route"""
        return self._current_route

    def current_route_name(self) -> Optional[str]:
        """Get the current route name"""
        if self._current_route:
            return self._current_route.get_name()
        return None

    def is_current(self, name: str) -> bool:
        """Check if the current route matches the given name"""
        return self.current_route_name() == name
    
    def is_api(self) -> bool:
        """Check if the current route is api blueprint"""
        if self._current_route:
            return self._current_route.get_blueprint() == 'api'
        return False
    
    def has_prefix(self, prefix: str) -> bool:
        if self._current_route:
            return self._current_route.get_prefix() == prefix
        return False


class RouteRegistrar:
    """
    Route registrar for fluent API with route groups

    Usage:
        Route.prefix('admin').middleware(['auth']).group(lambda: [
            Route.get('/dashboard', handler)
        ])
    """

    def __init__(self, router: Router, attributes: Dict):
        """
        Initialize registrar

        Args:
            router: Router instance
            attributes: Group attributes
        """
        self.router = router
        self.attributes = attributes

    def group(self, callback: Callable):
        """Execute the group"""
        self.router.group(self.attributes, callback)
        return self

    def prefix(self, prefix: str):
        """Add prefix"""
        self.attributes['prefix'] = prefix
        return self

    def middleware(self, middleware: Union[str, List[str]]):
        """Add middleware"""
        self.attributes['middleware'] = middleware
        return self

    def name(self, name: str):
        """Add name prefix"""
        self.attributes['as'] = name
        return self

    def domain(self, domain: str):
        """Add domain"""
        self.attributes['domain'] = domain
        return self

    def namespace(self, namespace: str):
        """Add namespace"""
        self.attributes['namespace'] = namespace
        return self

    def where(self, parameter: Union[str, Dict], pattern: str = None):
        """Add parameter constraints"""
        if 'where' not in self.attributes:
            self.attributes['where'] = {}

        if isinstance(parameter, dict):
            self.attributes['where'].update(parameter)
        else:
            self.attributes['where'][parameter] = pattern
        return self
