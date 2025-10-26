"""
Database Manager
Handles Tortoise ORM initialization and connection management
"""
from tortoise import Tortoise
from typing import Dict, Any, List
from larasanic.support import Config

class DatabaseManager:
    """Manages database connections and Tortoise ORM"""

    def __init__(self,include_aerich=False):
        """
        Initialize database manager
        """
        from larasanic.support import Storage
        self.database_url = Config.get('database.DATABASE_URL')
        self.models = Config.get('database.MODELS', [])
        self.migrations_path = Storage.database('migrations')
        Storage.ensure_directory(self.migrations_path)
        self._initialized = False
        self.include_aerich = include_aerich
        self.app_label = 'models'

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite"""
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL"""
        return self.database_url.startswith("postgres")

    def get_aerich_config(self) -> Dict[str, Any]:
        """
        Get Aerich configuration

        Returns:
            Aerich configuration dict
        """
        # Only include aerich.models if migrations have been initialized
        models = list(self.models)
        if self.include_aerich and "aerich.models" not in models:
            models.append("aerich.models")

        return {
            "connections": {"default": self.database_url},
            "apps": {
                self.app_label: {
                    "models": models,
                    "default_connection": "default",
                }
            },
        }

    async def init(self):
        """Initialize Tortoise ORM"""
        if self._initialized:
            return

        config = self.get_aerich_config()
        await Tortoise.init(config)

        # Test the connection
        try:
            connection = Tortoise.get_connection("default")
            # Try a simple query to verify connection works
            await connection.execute_query("SELECT 1")
        except Exception as e:
            print("\n" + "=" * 70)
            print("❌ DATABASE CONNECTION TEST FAILED")
            print(f"\nConnected to database but query failed: {e}")
            print("=" * 70)
            print(f"Database URL: {self.database_url}")
            print("=" * 70)
            import sys
            sys.exit(1)

        # SQLite optimizations
        if self.is_sqlite:
            await self._setup_sqlite_pragmas()
        self._initialized = True

    async def _setup_sqlite_pragmas(self):
        """Setup SQLite performance optimizations"""
        connection = Tortoise.get_connection("default")

        # Enable WAL mode for better concurrency
        await connection.execute_query("PRAGMA journal_mode=WAL")

        # Synchronous mode for better performance (still safe with WAL)
        await connection.execute_query("PRAGMA synchronous=NORMAL")

        # Increase cache size (in pages, negative = KB)
        await connection.execute_query("PRAGMA cache_size=-64000")  # 64MB

        # Enable foreign keys
        await connection.execute_query("PRAGMA foreign_keys=ON")

        # Optimize for modern storage
        await connection.execute_query("PRAGMA temp_store=MEMORY")

    async def _aerich_command(self):
        """Helper to get Aerich Command instance."""
        from aerich import Command
        return Command(
            tortoise_config=self.get_aerich_config(),
            app=self.app_label,
            location=str(self.migrations_path),
        )
    
    async def aerich_init(self):
        """Detect schema and create initial migration."""
        cmd = await self._aerich_command()
        await cmd.init()
        await cmd.init_db(safe=True)
        await self.generate_schemas(safe=True)
        await cmd.migrate(name="initial")
        await cmd.upgrade()
        return "🏁 Created baseline migration."
        
    async def aerich_status(self):
        """Show migration status."""
        cmd = await self._aerich_command()
        await cmd.init()
        # must include aerich.models in config
        from aerich.models import Aerich
        return  await Aerich.all().values("app", "version")

    async def aerich_make_migration(self, name: str):
        """Generate a new migration file (like 'make:migration')."""
        cmd = await self._aerich_command()
        await cmd.init()
        from datetime import datetime

        # Timestamp prefix (Laravel-style)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_name = f"{timestamp}_{name}"

        return await cmd.migrate(name=full_name)

    async def aerich_migrate(self):
        """Apply pending migrations."""
        cmd = await self._aerich_command()
        await cmd.init()
        return await cmd.upgrade(run_in_transaction=True)

    async def aerich_rollback(self, steps=-1):
        """Rollback last migration batch."""
        cmd = await self._aerich_command()
        await cmd.init()
        await cmd.downgrade(version=steps, delete=True)
        print("⏪ Rolled back last batch.")

    async def aerich_fresh(self):
        """Drop all tables and re-run all migrations."""
        await Tortoise._drop_databases()
        return self.migrate()

    async def aerich_reset(self):
        """Rollback ALL migrations."""
        cmd = await self._aerich_command()
        await cmd.init()
        while True:
            try:
                await cmd.downgrade(version=-1, delete=True)
            except Exception:
                break
        print("🔁 All migrations rolled back.")

    async def close(self):
        """Close database connections"""
        if self._initialized:
            await Tortoise.close_connections()
            self._initialized = False

    async def generate_schemas(self, safe: bool = True):
        """
        Generate database schemas

        Args:
            safe: If True, don't drop existing tables
        """
        await Tortoise.generate_schemas(safe=safe)

    async def validate_initialized(self):
        """
        Check if database has been initialized with migrations

        Raises:
            RuntimeError: If database is not initialized
        """
        if not self._initialized:
            await self.init()

        try:
            connection = Tortoise.get_connection("default")

            # Check if aerich tracking table exists
            if self.is_sqlite:
                result = await connection.execute_query(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='aerich'"
                )
            elif self.is_postgres:
                result = await connection.execute_query(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='aerich'"
                )
            else:
                # For other databases, skip validation
                return

            # If aerich table doesn't exist, database not initialized
            if not result or len(result[1]) == 0:
                raise RuntimeError(
                    "\n"
                    "╔═══════════════════════════════════════════════════════════╗\n"
                    "║  Database Not Initialized                                ║\n"
                    "╚═══════════════════════════════════════════════════════════╝\n"
                    "\n"
                    "The database has not been initialized yet.\n"
                    "\n"
                    "Initialize the database with:\n"
                    "  ./artisan db:init\n"
                    "\n"
                    "This will create all required tables and migrations.\n"
                )

        except RuntimeError:
            raise
        except Exception as e:
            # If we can't check (table doesn't exist, etc), assume not initialized
            raise RuntimeError(
                "\n"
                "╔═══════════════════════════════════════════════════════════╗\n"
                "║  Database Not Initialized                                ║\n"
                "╚═══════════════════════════════════════════════════════════╝\n"
                "\n"
                "The database has not been initialized yet.\n"
                "\n"
                "Initialize the database with:\n"
                "  ./artisan db:init\n"
                "\n"
                f"Error: {e}\n"
            )
