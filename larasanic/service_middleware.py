from sanic import Request, response
from larasanic.middleware import Middleware
from larasanic.support.facades import Route
from typing import Optional

class ServiceMiddleware:
    """Manages middleware registration and execution"""

    def __init__(self, app):
        self.app = app
        self.middlewares = []  # List of (middleware_instance, name) tuples
        self._middleware_groups = None

    def add(self, middleware_instance: Middleware, name: str = None):
        """
        Add a middleware to the stack
        """
        self.middlewares.append((middleware_instance, name))

    def _load_middleware_config(self):
        """Load middleware configuration from config"""
        if self._middleware_groups is None:
            from larasanic.support import Config
            self._middleware_groups = Config.get('middleware.MIDDLEWARE_GROUPS', {})

    def _should_skip_middleware(self, blueprint_route_name, middleware: Middleware, middleware_name: str) -> bool:
        """
        Check if middleware should be skipped for this request
        Returns:
            True if middleware should be skipped, False otherwise
        """
        self._load_middleware_config()
      
        # If no middleware name, don't skip (legacy middleware without name)
        if not middleware_name:
            return False
        
        if blueprint_route_name:
            # Check if this middleware is in the blueprint's group
            blueprint_middleware = self._middleware_groups.get(blueprint_route_name, [])

            # If middleware is NOT in the blueprint's group, skip it
            if middleware_name not in blueprint_middleware:
                return True
        return False

    def register_with_sanic(self):
        from larasanic.support.facades import Facade,HttpRequest
        from larasanic.support import Config
        from larasanic.exceptions.error_handler import ErrorHandler
        from larasanic.support.facades.http_response import ResponseBuilder

        # Create error handler instance
        error_handler = ErrorHandler(debug=Config.get('app.APP_DEBUG', False))

        # Register with Sanic's exception system
        @self.app.sanic_app.exception(Exception)
        async def handle_exception(request, exception):
            """Handle all exceptions through centralized error handler"""
            resp = await error_handler.handle_error(request, exception)
            if isinstance(resp, ResponseBuilder):
                # __await__() handles both sync and async build()
                resp = await resp
            return resp

        """Register middlewares with Sanic app"""
        # Register request middlewares
        @self.app.sanic_app.middleware('request')
        async def process_request(request):
            # Set current request and analyze it (stores analysis in request.ctx)
            Facade.set_current_request(request)

            # Track which middlewares actually ran for this request
            HttpRequest.set('_executed_middlewares',[])
            
            """
            from larasanic.support.facades import TemplateBlade
            from larasanic.helpers import view
            if TemplateBlade.view_exists('errors.maintenance'):
                return view('errors.maintenance', {'message': 'Not found'})
            """

            # Get blueprint name (None for 404 errors or routes without blueprints)
            current_route = Route.current()
            blueprint_route_name = current_route.get_blueprint() if current_route else None

            for middleware_instance, middleware_name in self.middlewares:
                # Check if middleware should be skipped
                if self._should_skip_middleware(blueprint_route_name, middleware_instance, middleware_name):
                    continue
                
                # Track that this middleware executed
                HttpRequest.append('_executed_middlewares',middleware_instance)

                result = await middleware_instance.before_request(request)
                if result is not None:
                    return result  # Short-circuit
            return None

        # IMPORTANT: Response middlewares run in REVERSE order of registration!
        # Register process_response FIRST so it runs LAST (adds CORS headers after normalization)
        @self.app.sanic_app.middleware('response')
        async def process_response(request, resp):
            # Only run after_response for middlewares that ran before_request
            executed_middlewares = HttpRequest.get('_executed_middlewares',[])
            
            # PHASE 1: Run middlewares' after_response (they receive ResponseBuilder and can queue headers/cookies)
            for middleware in reversed(executed_middlewares):
                resp = await middleware.after_response(request, resp)

            # PHASE 2: Handle ResponseBuilder instances (after all middlewares queued data)
            # This ensures build() picks up all queued headers/cookies
            if isinstance(resp, ResponseBuilder):
                resp = await resp

            # PHASE 3: Run middlewares again for post-build operations (like compression)
            # These middlewares receive the built HTTPResponse
            for middleware in reversed(executed_middlewares):
                if hasattr(middleware, 'after_build'):
                    resp = await middleware.after_build(request, resp)
        
            Facade.clear_current_request()
            return resp