"""
Auth Service Provider
Registers authentication services and routes
"""
from larasanic.service_provider import ServiceProvider
from larasanic.auth.auth_service import AuthService
from larasanic.auth.controllers.auth_controller import AuthController
from larasanic.auth.models.user import User
from larasanic.support import Storage, Config
from larasanic.support.facades import Route,App


class AuthServiceProvider(ServiceProvider):
    """Auth layer service provider"""

    def register(self):
        """Register auth services"""
        # Load JWT keys
        private_key, public_key = self._load_jwt_keys()
        # Create auth service (now includes crypto operations)
        from larasanic.defaults import DEFAULT_JWT_ALGORITHM, DEFAULT_ACCESS_TOKEN_TTL, DEFAULT_REFRESH_TOKEN_TTL
        auth_service = AuthService(
            private_key=private_key,
            public_key=public_key,
            algorithm=Config.get('security.JWT_ALGORITHM', DEFAULT_JWT_ALGORITHM),
            access_ttl=Config.get('security.ACCESS_TOKEN_TTL_SECONDS', DEFAULT_ACCESS_TOKEN_TTL),
            refresh_ttl=Config.get('security.REFRESH_TOKEN_TTL_SECONDS', DEFAULT_REFRESH_TOKEN_TTL),
            cookie_secure=Config.get('session.COOKIE_SECURE', False),
            user_model=User
        )

        # Create auth controller
        auth_controller = AuthController(auth_service=auth_service)

        # Register services in container
        App.singleton('auth_service', auth_service)
        App.singleton('auth_controller', auth_controller)

    def boot(self):
        """Bootstrap auth services"""
        self.register_routes()

    def register_routes(self):
        """Register authentication routes using new routing system"""
        auth_controller = App.make('auth_controller')

        # Guest routes (only for unauthenticated users)
        # Register guest routes with middleware
        Route.prefix('/api/auth').middleware('guest').group(lambda: [
            Route.post('/register', auth_controller.register).name('register'),
            Route.post('/login', auth_controller.login).name('login'),
        ])
        # Protected routes (only for authenticated users)
        # Register protected routes with middleware
        Route.prefix('/api/auth').middleware('auth').name('api.auth.').group(lambda: [
            Route.post('/logout', auth_controller.logout).name('logout'),
            Route.get('/me', auth_controller.me).name('me'),
        ])
        # Public route (no authentication required - uses refresh token)
        Route.post('/api/auth/refresh', auth_controller.refresh).name('api.auth.refresh')


    def _load_jwt_keys(self):
        """
        Load JWT public and private keys
        """
        public_key_path,private_key_path = Storage.get_jwt_paths()

        # Read keys
        try:
            with open(private_key_path, 'r') as f:
                private_key = f.read()
            with open(public_key_path, 'r') as f:
                public_key = f.read()

            return private_key, public_key
        except FileNotFoundError as e:
            raise ValueError(
                f"JWT key files not found: {e}\n"
                f"Please generate JWT keys first."
            )