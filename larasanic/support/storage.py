"""
Storage - Centralized path management (Laravel-style)
Provides consistent path resolution across the application
"""

import os
from pathlib import Path
from typing import Union


class Storage:
    """
    Centralized path management helper (Laravel-style)

    Directory structure:
    /
    ├── app/                # Application code
    ├── bootstrap/          # Bootstrap files
    ├── config/             # Configuration files
    ├── larasanic/          # Framework code
    ├── packages/           # Modular packages
    ├── public/             # Public assets
    ├── resources/          # Resources (views, etc.)
    │   └── views/          # Blade templates
    ├── routes/             # Route definitions
    ├── storage/            # File storage
    │   ├── app/            # Application storage
    │   ├── larasanic/      # Framework storage
    │   │   ├── cache/      # Cache files
    │   │   │   ├── blade/  # Blade template cache
    │   │   │   ├── data/   # Data cache
    │   │   │   └── commands.cache
    │   │   ├── sessions/   # Session storage
    │   ├── logs/           # Log files
    │   └── database/       # Database files
    └── main.py             # Application entry point
    """

    # Base directories
    _base_path: Path = None
    _storage_path: Path = None
    _framework_path: Path = None

    @classmethod
    def initialize(cls, base_path: Union[str, Path] = None):
        """
        Initialize paths (should be called during app startup)

        Args:
            base_path: Application base directory (defaults to current working directory)
        """
        if base_path is None:
            # Use current working directory as base path
            # This allows the framework to work when installed via pip
            base_path = os.getcwd()

        cls._base_path = Path(base_path).resolve()
        cls._storage_path = cls._base_path / 'storage'

        # Locate the installed larasanic framework directory
        # This is needed to access framework resources (stubs, templates, etc.)
        cls._framework_path = Path(__file__).parent.parent.resolve()

    @classmethod
    def framework(cls, *paths: str) -> Path:
        """
        Get framework installation path (where larasanic package is installed)
        Use this for accessing framework resources like stubs, templates, etc.

        Args:
            *paths: Additional path segments

        Returns:
            Path object pointing to framework directory or subdirectory
        """
        if cls._framework_path is None:
            cls.initialize()

        if paths:
            return cls._framework_path.joinpath(*paths)
        return cls._framework_path

    @classmethod
    def base(cls, *paths: str) -> Path:
        """
        Get application base path

        Args:
            *paths: Additional path segments

        Returns:
            Path object

        Example:
            Path.base('app', 'models')  # /project/app/models
        """
        if cls._base_path is None:
            cls.initialize()

        if paths:
            clean_paths = [p.lstrip('/') for p in paths]
            return cls._base_path.joinpath(*clean_paths)
        return cls._base_path

    @classmethod
    def app(cls, *paths: str) -> Path:
        """Get app path (app/)"""
        return cls.base('app', *paths)

    @classmethod
    def bootstrap(cls, *paths: str) -> Path:
        """Get bootstrap path (bootstrap/)"""
        return cls.base('bootstrap', *paths)

    @classmethod
    def config(cls, *paths: str) -> Path:
        """Get config path (config/)"""
        return cls.base('config', *paths)

    @classmethod
    def public(cls, *paths: str) -> Path:
        """Get public path (public/)"""
        return cls.base('public', *paths)

    @classmethod
    def resources(cls, *paths: str) -> Path:
        """Get resources path (resources/)"""
        return cls.base('resources', *paths)

    @classmethod
    def views(cls, *paths: str) -> Path:
        """Get views path (resources/views/)"""
        return cls.resources('views', *paths)

    @classmethod
    def routes(cls, *paths: str) -> Path:
        """Get routes path (routes/)"""
        return cls.base('routes', *paths)

    @classmethod
    def packages(cls, *paths: str) -> Path:
        """Get packages path (packages/)"""
        return cls.base('packages', *paths)

    # === Storage Paths ===

    @classmethod
    def storage(cls, *paths: str) -> Path:
        """
        Get storage path

        Args:
            *paths: Additional path segments

        Returns:
            Path object

        Example:
            Path.storage('app', 'media')  # storage/app/media
        """
        if cls._storage_path is None:
            cls.initialize()

        if paths:
            clean_paths = [p.lstrip('/') for p in paths]
            return cls._storage_path.joinpath(*clean_paths)
        return cls._storage_path

    @classmethod
    def app_storage(cls, *paths: str) -> Path:
        """Get app storage path (storage/app/)"""
        return cls.storage('app', *paths)
    
    @classmethod
    def app_media(cls, *paths: str) -> Path:
        """Get app storage path (storage/app/)"""
        return cls.app_storage('media', *paths)
    
    @classmethod
    def app_backup(cls, *paths: str) -> Path:
        """Get app storage path (storage/app/)"""
        return cls.app_storage('backup', *paths)

    @classmethod
    def framework_storage(cls, *paths: str) -> Path:
        """Get framework storage path (storage/larasanic/)"""
        return cls.storage('framework', *paths)

    @classmethod
    def cache(cls, *paths: str) -> Path:
        return cls.framework_storage('cache', *paths)

    @classmethod
    def cache_blade(cls, *paths: str) -> Path:
        return cls.cache('blade', *paths)
    
    @classmethod
    def cache_thumbnails(cls, *paths: str) -> Path:
        return cls.cache('thumbnails', *paths)

    @classmethod
    def cache_data(cls, *paths: str) -> Path:
        """Get data cache path (storage/larasanic/cache/data/)"""
        return cls.cache('data', *paths)

    @classmethod
    def sessions(cls, *paths: str) -> Path:
        """Get sessions storage path (storage/larasanic/sessions/)"""
        return cls.framework_storage('sessions', *paths)

    @classmethod
    def database(cls, *paths: str) -> Path:
        """Get database storage path (storage/database/)"""
        return cls.storage('database', *paths)

    @classmethod
    def logs(cls, *paths: str) -> Path:
        """Get logs path (storage/logs/)"""
        return cls.storage('logs', *paths)


    # === Helpers ===

    @classmethod
    def ensure_directory(cls, path: Union[str, Path]) -> Path:
        """
        Ensure directory exists, create if it doesn't

        Args:
            path: Directory path

        Returns:
            Path object
        """
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        return path_obj

    @classmethod
    def create_storage_structure(cls):
        """
        Create the complete storage directory structure
        Should be called during application initialization
        """
        directories = [
            cls.app_storage(),
            cls.cache(),
            cls.cache_blade(),
            cls.cache_data(),
            cls.sessions(),
            cls.database(),
            cls.logs(),
            cls.public(),
        ]

        for directory in directories:
            cls.ensure_directory(directory)
        return True

    # Utility methods for path operations
    @classmethod
    def exists(cls, path: Union[str, Path]) -> bool:
        """Check if file or directory exists"""
        return Path(path).exists()

    @classmethod
    def makedirs(cls, path: Union[str, Path], exist_ok: bool = True) -> Path:
        """Create directory with parents"""
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=exist_ok)
        return path_obj

    @classmethod
    def join(cls, *paths: str) -> str:
        """Join path segments"""
        return str(Path(*paths))

    @classmethod
    def unlink(cls, path: Union[str, Path]) -> None:
        """Delete file"""
        Path(path).unlink()

    @classmethod
    def delete_directory(cls, path: Union[str, Path], recursive: bool = True) -> None:
        """
        Delete directory and optionally its contents

        Args:
            path: Directory path to delete
            recursive: If True, delete directory and all contents. If False, only delete if empty.

        Raises:
            OSError: If directory is not empty and recursive=False
        """
        import shutil
        path_obj = Path(path)

        if not path_obj.exists():
            return

        if not path_obj.is_dir():
            raise NotADirectoryError(f"{path} is not a directory")

        if recursive:
            shutil.rmtree(path_obj)
        else:
            path_obj.rmdir()

    @classmethod
    def delete_storage(cls) -> list:
        """List directory contents"""
        return cls.delete_directory(cls.storage())
    
    @classmethod
    def listdir(cls, path: Union[str, Path]) -> list:
        """List directory contents"""
        return list(Path(path).iterdir())

    @classmethod
    def isdir(cls, path: Union[str, Path]) -> bool:
        """Check if path is directory"""
        return Path(path).is_dir()

    @classmethod
    def basename(cls, path: Union[str, Path]) -> str:
        """Get filename from path"""
        return Path(path).name

    @classmethod
    def glob(cls, pattern: str, directory: Union[str, Path] = None) -> list:
        """Find files matching pattern in directory"""
        if directory:
            return list(Path(directory).glob(pattern))
        return []

    @classmethod
    def is_setup_complete(cls) -> bool:
        """
        Check if application setup has been completed

        Returns:
            True if .initialized marker file exists in storage/
        """
        marker_file = cls.storage('.initialized')
        return marker_file.exists()

    @classmethod
    def mark_setup_complete(cls) -> None:
        """
        Mark application setup as complete by creating .initialized marker file
        """
        marker_file = cls.storage('.initialized')
        marker_file.touch()

    @classmethod
    def mark_setup_incomplete(cls) -> None:
        """
        Remove setup completion marker (for reset/cleanup operations)
        """
        marker_file = cls.storage('.initialized')
        if marker_file.exists():
            marker_file.unlink()


# Auto-initialize on import
Storage.initialize()