"""
Resource Registrar
Registers RESTful resource routes (Laravel-style)

Moved from larasanic.routing to framework.http as resource registration
is more about HTTP CRUD operations than routing logic.
"""
from typing import List, Dict, Optional
from larasanic.routing.route import Route


class ResourceRegistrar:
    """
    Registers RESTful resource routes for controllers

    Automatically creates standard CRUD routes following Laravel conventions.
    Uses Route facade to access router dynamically.

    Usage:
        registrar = ResourceRegistrar()
        registrar.register('photos', 'PhotoController')
    """

    # Resource route definitions
    RESOURCE_METHODS = [
        'index',    # GET    /photos
        'create',   # GET    /photos/create
        'store',    # POST   /photos
        'show',     # GET    /photos/{photo}
        'edit',     # GET    /photos/{photo}/edit
        'update',   # PUT    /photos/{photo}
        'destroy',  # DELETE /photos/{photo}
    ]

    def __init__(self):
        """
        Initialize resource registrar

        Note: Uses Route facade to access router dynamically
        """
        self._parameters: Dict[str, str] = {}  # Custom parameter names

    @property
    def router(self):
        """Get router from Route facade dynamically"""
        from larasanic.support.facades import Route as RouteFacade
        return RouteFacade.get_facade_root()

    def register(self, name: str, controller: str, **options) -> List[Route]:
        """
        Register resource routes

        Args:
            name: Resource name (e.g., 'photos', 'admin/posts')
            controller: Controller class name
            **options:
                - only: List of methods to include
                - except: List of methods to exclude
                - names: Custom route names
                - parameters: Custom parameter names
                - middleware: Middleware to apply
                - shallow: Use shallow nesting

        Returns:
            List of created routes

        Usage:
            registrar.register('photos', 'PhotoController')
            registrar.register('photos', 'PhotoController', only=['index', 'show'])
            registrar.register('photos', 'PhotoController', names={'index': 'photos.list'})
        """
        # Get methods to register
        methods = self._get_resource_methods(options)

        # Custom parameter name for this resource
        parameter = options.get('parameter', name.split('/')[-1])
        self._parameters[name] = parameter

        # Custom route names
        names = options.get('names', {})

        # Create routes for each method
        routes = []

        for method in methods:
            route = self._add_resource_route(name, controller, method, names)
            if route:
                # Apply middleware if specified
                if 'middleware' in options:
                    middleware = options['middleware']
                    if isinstance(middleware, str):
                        middleware = [middleware]
                    route.middleware(middleware)

                routes.append(route)

        return routes

    def _get_resource_methods(self, options: Dict) -> List[str]:
        """
        Get methods to register based on options

        Args:
            options: Registration options

        Returns:
            List of method names
        """
        methods = self.RESOURCE_METHODS.copy()

        # Apply 'only' filter
        if 'only' in options:
            only = options['only']
            if isinstance(only, str):
                only = [only]
            methods = [m for m in methods if m in only]

        # Apply 'except' filter
        if 'except' in options:
            exclude = options['except']
            if isinstance(exclude, str):
                exclude = [exclude]
            methods = [m for m in methods if m not in exclude]

        return methods

    def _add_resource_route(
        self,
        name: str,
        controller: str,
        method: str,
        custom_names: Dict = None
    ) -> Optional[Route]:
        """
        Add a single resource route

        Args:
            name: Resource name
            controller: Controller class name
            method: Method name (index, show, etc.)
            custom_names: Custom route names

        Returns:
            Created Route instance
        """
        custom_names = custom_names or {}
        parameter = self._parameters.get(name, name.split('/')[-1])

        # Build route definition
        route_name = custom_names.get(method, f"{name}.{method}")
        action = f"{controller}@{method}"

        if method == 'index':
            # GET /photos
            return self.router.get(name, action).name(route_name)

        elif method == 'create':
            # GET /photos/create
            return self.router.get(f"{name}/create", action).name(route_name)

        elif method == 'store':
            # POST /photos
            return self.router.post(name, action).name(route_name)

        elif method == 'show':
            # GET /photos/{photo}
            return self.router.get(f"{name}/{{{parameter}}}", action).name(route_name)

        elif method == 'edit':
            # GET /photos/{photo}/edit
            return self.router.get(f"{name}/{{{parameter}}}/edit", action).name(route_name)

        elif method == 'update':
            # PUT /photos/{photo}
            # Also register PATCH method
            route = self.router.match(['PUT', 'PATCH'], f"{name}/{{{parameter}}}", action)
            route.name(route_name)
            return route

        elif method == 'destroy':
            # DELETE /photos/{photo}
            return self.router.delete(f"{name}/{{{parameter}}}", action).name(route_name)

        return None

    def api_register(self, name: str, controller: str, **options) -> List[Route]:
        """
        Register API resource routes (excludes create and edit)

        Args:
            name: Resource name
            controller: Controller class name
            **options: Same as register()

        Returns:
            List of created routes

        Usage:
            registrar.api_register('posts', 'PostController')
        """
        # Exclude create and edit methods
        exclude = options.get('except', [])
        if isinstance(exclude, str):
            exclude = [exclude]

        exclude.extend(['create', 'edit'])
        options['except'] = list(set(exclude))  # Remove duplicates

        return self.register(name, controller, **options)

    def singleton_register(self, name: str, controller: str, **options) -> List[Route]:
        """
        Register singleton resource routes

        For resources that only have one instance (e.g., profile, settings)
        Excludes index method and doesn't use ID parameters

        Args:
            name: Resource name
            controller: Controller class name
            **options: Same as register()

        Returns:
            List of created routes

        Usage:
            registrar.singleton_register('profile', 'ProfileController')
        """
        # Singleton resources exclude 'index' and don't need {id}
        exclude = options.get('except', [])
        if isinstance(exclude, str):
            exclude = [exclude]

        exclude.append('index')
        options['except'] = list(set(exclude))

        routes = []
        custom_names = options.get('names', {})

        methods = self._get_resource_methods(options)

        for method in methods:
            route_name = custom_names.get(method, f"{name}.{method}")
            action = f"{controller}@{method}"

            if method == 'create':
                # GET /profile/create
                route = self.router.get(f"{name}/create", action).name(route_name)

            elif method == 'store':
                # POST /profile
                route = self.router.post(name, action).name(route_name)

            elif method == 'show':
                # GET /profile
                route = self.router.get(name, action).name(route_name)

            elif method == 'edit':
                # GET /profile/edit
                route = self.router.get(f"{name}/edit", action).name(route_name)

            elif method == 'update':
                # PUT /profile
                route = self.router.match(['PUT', 'PATCH'], name, action).name(route_name)

            elif method == 'destroy':
                # DELETE /profile
                route = self.router.delete(name, action).name(route_name)

            else:
                continue

            # Apply middleware if specified
            if 'middleware' in options:
                middleware = options['middleware']
                if isinstance(middleware, str):
                    middleware = [middleware]
                route.middleware(middleware)

            routes.append(route)

        return routes

    def nested_register(
        self,
        parent: str,
        name: str,
        controller: str,
        **options
    ) -> List[Route]:
        """
        Register nested resource routes

        Args:
            parent: Parent resource name
            name: Child resource name
            controller: Controller class name
            **options: Same as register()

        Returns:
            List of created routes

        Usage:
            # Creates routes like: /posts/{post}/comments
            registrar.nested_register('posts', 'comments', 'CommentController')
        """
        # Nested resources are prefixed with parent
        nested_name = f"{parent}/{{{parent}}}/{name}"

        return self.register(nested_name, controller, **options)

    def shallow_nested_register(
        self,
        parent: str,
        name: str,
        controller: str,
        **options
    ) -> List[Route]:
        """
        Register shallow nested resource routes

        Shallow nesting only nests index, create, and store routes

        Args:
            parent: Parent resource name
            name: Child resource name
            controller: Controller class name
            **options: Same as register()

        Returns:
            List of created routes

        Usage:
            # Nested: /posts/{post}/comments (index, create, store)
            # Shallow: /comments/{comment} (show, edit, update, destroy)
            registrar.shallow_nested_register('posts', 'comments', 'CommentController')
        """
        routes = []

        # Nested routes (index, create, store)
        nested_methods = ['index', 'create', 'store']
        nested_options = options.copy()
        nested_options['only'] = nested_methods

        routes.extend(self.nested_register(parent, name, controller, **nested_options))

        # Shallow routes (show, edit, update, destroy)
        shallow_methods = ['show', 'edit', 'update', 'destroy']
        shallow_options = options.copy()
        shallow_options['only'] = shallow_methods

        routes.extend(self.register(name, controller, **shallow_options))

        return routes

    def get_resource_uri(self, name: str, method: str, parameter: str = None) -> str:
        """
        Get the URI for a resource method

        Args:
            name: Resource name
            method: Method name
            parameter: Parameter name (optional)

        Returns:
            URI string
        """
        if parameter is None:
            parameter = name.split('/')[-1]

        uri_map = {
            'index': name,
            'create': f"{name}/create",
            'store': name,
            'show': f"{name}/{{{parameter}}}",
            'edit': f"{name}/{{{parameter}}}/edit",
            'update': f"{name}/{{{parameter}}}",
            'destroy': f"{name}/{{{parameter}}}",
        }

        return uri_map.get(method, '')

    def get_resource_action(self, controller: str, method: str) -> str:
        """
        Get the action string for a resource method

        Args:
            controller: Controller class name
            method: Method name

        Returns:
            Action string
        """
        return f"{controller}@{method}"

    def get_resource_name(self, base: str, method: str) -> str:
        """
        Get the route name for a resource method

        Args:
            base: Base resource name
            method: Method name

        Returns:
            Route name
        """
        return f"{base}.{method}"
