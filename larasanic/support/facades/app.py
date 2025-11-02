"""
App Facade
Provides static access to the application container
"""
from larasanic.support.facades.facade import Facade


class App(Facade):
    """
    Application Facade

    Provides static access to the application container.

    Example:
        # Get service from container
        router = App.make('router')
        auth = App.make('auth_service')

        # Check if service is bound
        if App.bound('cache'):
            cache = App.make('cache')

        # Register singleton
        App.singleton('my_service', MyService())

        # Get base path
        base_path = App.base_path()
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        """Return 'app' to get the application itself"""
        return 'app'

    @classmethod
    def get_facade_root(cls):
        """Override to return app directly instead of resolving"""
        return cls.get_app()

    @classmethod
    def get_sanic(cls):
        """
        Get the application instance

        Returns:
            Application instance or None
        """
        return cls.get_app().sanic_app