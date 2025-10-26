"""
Route Collection
Manages a collection of routes with lookup capabilities
"""
from typing import Dict, List, Optional
from larasanic.routing.route import Route


class RouteCollection:
    """
    Collection of routes with name-based and method-based lookup

    Provides efficient route lookup by name, method, and URI
    """

    def __init__(self):
        """Initialize an empty route collection"""
        self._routes: List[Route] = []
        self._routes_by_name: Dict[str, Route] = {}
        self._routes_by_method: Dict[str, List[Route]] = {
            'GET': [],
            'POST': [],
            'PUT': [],
            'PATCH': [],
            'DELETE': [],
            'OPTIONS': [],
            'HEAD': []
        }
        self._all_routes: Dict[str, Route] = {}

    def add(self, route: Route) -> Route:
        """
        Add a route to the collection

        Args:
            route: Route instance

        Returns:
            The added route
        """
        # Don't check for duplicates - routes can have same URI in different blueprints
        # Sanic will handle actual duplicate route registration
        self._routes.append(route)

        # Index by name if route has one
        if route.get_name():
            # Check for duplicate names
            if route.get_name() in self._routes_by_name:
                existing = self._routes_by_name[route.get_name()]
                print(f"⚠️  Duplicate route name: {route.get_name()}")
                print(f"    Existing URI: {existing.get_uri()}")
                print(f"    New URI: {route.get_uri()}")
            self._routes_by_name[route.get_name()] = route

        # Index by methods
        for method in route.get_methods():
            if method in self._routes_by_method:
                self._routes_by_method[method].append(route)

        # Index by URI + method combination (for fast lookup)
        for method in route.get_methods():
            key = f"{method}:{route.get_uri()}"
            self._all_routes[key] = route

        return route

    def get_by_name(self, name: str) -> Optional[Route]:
        """
        Get route by name

        Args:
            name: Route name

        Returns:
            Route instance or None
        """
        return self._routes_by_name.get(name)

    def get_by_method(self, method: str) -> List[Route]:
        """
        Get all routes for a specific HTTP method

        Args:
            method: HTTP method (GET, POST, etc.)

        Returns:
            List of routes
        """
        return self._routes_by_method.get(method.upper(), [])

    def get_by_action(self, action: str) -> Optional[Route]:
        """
        Get route by action (controller@method)

        Args:
            action: Action string (e.g., 'UserController@show')

        Returns:
            Route instance or None
        """
        for route in self._routes:
            if route.get_action_name() == action:
                return route
        return None

    def match(self, uri: str, method: str) -> Optional[Route]:
        """
        Find a route that matches the URI and method

        Args:
            uri: Request URI
            method: HTTP method

        Returns:
            Matching route or None
        """
        # Try exact match first (fast path)
        key = f"{method.upper()}:{uri.strip('/')}"
        if key in self._all_routes:
            return self._all_routes[key]

        # Try pattern matching (slower path)
        for route in self.get_by_method(method):
            if route.matches(uri, method):
                return route

        return None

    def get_routes(self) -> List[Route]:
        """Get all routes"""
        return self._routes

    def get_routes_by_uri(self, uri: str) -> List[Route]:
        """
        Get all routes for a specific URI (across all methods)

        Args:
            uri: Route URI

        Returns:
            List of routes
        """
        return [route for route in self._routes if route.get_uri() == uri.strip('/')]

    def has_named_route(self, name: str) -> bool:
        """Check if a named route exists"""
        return name in self._routes_by_name

    def count(self) -> int:
        """Get total number of routes"""
        return len(self._routes)

    def refresh_name_lookups(self):
        """Refresh the name-based lookup index"""
        self._routes_by_name.clear()
        for route in self._routes:
            if route.get_name():
                self._routes_by_name[route.get_name()] = route

    def refresh_method_lookups(self):
        """Refresh the method-based lookup index"""
        for method in self._routes_by_method:
            self._routes_by_method[method] = []

        for route in self._routes:
            for method in route.get_methods():
                if method in self._routes_by_method:
                    self._routes_by_method[method].append(route)

    def clear(self):
        """Clear all routes from the collection"""
        self._routes.clear()
        self._routes_by_name.clear()
        self._all_routes.clear()
        for method in self._routes_by_method:
            self._routes_by_method[method] = []

    def __iter__(self):
        """Make collection iterable"""
        return iter(self._routes)

    def __len__(self):
        """Get number of routes"""
        return len(self._routes)

    def to_dict(self) -> Dict[str, any]:
        """
        Convert route collection to a beautiful dictionary representation

        Returns:
            Dict with route information organized by name, method, and metadata
        """
        routes_list = []

        for route in self._routes:
            route_dict = {
                'name': route.get_name(),
                'uri': route.get_uri(),
                'methods': route.get_methods(),
                'action': route.get_action_name(),
                'middleware': route.get_middleware(),
                'parameters': route.get_parameter_names(),
            }

            # Add optional fields if they exist
            if route.get_blueprint():
                route_dict['blueprint'] = route.get_blueprint()

            if route.get_domain():
                route_dict['domain'] = route.get_domain()

            if route.get_wheres():
                route_dict['constraints'] = route.get_wheres()

            if route.get_defaults():
                route_dict['defaults'] = route.get_defaults()

            routes_list.append(route_dict)

        return {
            'total': len(self._routes),
            'routes': routes_list,
            'by_method': {
                method: len(routes)
                for method, routes in self._routes_by_method.items()
                if routes
            },
            'named_routes': len(self._routes_by_name),
        }

    def __repr__(self):
        """String representation"""
        return f"<RouteCollection ({len(self._routes)} routes)>"
