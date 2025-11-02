"""
Auth Service Provider
Registers authentication services and routes
"""
from larasanic.service_provider import ServiceProvider
from larasanic.auth.auth_service import AuthService
from larasanic.auth.controllers.auth_controller import AuthController
from larasanic.support.facades import Route,App


class AuthServiceProvider(ServiceProvider):
    """Auth layer service provider"""

    def register(self):
        # Register services in container
        App.singleton('auth_service', AuthService())
        App.singleton('auth_controller', AuthController())

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