"""
Blueprint Loader
Automatically scans and loads routes from web.py, api.py, ws.py files
"""
import os
import importlib.util
from typing import Dict, List, Optional
from larasanic.support.facades import App,Route
from larasanic.support import Storage

class BlueprintLoader:
    """
    Loads route files and creates Sanic blueprints
    """
    def __init__(self,routes_dir = None):
        """
        Initialize blueprint loader
        """
        self.routes_dir: Dict[str, Blueprint] = routes_dir if routes_dir else Storage.routes()

    def load_route_file(self, file_path: str, blueprint_name: str) -> Optional[Dict]:
        """
        Load a route file and prepare routes for registration
        """
        if not os.path.exists(file_path):
            return None

        # Store current route count
        routes_before = len(Route.get_routes())

        # Load the route file (this will register routes with Router singleton)
        spec = importlib.util.spec_from_file_location(f"routes.{blueprint_name}", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get newly registered routes
        all_routes = Route.get_routes()
        new_routes = all_routes[routes_before:]


        if not new_routes:
            return None

        # Get blueprint prefix
        blueprint_prefix = self._get_blueprint_prefix(blueprint_name)

        # Apply blueprint name prefix to all routes
        for route in new_routes:
            # Set blueprint name
            route.set_blueprint(blueprint_name)

            # Apply route name prefix (e.g., "web.login", "api.users")
            if route.get_name() and not route.get_name().startswith(f"{blueprint_name}."):
                route._name = f"{blueprint_name}.{route.get_name()}"

            # DON'T apply URL prefix here via route.prefix() - it will be prepended
            # during Sanic registration to ensure correct prefix ordering

        # Store blueprint info
        return {
            'name': blueprint_name,
            'routes': new_routes,
            'prefix': blueprint_prefix,
        }

    def _get_blueprint_prefix(self, blueprint_name: str) -> Optional[str]:
        """
        Get URL prefix for blueprint
        """
        prefixes = {
            'api': '/api',
            'ws': '/ws',
            # 'web' has no prefix (root level)
        }
        return prefixes.get(blueprint_name)

    def _organize_provider_routes(self, provider_routes: List) -> Dict[str, List]:
        """
        Organize provider routes by blueprint based on their group name or URI prefix
        """
        organized = {}

        for route in provider_routes:
            blueprint_name = 'web'  # default

            # First, check if route has a group name prefix (from .name('api.auth.'))
            group_name = route.get_group_name_prefix()
            if group_name:
                # Extract blueprint from group name (e.g., 'api.auth.' -> 'api')
                blueprint_name = group_name.split('.')[0]
            else:
                # Fall back to URI prefix detection
                uri = route.get_compiled_uri()
                if uri.startswith('api/'):
                    blueprint_name = 'api'
                elif uri.startswith('ws/'):
                    blueprint_name = 'ws'

            # Add route to appropriate blueprint
            if blueprint_name not in organized:
                organized[blueprint_name] = []
            organized[blueprint_name].append(route)

        return organized

    def prepare_blueprints(self) -> Dict[str, Dict]:
        """
        Prepare all blueprints by loading route files and organizing provider routes
        """
        # Step 1: Track routes registered by providers (before loading files)
        routes_before_files = len(Route.get_routes())

        # Step 2: Load route files
        # Order matters! API routes must be registered before web catch-all
        blueprint_files = {
            'api': os.path.join(self.routes_dir, 'api.py'),
            'ws': os.path.join(self.routes_dir, 'ws.py'),
            'web': os.path.join(self.routes_dir, 'web.py'),
        }

        blueprints_info = {}

        for blueprint_name, file_path in blueprint_files.items():
            if os.path.exists(file_path):
                blueprint_info = self.load_route_file(file_path, blueprint_name)
                if blueprint_info:
                    blueprints_info[blueprint_name] = blueprint_info

        # Step 3: Organize provider routes by blueprint
        all_routes = Route.get_routes()
        if routes_before_files > 0:
            provider_routes = all_routes[:routes_before_files]
            organized_provider_routes = self._organize_provider_routes(provider_routes)

            # Step 4: Merge provider routes into blueprints
            for blueprint_name, routes in organized_provider_routes.items():
                # Set blueprint name on provider routes
                for route in routes:
                    route.set_blueprint(blueprint_name)

                # Ensure blueprint exists
                if blueprint_name not in blueprints_info:
                    blueprints_info[blueprint_name] = {
                        'name': blueprint_name,
                        'routes': [],
                        'prefix': self._get_blueprint_prefix(blueprint_name)
                    }

                # Prepend provider routes (so they're registered before file routes)
                blueprints_info[blueprint_name]['routes'] = routes + blueprints_info[blueprint_name]['routes']

        return blueprints_info

    def register_sanic_routes(self):
        """
        Register blueprint routes directly with Sanic app
        """
        from larasanic.routing.route_middleware_registry import RouteMiddlewareRegistry
        from larasanic.support import Config, ClassLoader

        # Create middleware registry once
        registry = RouteMiddlewareRegistry()

        # Load route middleware from config
        route_middleware_config = Config.get('middleware.ROUTE_MIDDLEWARE', {})
        for name, class_path in route_middleware_config.items():
            try:
                middleware_cls = ClassLoader.load(class_path)
                instance = middleware_cls._register_middleware()
                if instance:
                    registry.register(name, instance)
            except Exception as e:
                print(f"⚠️  Failed to load middleware '{name}': {e}")

        # Register routes from each blueprint
        route_count = 0
        sanic_app = App.get_sanic()
        registered_route_names = set()  # Track which routes we register

        for blueprint_name, info in self.prepare_blueprints().items():
            prefix = info['prefix'] or ''

            for route in info['routes']:
                handler = route.get_action()
                route_uri = route.get_compiled_uri()

                # Build final URI with proper prefix handling
                if prefix and route_uri.startswith(blueprint_name + '/'):
                    # Route already has prefix (e.g., provider routes)
                    uri = '/' + route_uri
                elif prefix:
                    # Add prefix to route
                    # Handle edge case: if route_uri is empty (root route '/'), just use prefix
                    if route_uri:
                        uri = f"{prefix}/{route_uri}"
                    else:
                        uri = prefix
                else:
                    # No prefix - use route_uri as-is or root '/'
                    uri = '/' + route_uri if route_uri else '/'

                methods = route.get_methods()

                # Build unique route name with blueprint prefix
                route_name = route.get_name()
                if route_name:
                    # Only add blueprint prefix if route name doesn't already start with it
                    # (provider routes may already have full names like 'api.auth.login')
                    if not route_name.startswith(f"{blueprint_name}."):
                        route_name = f"{blueprint_name}.{route_name}"

                # Get route-specific middleware from .middleware() calls
                route_middleware = route.get_middleware()

                if route_middleware:
                    # Wrap handler with route middleware
                    handler = registry.wrap_handler(handler, route_middleware)

                # Wrap handler to replace Sanic request with HttpRequest facade
                # Use closure factory to avoid capturing loop variable
                def make_wrapper(original_handler):
                    async def request_wrapper(sanic_request, *args, **kwargs):
                        """Replace first parameter (request) with HttpRequest facade"""
                        from larasanic.support.facades import HttpRequest
                        return await original_handler(HttpRequest, *args, **kwargs)
                    return request_wrapper

                handler = make_wrapper(handler)

                # Register handler with Sanic
                sanic_app.add_route(
                    handler,
                    uri,
                    methods=methods,
                    name=route_name
                )
                if route_name:
                    registered_route_names.add(route_name)
                route_count += 1

        # Import Sanic-only routes (like static files) into our Route collection
        # This ensures all routes are centralized in one place
        # Only routes NOT already in our collection will be added
        self._import_sanic_routes(registered_route_names)
        # Refresh route collection indexes after all routes are loaded
        Route.routes.refresh_name_lookups()

    def _import_sanic_routes(self, registered_route_names: set):
        """
        Import Sanic's registered routes into our Route collection
        (only routes NOT registered by us, like static files)
        """
        from larasanic.routing.route import Route as RouteClass
        from larasanic.support import Config,Str
        sanic_routes = App.get_sanic().router.routes

        for sanic_route in sanic_routes:
            # Skip if route already exists in our collection
            route_name = sanic_route.name.replace(f"{Str.snake(Config.get('app.app_name'))}.", '') if hasattr(sanic_route, 'name') else None

            # Skip routes that we registered ourselves
            if route_name and route_name in registered_route_names:
                continue

            if route_name and Route.routes.has_named_route(route_name):
                continue

            # Create our Route object from Sanic route
            methods = list(sanic_route.methods) if hasattr(sanic_route, 'methods') else ['GET']
            uri = sanic_route.uri if hasattr(sanic_route, 'uri') else sanic_route.path
            handler = sanic_route.handler if hasattr(sanic_route, 'handler') else None
            handler_name = getattr(handler, '__name__', '') if handler else None
            # Create route object
            route = RouteClass(methods, uri, handler)

            # Set name if exists
            if route_name:
                route._name = route_name

            # Check if handler is a static file handler
            if handler and handler_name and handler_name == '_static_request_handler':
                blueprint_name = 'static'
            else:
                blueprint_name = 'web'  # default
                # Fallback to URI-based detection
                if uri.startswith('/api/'):
                    blueprint_name = 'api'
                elif uri.startswith('/ws/'):
                    blueprint_name = 'ws'
            route.set_blueprint(blueprint_name)

            # Add to our collection
            Route.routes.add(route)