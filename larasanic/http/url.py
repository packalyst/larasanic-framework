"""
URL Generator
Generates URLs from named routes and paths (Laravel-style)

Moved from larasanic.routing to framework.http as URL generation
is more about HTTP/web concerns than routing logic.
"""
from typing import Dict, Optional, Union, List, Any
from urllib.parse import urlencode
import re

class UrlGenerator:
    """
    Usage:
        generator = UrlGenerator()
        url = generator.route('users.show', {'user': 1})  # /users/1
    """

    def __init__(self):
        """
        Initialize URL generator
        """
        self._forced_scheme: Optional[str] = None
        self._forced_root: Optional[str] = None

    @property
    def router(self):
        """Get router from Route facade dynamically"""
        from larasanic.support.facades import Route
        return Route.get_facade_root()

    def to(self, path: str, parameters: Dict = None, secure: Optional[bool] = None) -> str:
        """
        Generate a URL for the given path

        Args:
            path: URI path
            parameters: Query parameters
            secure: Use HTTPS (None = auto-detect from request)

        Returns:
            Full URL
        """
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path

        # Add query parameters
        if parameters:
            query_string = urlencode(parameters)
            path = f"{path}?{query_string}"

        # Return absolute URL (using HttpRequest facade for context)
        try:
            scheme = self._get_scheme(secure)
            root = self._get_root_url(scheme)
            if root:
                return f"{root}{path}"
        except:
            pass

        return path

    def route(self, name: str, parameters: Dict = None, absolute: bool = True) -> str:
        """
        Generate a URL for a named route

        Args:
            name: Route name
            parameters: Route parameters
            absolute: Return absolute URL (default True)

        Returns:
            URL string

        Raises:
            ValueError: If route name doesn't exist

        Usage:
            url = generator.route('users.show', {'user': 1})
            url = generator.route('posts.index')
        """
        route = self.router.get_route_by_name(name)

        if not route:
            raise ValueError(f"Route [{name}] not found")

        return self.to_route(route, parameters or {}, absolute)

    def to_route(self, route, parameters: Dict = None, absolute: bool = True) -> str:
        """
        Generate URL for a route instance

        Args:
            route: Route instance
            parameters: Route parameters
            absolute: Return absolute URL

        Returns:
            URL string
        """
        uri = route.get_uri()
        parameters = parameters or {}

        # Replace route parameters with values
        uri = self._replace_route_parameters(uri, parameters)

        # Add any remaining parameters as query string
        query_params = self._get_query_parameters(route, parameters)

        if query_params:
            query_string = urlencode(query_params)
            uri = f"{uri}?{query_string}"

        if absolute:
            try:
                scheme = self._get_scheme()
                root = self._get_root_url(scheme)
                if root:
                    return f"{root}/{uri}"
            except:
                pass

        return f"/{uri}"

    def _replace_route_parameters(self, uri: str, parameters: Dict) -> str:
        """
        Replace route parameters in URI with actual values

        Args:
            uri: Route URI pattern (supports both Sanic <param> and {param} syntax)
            parameters: Parameter values

        Returns:
            URI with parameters replaced
        """
        # Track which parameters we've used
        used_params = set()

        def replace_param(match):
            param_name = match.group(1).split(':')[0]  # Handle <page:path> -> page
            used_params.add(param_name)

            if param_name in parameters:
                value = parameters[param_name]
                # Handle model instances
                if hasattr(value, 'id'):
                    return str(value.id)
                elif hasattr(value, 'get_route_key'):
                    return str(value.get_route_key())
                else:
                    return str(value)
            else:
                # Parameter not provided, leave placeholder
                return match.group(0)

        # Replace both Sanic syntax <param> and <param:type> and standard {param} and {param?}
        result = re.sub(r'<(\w+):?\w*>', replace_param, uri)  # Sanic: <version> or <page:path>
        result = re.sub(r'\{(\w+)\??}', replace_param, result)  # Standard: {version} or {version?}

        # Store used parameters so we can add the rest as query params
        for param in used_params:
            parameters.pop(param, None)

        return result

    def _get_query_parameters(self, route, parameters: Dict) -> Dict:
        """
        Get parameters that should be added as query string

        Args:
            route: Route instance
            parameters: All parameters

        Returns:
            Query parameters dict
        """
        # Any parameters that weren't used in the route should be query params
        route_params = route.get_parameter_names()
        query_params = {}

        for key, value in parameters.items():
            if key not in route_params:
                query_params[key] = value

        return query_params

    def _get_scheme(self, secure: Optional[bool] = None) -> str:
        """
        Get URL scheme (http/https)

        Args:
            secure: Force HTTPS if True

        Returns:
            Scheme string
        """
        if self._forced_scheme:
            return self._forced_scheme

        if secure is not None:
            return 'https' if secure else 'http'

        # Auto-detect from request (using HttpRequest facade)
        from larasanic.support.facades import HttpRequest
        try:
            return HttpRequest.scheme()
        except:
            return 'http'

    def _get_root_url(self, scheme: str = None) -> str:
        """
        Get root URL (scheme + host)

        Args:
            scheme: URL scheme

        Returns:
            Root URL
        """
        if self._forced_root:
            return self._forced_root

        # Get from request context (using HttpRequest facade)
        from larasanic.support.facades import HttpRequest
        try:
            scheme = scheme or self._get_scheme()
            host = HttpRequest.host()
            if host:
                return f"{scheme}://{host}"
        except:
            pass

        return ''

    def current(self) -> str:
        """
        Get current URL

        Returns:
            Current request URL
        """
        from larasanic.support.facades import HttpRequest
        try:
            root = self._get_root_url()
            path = HttpRequest.path()
            return f"{root}{path}"
        except:
            return ''

    def previous(self, fallback: str = '/') -> str:
        """
        Get previous URL (from referrer)

        Args:
            fallback: Fallback URL if no referrer

        Returns:
            Previous URL
        """
        from larasanic.support.facades import HttpRequest
        try:
            return HttpRequest.referer() or fallback
        except:
            return fallback

    def full(self) -> str:
        """
        Get current URL with query string

        Returns:
            Full current URL
        """
        from larasanic.support.facades import HttpRequest
        try:
            url = self.current()
            query = HttpRequest.query_string()
            if query:
                url = f"{url}?{query}"
            return url
        except:
            return ''

    def force_scheme(self, scheme: str):
        """
        Force URL scheme for generated URLs

        Args:
            scheme: URL scheme (http or https)
        """
        self._forced_scheme = scheme

    def force_root_url(self, root: str):
        """
        Force root URL for generated URLs

        Args:
            root: Root URL (e.g., 'https://example.com')
        """
        self._forced_root = root.rstrip('/')

    def is_valid_url(self, path: str) -> bool:
        """
        Check if a path is a valid URL

        Args:
            path: Path to check

        Returns:
            True if valid URL
        """
        return path.startswith(('http://', 'https://', '//'))

    def action(self, action: str, parameters: Dict = None, absolute: bool = True) -> str:
        """
        Generate URL for a controller action

        Args:
            action: Controller action (e.g., 'UserController@show')
            parameters: Parameters
            absolute: Return absolute URL

        Returns:
            URL string
        """
        # Find route by action
        route = self.router.routes.get_by_action(action)

        if not route:
            raise ValueError(f"Action [{action}] not found")

        return self.to_route(route, parameters or {}, absolute)

    def signed_route(self, name: str, parameters: Dict = None, expiration: int = None) -> str:
        """
        Generate a signed URL for a named route

        Args:
            name: Route name
            parameters: Route parameters
            expiration: Expiration time in seconds (optional)

        Returns:
            Signed URL

        Note: Implementation requires signature generation
        """
        # TODO: Implement URL signing
        url = self.route(name, parameters, absolute=True)
        return url  # Placeholder
