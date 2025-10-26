"""
Package Migration Command
Run migrations from enabled packages
"""
from larasanic.console.command import Command
from larasanic.support import Config, Storage
from tortoise import Tortoise
import importlib.util
import sys


class PackageMigrateCommand(Command):
    """Run package migrations"""

    name = "package:migrate"
    description = "Run migrations from enabled packages"

    async def handle(self, **kwargs):
        """Handle package migrations"""
        try:
            # Get enabled packages
            enabled_packages = Config.get('packages.ENABLED_PACKAGES', [])

            if not enabled_packages:
                self.info("No packages enabled")
                return 0

            connection = Tortoise.get_connection("default")

            # Track applied migrations
            migration_count = 0

            # Process each enabled package
            for package_name in enabled_packages:
                migrations_dir = Storage.packages(package_name, 'migrations')

                if not migrations_dir.exists():
                    continue

                # Get migration files
                migration_files = sorted(
                    [f for f in migrations_dir.glob("*.py") if f.name != "__init__.py"]
                )

                if not migration_files:
                    continue

                self.info(f"\n📦 Package: {package_name}")

                # Run each migration
                for migration_file in migration_files:
                    migration_name = migration_file.stem

                    try:
                        # Import migration module
                        spec = importlib.util.spec_from_file_location(
                            f"migration_{migration_name}",
                            migration_file
                        )
                        migration_module = importlib.util.module_from_spec(spec)
                        sys.modules[f"migration_{migration_name}"] = migration_module
                        spec.loader.exec_module(migration_module)

                        # Check if migration has upgrade function
                        if not hasattr(migration_module, 'upgrade'):
                            self.warning(f"  ⚠️  {migration_name}: No upgrade function found")
                            continue

                        # Execute migration
                        sql = await migration_module.upgrade(connection)

                        if sql and sql.strip():
                            await connection.execute_script(sql)
                            self.success(f"  ✓ {migration_name}")
                            migration_count += 1
                        else:
                            self.info(f"  ○ {migration_name}: Empty migration")

                    except Exception as e:
                        self.error(f"  ✗ {migration_name}: {str(e)}")
                        if self.option('verbose'):
                            import traceback
                            traceback.print_exc()

            if migration_count > 0:
                self.line()
                self.success(f"✓ Applied {migration_count} package migrations")
            else:
                self.line()
                self.info("No package migrations to apply")

            return 0

        except Exception as e:
            self.error(f"Package migration failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
