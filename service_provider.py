"""
Service Provider Base Class
Laravel-style service providers for registering services and bootstrapping packages
"""
from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from larasanic.application import Application


class ServiceProvider(ABC):
    """
    Base Service Provider class

    Service providers are the central place for application and package bootstrapping.
    They handle:
    - Registering services in the container
    - Registering routes
    - Publishing configuration
    - Registering views
    - Running migrations
    """

    def __init__(self, app: 'Application'):
        self.app = app

    def register(self):
        """
        Register services in the container
        Called when the provider is registered (before booting)

        Example:
            self.app.singleton('auth', AuthService)
            self.app.bind('mailer', lambda app: MailService(app.config))
        """
        pass

    def boot(self):
        """
        Bootstrap services (after all providers are registered)
        This is where you should:
        - Register routes
        - Publish configuration
        - Set up event listeners
        - Register views

        Example:
            self.register_routes()
            self.register_config()
            self.register_views()
        """
        pass

    def register_routes(self):
        """Register package routes with Sanic"""
        pass

    def register_views(self):
        """Register package view namespaces"""
        pass

    def register_migrations(self):
        """Register package migrations"""
        pass

    def register_config(self, config_name: str, config_dict: dict):
        """
        Merge package configuration with app config

        Args:
            config_name: The config key (e.g., 'auth', 'database')
            config_dict: The configuration dictionary
        """
        if not hasattr(self.app, 'config'):
            self.app.config = {}

        if config_name not in self.app.config:
            self.app.config[config_name] = {}

        self.app.config[config_name].update(config_dict)

    def publishes(self, source: str, destination: str):
        """
        Register files to be published (config, views, migrations, etc.)

        Args:
            source: Source file path in package
            destination: Destination in app
        """
        if not hasattr(self.app, 'publishable'):
            self.app.publishable = []

        self.app.publishable.append({
            'source': source,
            'destination': destination,
            'provider': self.__class__.__name__
        })
