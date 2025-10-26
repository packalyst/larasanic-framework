"""
Framework Application Class
"""
from sanic import Sanic
from typing import Dict, List, Any, Optional
import importlib
import inspect
import sys


class Application:
    """Main application class - manages the entire framework lifecycle"""

    def __init__(self, base_path: str):
        self.base_path = base_path
        # Create Sanic app
        from larasanic.support import Config,Str

        self.sanic_app = Sanic(Str.snake(Config.get('app.app_name')))
        # Disable sanic-ext auto-loading since we have our own middleware system
        self.sanic_app.config.AUTO_EXTEND = False
        self.sanic_app.config.HEALTH = False
        self.sanic_app.config.HEALTH_ENDPOINT = False
        
        self.providers: List[Any] = []
        self.packages: Dict[str, Any] = {}
        self.booted = False
        self.bindings: Dict[str, Any] = {}
        self.middleware_manager = None  # Will be set by HttpServiceProvider

        # Add base path to Python path
        if self.base_path not in sys.path:
            sys.path.insert(0, self.base_path)

    def singleton(self, key: str, factory_or_instance):
        """
        Register a singleton binding (Laravel-style container)
        If factory: Will be called once and cached
        If instance: Will be stored directly
        """
        # Check if it's a factory function (lambda or regular function)
        if inspect.isfunction(factory_or_instance) or inspect.ismethod(factory_or_instance):
            # It's a factory function - will be called lazily
            self.bindings[key] = {'type': 'singleton', 'factory': factory_or_instance, 'instance': None}
        else:
            # It's a direct instance - store it immediately
            self.bindings[key] = {'type': 'singleton', 'factory': None, 'instance': factory_or_instance}

    def bind(self, key: str, factory: callable):
        """Register a factory binding (called every time)"""
        self.bindings[key] = {'type': 'factory', 'factory': factory}

    def make(self, key: str) -> Any:
        """Resolve a binding from the container"""
        if key not in self.bindings:
            raise KeyError(f"Binding '{key}' not found in container")

        binding = self.bindings[key]

        # Handle new dict format
        if isinstance(binding, dict):
            if binding['type'] == 'singleton':
                # Check if already instantiated
                if binding['instance'] is None:
                    # Create and cache the instance
                    binding['instance'] = binding['factory'](self)
                return binding['instance']
            elif binding['type'] == 'factory':
                # Call factory every time
                return binding['factory'](self)

        # Handle old format (direct binding)
        # If it's a callable (factory), call it
        if callable(binding) and not isinstance(binding, type):
            return binding(self)

        return binding

    def has(self, key: str) -> bool:
        """
        Check if a binding exists in the container
        """
        return key in self.bindings

    def get_bindings(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all container bindings
        """
        result = {}
        for key, binding in self.bindings.items():
            if isinstance(binding, dict):
                result[key] = {
                    'type': binding['type'],
                    'instantiated': binding.get('instance') is not None if binding['type'] == 'singleton' else None
                }
            else:
                result[key] = {'type': 'legacy','instantiated': None}
        return result

    def list_bindings(self) -> str:
        """
        Get a formatted list of all container bindings
        """
        bindings = self.get_bindings()

        if not bindings:
            return "No bindings registered in container."

        singletons = []
        factories = []
        legacy = []

        for key, info in bindings.items():
            if info['type'] == 'singleton':
                status = '✓ instantiated' if info['instantiated'] else '○ lazy'
                singletons.append(f"  {key:<30} [{status}]")
            elif info['type'] == 'factory':
                factories.append(f"  {key:<30} [new instance each call]")
            else:
                legacy.append(f"  {key:<30} [legacy format]")

        output = []

        if singletons:
            output.append("Singletons:")
            output.extend(sorted(singletons))

        if factories:
            if output:
                output.append("")
            output.append("Factories (bind):")
            output.extend(sorted(factories))

        if legacy:
            if output:
                output.append("")
            output.append("Legacy:")
            output.extend(sorted(legacy))

        return "\n".join(output)

    def register_provider(self, provider_class):
        """Register a service provider"""
        provider = provider_class(self)
        register = provider.register()
        if register != False:
            self.providers.append(provider)
        return provider

    def boot(self):
        """Boot all service providers"""
        if self.booted:
            return

        # Boot all providers
        for provider in self.providers:
            provider.boot()

        self.booted = True

    def run(self, host=None, port=None, **kwargs):
        """Run the Sanic server"""
        from larasanic.defaults import DEFAULT_HOST, DEFAULT_PORT
        host = host or DEFAULT_HOST
        port = port or DEFAULT_PORT
        self.sanic_app.run(host=host, port=port, **kwargs)