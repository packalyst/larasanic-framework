"""
Database Migration Manager
Laravel-style migrations for Tortoise ORM using Aerich
"""
import os
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from tortoise import Tortoise
from larasanic.support import Storage
from larasanic.logging import getLogger

logger = getLogger('application')


class MigrationManager:
    """
    Manages database migrations using Aerich

    Provides Laravel-style migration commands:
    - migrate: Run pending migrations
    - migrate:rollback: Rollback last batch
    - migrate:fresh: Drop all tables and re-run migrations
    - migrate:status: Show migration status
    """

    def __init__(self, database_url: str, models: List[str]):
        """
        Initialize migration manager

        Args:
            database_url: Database connection URL
            models: List of model module paths
        """
        self.database_url = database_url
        self.models = models
        self.migrations_path = Storage.database() / 'migrations'
        self.aerich_config_path = Storage.base() / 'aerich.ini'

        # Ensure migrations directory exists
        self.migrations_path.mkdir(parents=True, exist_ok=True)

    def get_aerich_config(self) -> dict:
        """
        Get Aerich configuration

        Returns:
            Aerich configuration dict
        """
        # Only include aerich.models if migrations have been initialized
        models = self.models.copy()

        # Check if aerich has been initialized (pyproject.toml or aerich.ini exists)
        aerich_init_file = self.migrations_path / 'models' / '__init__.py'
        if aerich_init_file.exists():
            models.append("aerich.models")
        from larasanic.support import Config
        return {
            "connections": {"default": self.database_url},
            "apps": {
                "models": {
                    "models": Config.get('database.MODELS', []) + ["aerich.models"],
                    "default_connection": "default",
                }
            },
        }

    async def init_aerich(self):
        """Initialize Aerich migration tracking (creates aerich table in database)"""
        try:
            from aerich import Command

            # Get full config WITH aerich.models
            config = self.get_aerich_config()

            # Initialize Tortoise ORM manually FIRST
            await Tortoise.init(config)

            # Generate schemas (creates tables for our models)
            await Tortoise.generate_schemas()

            # Now create the Command instance (Tortoise is already initialized)
            command = Command(
                tortoise_config=config,
                app='models',
                location=str(self.migrations_path)
            )

            # THIS is where aerich initializes its internal state
            # Tortoise is already initialized, so aerich.models should work
            await command.init_db(safe=True)

            # Close Tortoise connections
            await Tortoise.close_connections()

            logger.info("Aerich initialized successfully")
            return command

        except ImportError:
            logger.error("Aerich not installed. Install with: pip install aerich")
            raise RuntimeError(
                "Aerich is required for migrations.\n"
                "Install with: pip install aerich"
            )

    async def migrate(self):
        """
        Run pending migrations

        Equivalent to: php artisan migrate
        """
        from aerich import Command

        logger.info("Running migrations...")

        config = self.get_aerich_config()
        command = Command(
            tortoise_config=config,
            app='models',
            location=str(self.migrations_path)
        )

        await command.init()

        try:
            # Apply pending migrations (upgrade)
            await command.upgrade(run_in_transaction=True)
            logger.info("✓ Migrations completed successfully")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    async def rollback(self, version: int = -1):
        """
        Rollback last migration batch

        Args:
            version: Number of versions to rollback (-1 for last batch)

        Equivalent to: php artisan migrate:rollback
        """
        from aerich import Command

        logger.info(f"Rolling back migrations (version: {version})...")

        config = self.get_aerich_config()
        command = Command(
            tortoise_config=config,
            app='models',
            location=str(self.migrations_path)
        )

        await command.init()

        try:
            await command.downgrade(version=version, delete=True)
            logger.info("✓ Rollback completed successfully")
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise

    async def status(self):
        """
        Show migration status

        Equivalent to: php artisan migrate:status
        """
        from aerich import Command

        config = self.get_aerich_config()
        command = Command(
            tortoise_config=config,
            app='models',
            location=str(self.migrations_path)
        )

        await command.init()

        try:
            await command.heads()
            logger.info("Migration status displayed")
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            raise

    async def make_migration(self, name: str):
        """
        Create a new migration

        Args:
            name: Migration name

        Equivalent to: php artisan make:migration create_users_table
        """
        from aerich import Command

        logger.info(f"Creating migration: {name}")

        config = self.get_aerich_config()
        command = Command(
            tortoise_config=config,
            app='models',
            location=str(self.migrations_path)
        )

        await command.init()

        try:
            # Generate migration file from model changes
            migration_file = await command.migrate(name=name)

            if migration_file:
                logger.info(f"✓ Migration created: {migration_file}")
            else:
                logger.info("No changes detected - no migration created")
        except Exception as e:
            logger.error(f"Migration creation failed: {e}")
            raise

    async def fresh(self):
        """
        Drop all tables and re-run migrations

        WARNING: This will delete all data!

        Equivalent to: php artisan migrate:fresh
        """
        from aerich import Command

        logger.warning("DROPPING ALL TABLES - All data will be lost!")

        config = self.get_aerich_config()

        # Initialize Tortoise
        await Tortoise.init(config)

        # Drop all tables
        await Tortoise._drop_databases()

        # Close connections
        await Tortoise.close_connections()

        # Reinitialize aerich
        command = Command(
            tortoise_config=config,
            app='models',
            location=str(self.migrations_path)
        )

        await command.init()
        await command.init_db(safe=True)

        # Apply all migrations
        await command.upgrade(run_in_transaction=True)

        logger.info("✓ Fresh migration completed")

    async def reset(self):
        """
        Rollback all migrations

        Equivalent to: php artisan migrate:reset
        """
        from aerich import Command

        logger.info("Resetting all migrations...")

        config = self.get_aerich_config()
        command = Command(
            tortoise_config=config,
            app='models',
            location=str(self.migrations_path)
        )

        await command.init()

        # Rollback all
        try:
            # Keep rolling back until no more migrations
            while True:
                try:
                    await command.downgrade(version=-1, delete=True)
                except:
                    break
            logger.info("✓ Reset completed successfully")
        except Exception as e:
            logger.error(f"Reset failed: {e}")
            raise

    def list_migrations(self) -> List[str]:
        """
        List all migration files

        Returns:
            List of migration file names
        """
        if not self.migrations_path.exists():
            return []

        migration_files = sorted([
            f.name for f in self.migrations_path.glob('*.py')
            if not f.name.startswith('__')
        ])

        return migration_files


# Helper function for use in console commands
async def run_migrations(database_url: str, models: List[str]):
    """
    Quick helper to run migrations

    Args:
        database_url: Database connection URL
        models: List of model module paths

    Example:
        from larasanic.database.migrations import run_migrations
        from larasanic.support import Config

        asyncio.run(run_migrations(
            Config.get('database.DATABASE_URL'),
            Config.get('database.MODELS')
        ))
    """
    manager = MigrationManager(database_url, models)
    await manager.migrate()
