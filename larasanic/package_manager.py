"""
Package Manager
Handles package discovery, loading, and management
"""
import json
from larasanic.support.facades import App
from typing import Dict, Any, TYPE_CHECKING
from larasanic.support.storage import Storage
if TYPE_CHECKING:
    from pathlib import Path

class PackageManager:
    """Manages framework packages"""
    def __init__(self):
        self.packages: Dict[str, 'PackageManifest'] = {}
        self.packages_path = Storage.packages()

    def discover(self) -> Dict[str, 'PackageManifest']:
        """Discover all packages in the packages directory"""
        if not self.packages_path.exists():
            return {}

        for package_dir in self.packages_path.iterdir():
            if package_dir.is_dir() and not package_dir.name.startswith('_'):
                manifest_path = package_dir / 'package.json'

                if manifest_path.exists():
                    manifest = PackageManifest.load(manifest_path, package_dir)
                    self.packages[manifest.name] = manifest

        return self.packages

    def get_packages(self):
        return self.packages
     
    def load_package(self, package_name: str):
        """Load a specific package"""
        if package_name not in self.packages:
            raise ValueError(f"Package '{package_name}' not found")

        manifest = self.packages[package_name]
        return self._register_package(manifest)

    def load_all(self):
        """Load all discovered packages"""
        for package_name, manifest in self.packages.items():
            try:
                self._register_package(manifest)
            except Exception as e:
                print(f"Error loading package '{package_name}': {e}")

    def _register_package(self, manifest: 'PackageManifest'):
        """Register a package with the application"""
        from larasanic.support import ClassLoader

        # Import and register the service provider
        if manifest.provider:
            provider_class = ClassLoader.load(manifest.provider)
            App.register_provider(provider_class)

        return manifest


class PackageManifest:
    """Represents a package manifest (package.json)"""

    def __init__(self, data: Dict[str, Any], package_path: 'Path'):
        self.data = data
        self.package_path = package_path
        self.name = data.get('name', '')
        self.version = data.get('version', '1.0.0')
        self.description = data.get('description', '')
        self.provider = data.get('provider')
        self.dependencies = data.get('dependencies', {})
        self.routes = data.get('routes', {})
        self.migrations = data.get('migrations', 'migrations/')
        self.views = data.get('views', 'views/')
        self.config = data.get('config')
        self.autoload = data.get('autoload', {})

    @classmethod
    def load(cls, manifest_path: 'Path', package_path: 'Path') -> 'PackageManifest':
        """Load a package manifest from file"""
        with open(manifest_path, 'r') as f:
            data = json.load(f)

        return cls(data, package_path)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary"""
        return self.data
