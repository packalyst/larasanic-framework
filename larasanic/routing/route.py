"""
Route Class
Represents a single route with fluent API (Laravel-style)
"""
from typing import Union, List, Dict, Optional, Callable, Any
import re


class Route:
    """
    Route class with fluent API for defining routes

    Usage:
        route = Route(['GET'], '/users/{id}', handler)
        route.name('users.show').where('id', '[0-9]+').middleware(['auth'])
    """

    def __init__(
        self,
        methods: List[str],
        uri: str,
        action: Union[Callable, str, Dict],
        **options
    ):
        """
        Initialize a Route instance

        Args:
            methods: HTTP methods (GET, POST, etc.)
            uri: Route URI pattern
            action: Handler function, controller string, or action dict
            **options: Additional route options
        """
        self.methods = [m.upper() for m in methods]
        self.uri = uri.strip('/')
        self.action = action
        self._name: Optional[str] = None
        self._middleware: List[str] = []
        self._wheres: Dict[str, str] = {}
        self._defaults: Dict[str, Any] = {}
        self._domain: Optional[str] = None
        self._prefix: str = ''
        self._namespace: Optional[str] = None
        self._as: Optional[str] = None  # Not used - kept for potential future use
        self._group_name_prefix: Optional[str] = None  # Store group's 'as' attribute
        self._controller: Optional[str] = None
        self._compiled_uri: Optional[str] = None
        self._parameter_names: List[str] = []
        self._blueprint: Optional[str] = None  # Store blueprint name (web, api, ws)

        # Store additional options
        self._options = options

        # Extract controller and method if action is string
        if isinstance(action, str) and '@' in action:
            self._controller, method = action.split('@')
            self._action_name = method
        elif isinstance(action, dict):
            # Action dict format: {'controller': 'UserController', 'method': 'show'}
            self._controller = action.get('controller')
            self._action_name = action.get('method', action.get('uses'))
        else:
            self._action_name = getattr(action, '__name__', 'Closure')

        # Parse parameters from URI
        self._parse_parameters()

    def _parse_parameters(self):
        """Extract parameter names from URI pattern"""
        # Match {param} and {param?}
        pattern = r'\{(\w+)\??}'
        self._parameter_names = re.findall(pattern, self.uri)

    def name(self, name: str) -> 'Route':
        """
        Set the route name

        Args:
            name: Route name

        Returns:
            Self for method chaining
        """
        # Apply group name prefix if it exists and name doesn't already have it
        if self._group_name_prefix and not name.startswith(self._group_name_prefix):
            self._name = self._group_name_prefix + name
        else:
            self._name = name
        return self

    def middleware(self, middleware: Union[str, List[str]]) -> 'Route':
        """
        Add middleware to the route

        Args:
            middleware: Middleware name or list of middleware names

        Returns:
            Self for method chaining
        """
        if isinstance(middleware, str):
            middleware = [middleware]
        self._middleware.extend(middleware)
        return self

    def where(self, parameter: Union[str, Dict[str, str]], pattern: Optional[str] = None) -> 'Route':
        """
        Add parameter constraints

        Args:
            parameter: Parameter name or dict of constraints
            pattern: Regex pattern (if parameter is string)

        Returns:
            Self for method chaining

        Usage:
            route.where('id', '[0-9]+')
            route.where({'id': '[0-9]+', 'slug': '[a-z-]+'})
        """
        if isinstance(parameter, dict):
            self._wheres.update(parameter)
        elif pattern is not None:
            self._wheres[parameter] = pattern
        return self

    def whereNumber(self, parameter: str) -> 'Route':
        """Constrain parameter to be numeric"""
        return self.where(parameter, r'[0-9]+')

    def whereAlpha(self, parameter: str) -> 'Route':
        """Constrain parameter to be alphabetic"""
        return self.where(parameter, r'[a-zA-Z]+')

    def whereAlphaNumeric(self, parameter: str) -> 'Route':
        """Constrain parameter to be alphanumeric"""
        return self.where(parameter, r'[a-zA-Z0-9]+')

    def whereUuid(self, parameter: str) -> 'Route':
        """Constrain parameter to be a UUID"""
        pattern = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
        return self.where(parameter, pattern)

    def whereIn(self, parameter: str, values: List[str]) -> 'Route':
        """Constrain parameter to be one of given values"""
        escaped_values = [re.escape(v) for v in values]
        pattern = '|'.join(escaped_values)
        return self.where(parameter, f'({pattern})')

    def defaults(self, key: Union[str, Dict], value: Any = None) -> 'Route':
        """
        Set default values for parameters

        Args:
            key: Parameter name or dict of defaults
            value: Default value (if key is string)

        Returns:
            Self for method chaining
        """
        if isinstance(key, dict):
            self._defaults.update(key)
        else:
            self._defaults[key] = value
        return self

    def domain(self, domain: str) -> 'Route':
        """
        Set the domain constraint for the route

        Args:
            domain: Domain pattern (e.g., '{account}.example.com')

        Returns:
            Self for method chaining
        """
        self._domain = domain
        return self

    def prefix(self, prefix: str) -> 'Route':
        """
        Add a prefix to the route URI (accumulates for nested groups)

        Args:
            prefix: URI prefix

        Returns:
            Self for method chaining
        """
        prefix = prefix.strip('/')
        if self._prefix:
            # Accumulate prefixes for nested groups
            self._prefix = f"{self._prefix}/{prefix}"
        else:
            self._prefix = prefix
        return self

    def get_prefix(self) -> Optional[str]:
        """
        Get the prefix without blueprint name

        If prefix is 'api/auth', and blueprint is 'api', returns 'auth'
        If prefix is 'admin', and blueprint is 'web', returns 'admin'
        If prefix matches blueprint exactly, returns None

        Returns:
            Prefix without blueprint, or None
        """
        if not self._prefix:
            return None

        if not self._blueprint:
            return self._prefix

        # Split prefix by '/'
        parts = self._prefix.split('/')

        # If first part matches blueprint, remove it
        if parts[0] == self._blueprint:
            remaining = '/'.join(parts[1:])
            return remaining if remaining else None

        return self._prefix
    
    def get_name(self) -> Optional[str]:
        """Get the route name"""
        return self._name

    def get_group_name_prefix(self) -> Optional[str]:
        """Get the group name prefix (from group's 'as' attribute)"""
        return self._group_name_prefix

    def get_action_name(self) -> str:
        """Get the action name (for display)"""
        if self._controller:
            return f"{self._controller}@{self._action_name}"
        return self._action_name

    def get_uri(self) -> str:
        """Get the full URI with prefix and blueprint prefix"""
        # Build URI from prefix + uri
        if self._prefix:
            uri = f"{self._prefix}/{self.uri}".strip('/')
        else:
            uri = self.uri or '/'

        # Add blueprint prefix if exists (and not already present)
        if self._blueprint:
            blueprint_prefixes = {'api': 'api', 'ws': 'ws'}
            blueprint_prefix = blueprint_prefixes.get(self._blueprint)
            if blueprint_prefix and not uri.startswith(f"{blueprint_prefix}/"):
                uri = f"{blueprint_prefix}/{uri}".strip('/')

        return uri

    def get_compiled_uri(self) -> str:
        """
        Get URI with constraints applied (for Sanic routing)

        Converts Laravel-style {id} to Sanic-style <id:int> based on constraints
        """
        if self._compiled_uri is not None:
            return self._compiled_uri

        uri = self.get_uri()

        # Convert {param} to <param> or <param:type> based on constraints
        def convert_param(match):
            param_name = match.group(1)
            is_optional = match.group(0).endswith('?}')

            # Check if we have a constraint for this parameter
            if param_name in self._wheres:
                constraint = self._wheres[param_name]

                # Map common constraints to Sanic types
                if constraint == r'[0-9]+':
                    param_type = 'int'
                elif constraint.startswith(r'[0-9a-fA-F]{8}'):  # UUID
                    param_type = 'uuid'
                elif constraint == r'[a-zA-Z0-9\-]+':
                    param_type = 'slug'
                elif constraint == r'.*':
                    param_type = 'path'
                else:
                    # For custom regex, use Sanic's regex format: <name:ymd>
                    # where ymd is defined in app.router.regex()
                    # Since we can't dynamically register regex patterns,
                    # we'll just use 'str' and warn about the limitation
                    param_type = 'str'
                    # TODO: Add custom regex support via Sanic's regex() method
            else:
                # Default to string type
                param_type = 'str'

            # Format for Sanic
            if param_type == 'str':
                return f"<{param_name}>"
            else:
                return f"<{param_name}:{param_type}>"

        # Replace {param} and {param?} patterns
        self._compiled_uri = re.sub(r'\{(\w+)\??}', convert_param, uri)
        return self._compiled_uri

    def get_middleware(self) -> List[str]:
        """Get route middleware"""
        return self._middleware

    def get_methods(self) -> List[str]:
        """Get HTTP methods"""
        return self.methods

    def get_action(self) -> Union[Callable, str, Dict]:
        """Get route action"""
        return self.action

    def get_parameter_names(self) -> List[str]:
        """Get parameter names from URI"""
        return self._parameter_names

    def get_wheres(self) -> Dict[str, str]:
        """Get parameter constraints"""
        return self._wheres

    def get_defaults(self) -> Dict[str, Any]:
        """Get default parameter values"""
        return self._defaults

    def get_domain(self) -> Optional[str]:
        """Get domain constraint"""
        return self._domain

    def get_blueprint(self) -> Optional[str]:
        """Get blueprint name"""
        return self._blueprint

    def set_blueprint(self, blueprint: str) -> 'Route':
        """
        Set the blueprint name

        Args:
            blueprint: Blueprint name (web, api, ws, etc.)

        Returns:
            Self for method chaining
        """
        self._blueprint = blueprint
        return self

    def has_parameters(self) -> bool:
        """Check if route has parameters"""
        return len(self._parameter_names) > 0

    def parameter_count(self) -> int:
        """Get number of parameters"""
        return len(self._parameter_names)

    def matches(self, uri: str, method: str) -> bool:
        """
        Check if route matches given URI and method

        Args:
            uri: Request URI
            method: HTTP method

        Returns:
            True if route matches
        """
        if method.upper() not in self.methods:
            return False

        # Simple pattern matching (Sanic handles the actual routing)
        pattern = self.get_compiled_uri()
        # Convert Sanic pattern to regex for matching
        regex_pattern = re.sub(r'<(\w+):?(\w+)?>', r'(?P<\1>[^/]+)', pattern)
        regex_pattern = '^' + regex_pattern + '$'

        return re.match(regex_pattern, uri.strip('/')) is not None

    def bind(self, request):
        """
        Bind the route to a request (for model binding)

        Args:
            request: Sanic request object

        Returns:
            Self for method chaining
        """
        # This will be implemented when we add model binding
        return self

    def __repr__(self) -> str:
        """String representation of route"""
        methods_str = '|'.join(self.methods)
        name_str = f" (name: {self._name})" if self._name else ""
        return f"<Route [{methods_str}] {self.get_uri()}{self.get_blueprint()}{name_str}>"
