"""
Model Auto-Discovery
Automatically discovers Tortoise ORM models from framework and application (Laravel-style)
"""
import importlib
import pkgutil
import os
from pathlib import Path
from typing import List, Set


class ModelDiscovery:
    """
    Auto-discovers Tortoise ORM models similar to Laravel

    Flow:
    1. Scan larasanic/ directory for all 'models' packages
    2. Scan app/models/ for user models
    3. Scan packages/ using PackageManager.get_packages()
    4. Apply user config includes/excludes from Config.get('database.MODELS')
    """

    @classmethod
    def discover_all(cls) -> List[str]:
        """
        Auto-discover all models from framework, app, and packages

        Returns:
            List of auto-discovered model module paths

        Example:
            # Auto-discovers:
            # - larasanic.auth.models.user
            # - larasanic.auth.models.access_token
            # - app.models.setting
            # - app.models.files
            # - packages.blog.models.post
        """
        models = set()

        # 1. Discover framework models from larasanic/
        framework_models = cls.discover_framework_models()
        models.update(framework_models)

        # 2. Discover app models from app/models/
        app_models = cls.discover_app_models()
        models.update(app_models)

        # 3. Discover package models from packages/
        package_models = cls.discover_package_models()
        models.update(package_models)

        return sorted(list(models))

    @classmethod
    def discover_framework_models(cls) -> List[str]:
        """
        Auto-discover models from larasanic/ directory
        Scans for any 'models' directories within larasanic package

        Returns:
            List of discovered framework model paths
        """
        discovered = []

        try:
            # Import larasanic package
            import larasanic

            if not hasattr(larasanic, '__path__'):
                return []

            larasanic_path = Path(larasanic.__path__[0])

            # Find all 'models' directories in larasanic/
            for models_dir in larasanic_path.rglob('models'):
                if models_dir.is_dir() and not models_dir.name.startswith('_'):
                    # Get relative path from larasanic root
                    rel_path = models_dir.relative_to(larasanic_path.parent)

                    # Convert path to module name: larasanic/auth/models -> larasanic.auth.models
                    package_name = str(rel_path).replace(os.sep, '.')

                    # Discover models in this package
                    package_models = cls._discover_models_in_package(package_name)
                    discovered.extend(package_models)

        except Exception as e:
            # Log but don't fail
            pass

        return discovered

    @classmethod
    def discover_app_models(cls) -> List[str]:
        """
        Auto-discover models from app/models/ directory

        Returns:
            List of discovered app model paths

        Example:
            # Discovers from app/models/
            app/
            ├── models/
            │   ├── __init__.py
            │   ├── setting.py     → app.models.setting
            │   └── files.py       → app.models.files
        """
        return cls._discover_models_in_package('app.models')

    @classmethod
    def discover_package_models(cls) -> List[str]:
        """
        Auto-discover models from packages/ using PackageManager

        Returns:
            List of discovered package model paths
        """
        discovered = []

        try:
            from larasanic.support.facades import PackageManager

            # Get registered packages
            packages = PackageManager.get_packages()

            # Scan each package for models
            for package_name, manifest in packages.items():
                # Construct package models path: packages.{package_name}.models
                package_models_path = f"packages.{package_name}.models"

                # Discover models in this package
                package_models = cls._discover_models_in_package(package_models_path)
                discovered.extend(package_models)

        except Exception as e:
            # PackageManager not available or no packages
            pass

        return discovered

    @classmethod
    def _discover_models_in_package(cls, package_name: str) -> List[str]:
        """
        Discover models from a specific package

        Args:
            package_name: Package path (e.g., "larasanic.auth.models", "app.models")

        Returns:
            List of discovered model module paths
        """
        discovered = []

        try:
            # Import the package
            package = importlib.import_module(package_name)

            # Check if it has a path (is a package, not just a module)
            if not hasattr(package, '__path__'):
                return []

            package_path = package.__path__[0]

            # Iterate through all modules in the package
            for finder, name, ispkg in pkgutil.iter_modules([package_path]):
                # Skip packages (directories) and private modules
                if not ispkg and not name.startswith('_'):
                    model_path = f"{package_name}.{name}"

                    # Verify it contains Tortoise models
                    if cls._is_tortoise_model_module(model_path):
                        discovered.append(model_path)

        except ImportError:
            # Package doesn't exist (e.g., app.models not created yet)
            pass
        except Exception as e:
            # Log error but don't fail
            pass

        return discovered

    @classmethod
    def _is_tortoise_model_module(cls, module_path: str) -> bool:
        """
        Check if a module contains Tortoise ORM models DEFINED in it
        (not just imported)

        Args:
            module_path: Module path to check

        Returns:
            True if module contains at least one Tortoise Model class
        """
        try:
            module = importlib.import_module(module_path)

            # Look for Tortoise Model classes defined in this module
            for attr_name in dir(module):
                if not attr_name.startswith('_'):
                    attr = getattr(module, attr_name, None)

                    # Check if it's a Tortoise Model class defined in THIS module
                    if cls._is_tortoise_model_class(attr) and cls._is_defined_in_module(attr, module):
                        return True

            return False

        except Exception:
            return False

    @classmethod
    def build_final_list(cls, auto_discovered: List[str], user_config: List[str]) -> List[str]:
        """
        Build final model list from auto-discovered models and user config

        User config can:
        - Add models: "packages.blog.models.post"
        - Exclude models: "-app.models.old_legacy"

        Args:
            auto_discovered: Auto-discovered model paths
            user_config: User-defined includes/excludes from Config.get('database.MODELS')

        Returns:
            Final unique list of model paths

        Example:
            # Auto-discovered: ['larasanic.auth.models.user', 'app.models.files']
            # User config: ['packages.blog.models.post', '-app.models.files']
            # Result: ['larasanic.auth.models.user', 'packages.blog.models.post']
        """
        # Start with auto-discovered models
        models = set(auto_discovered)

        # Process user config
        for item in user_config:
            if item.startswith('-'):
                # Exclusion: remove from auto-discovered
                model_to_remove = item[1:]  # Strip the '-' prefix
                models.discard(model_to_remove)
            else:
                # Inclusion: add to the list
                models.add(item)

        # Return sorted unique list
        return sorted(list(models))

    @classmethod
    def discover_and_build(cls, user_config: List[str] = None) -> List[str]:
        """
        Convenience method: auto-discover and apply user config in one call

        Args:
            user_config: User-defined includes/excludes (optional)

        Returns:
            Final model list ready for Tortoise ORM

        Raises:
            ValueError: If duplicate table names are detected

        Example:
            # In DatabaseManager:
            models = ModelDiscovery.discover_and_build(
                user_config=Config.get('database.MODELS', [])
            )
        """
        auto_discovered = cls.discover_all()
        user_config = user_config or []

        final_models = cls.build_final_list(auto_discovered, user_config)

        # Validate no duplicate table names
        cls.validate_no_duplicate_tables(final_models)

        return final_models

    @classmethod
    def validate_no_duplicate_tables(cls, model_paths: List[str]) -> None:
        """
        Validate that no two models use the same database table name

        Args:
            model_paths: List of model module paths to validate

        Raises:
            ValueError: If duplicate table names are detected

        Example:
            # Will raise error if both exist:
            # - app.models.access_token (table: access_tokens)
            # - larasanic.auth.models.access_token (table: access_tokens)
        """
        table_to_models = {}  # {table_name: [model_path1, model_path2, ...]}

        for model_path in model_paths:
            try:
                # Import the model module
                module = importlib.import_module(model_path)

                # Find all Tortoise Model classes DEFINED in this module
                for attr_name in dir(module):
                    if not attr_name.startswith('_'):
                        attr = getattr(module, attr_name, None)

                        # Check if it's a Tortoise Model class defined in THIS module
                        if cls._is_tortoise_model_class(attr) and cls._is_defined_in_module(attr, module):
                            # Get the table name
                            table_name = cls._get_model_table_name(attr)

                            # Skip if no table name (shouldn't happen but be safe)
                            if not table_name:
                                continue

                            # Track which models use this table
                            if table_name not in table_to_models:
                                table_to_models[table_name] = []

                            table_to_models[table_name].append({
                                'model_path': model_path,
                                'model_class': attr_name,
                                'table': table_name
                            })

            except Exception as e:
                # If we can't import/check a model, skip it
                # The error will surface when Tortoise tries to init
                continue

        # Check for duplicates
        duplicates = {
            table: models
            for table, models in table_to_models.items()
            if len(models) > 1
        }

        if duplicates:
            error_message = cls._format_duplicate_table_error(duplicates)
            raise ValueError(error_message)

    @classmethod
    def _is_tortoise_model_class(cls, obj) -> bool:
        """
        Check if an object is a Tortoise Model class

        Args:
            obj: Object to check

        Returns:
            True if it's a Tortoise Model class
        """
        if not isinstance(obj, type):
            return False

        # Check for Tortoise Model characteristics
        # Models have _meta but it's a descriptor, so check for the class itself
        try:
            from tortoise.models import Model
            return issubclass(obj, Model) and obj is not Model
        except (ImportError, TypeError):
            return False

    @classmethod
    def _is_defined_in_module(cls, obj, module) -> bool:
        """
        Check if a class is actually defined in the given module
        (not just imported into it)

        Args:
            obj: Class object to check
            module: Module to check against

        Returns:
            True if the class is defined in this module
        """
        if not hasattr(obj, '__module__'):
            return False

        # Check if the class's __module__ matches the module's __name__
        return obj.__module__ == module.__name__

    @classmethod
    def _get_model_table_name(cls, model_class) -> str:
        """
        Get the table name for a Tortoise Model class

        Handles both explicit Meta.table and auto-generated names

        Args:
            model_class: Tortoise Model class

        Returns:
            Table name
        """
        # Check if model has explicit table name in Meta
        if hasattr(model_class, 'Meta') and hasattr(model_class.Meta, 'table'):
            return model_class.Meta.table

        # Otherwise, use Tortoise's default naming convention
        # Tortoise converts ClassName to class_name (snake_case) + 's' (plural)
        # e.g., AccessToken -> access_tokens, User -> users
        class_name = model_class.__name__

        # Convert CamelCase to snake_case
        import re
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()

        # Tortoise doesn't auto-pluralize, it just uses the snake_case name
        # Unless explicitly set in Meta.table
        return snake_case

    @classmethod
    def _format_duplicate_table_error(cls, duplicates: dict) -> str:
        """
        Format a clear error message for duplicate table names

        Args:
            duplicates: Dict of {table_name: [model_info1, model_info2, ...]}

        Returns:
            Formatted error message
        """
        lines = [
            "",
            "=" * 70,
            "❌ DUPLICATE TABLE NAMES DETECTED",
            "=" * 70,
            "",
            "Multiple models are trying to use the same database table.",
            "Each table can only be used by ONE model.",
            "",
        ]

        for table_name, models in duplicates.items():
            lines.append(f"Table: '{table_name}'")
            lines.append("-" * 70)

            for model_info in models:
                lines.append(f"  • {model_info['model_class']} in {model_info['model_path']}")

            lines.append("")

        lines.extend([
            "SOLUTION:",
            "-" * 70,
            "Choose ONE model to keep for each table and exclude the others.",
            "",
            "Add exclusions to config/database.py:",
            "",
            "MODELS = [",
        ])

        # Suggest exclusions (exclude all but the first one for each table)
        for table_name, models in duplicates.items():
            for model_info in models[1:]:  # Skip first, suggest excluding the rest
                lines.append(f"    '-{model_info['model_path']}',  # Exclude duplicate for table '{table_name}'")

        lines.extend([
            "]",
            "",
            "=" * 70,
            ""
        ])

        return "\n".join(lines)
