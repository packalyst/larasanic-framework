"""
Setup App Command
Complete application setup: env, secrets, keys, and database
"""
from larasanic.console.command import Command
from larasanic.support import Storage, Crypto,EnvHelper
from larasanic.database.database_manager import DatabaseManager
import shutil


class SetupAppCommand(Command):
    """Complete application setup workflow"""

    name = "app:setup"
    description = "Complete application setup (env, secrets, keys, database)"
    signature = "app:setup"

    async def handle(self, **kwargs):
        """Run complete application setup"""
        try:
            self.info("🚀 Starting application setup...\n")
            if not await self._setup_storage():
                return 1

            # Step 1: Copy .env.template to .env
            if not await self._setup_env():
                return 1

            # Step 2: Generate secrets
            if not await self._generate_secrets():
                return 1
            
            # Step 4: Cache settings
            if not await self._setup_cache():
                return 1
            
            # Step 5: Initialize database
            if not await self._init_database():
                return 1

            self.line()
            self.success("✅ Application setup completed successfully!")
            self.line()
            self.line("Next steps:")
            self.line("  1. Review and edit .env file with your configuration")
            self.line("  2. Run: python main.py")
            self.line()
            Storage.mark_setup_complete()
            return 0
        except Exception as e:
            self.error(f"Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

    async def _setup_storage(self) -> bool:
        self.info("Step 1/5: Setting up storage ...")
        if Storage.is_setup_complete():
            self.warning(f"Storage is initialized")
            if not self.confirm("This will DELETE everything in storage folder", default=False):
                self.info(" Existing")
                return False
            Storage.delete_storage()
        Storage.create_storage_structure()
        return True
   
    async def _setup_env(self) -> bool:
        """Copy .env.template to .env"""
        try:
            self.info("Step 2/5: Setting up environment file...")

            env_path = Storage.base('.env')
            template_path = Storage.base('.env.template')

            # Check if .env already exists
            if env_path.exists():
                self.warning(f"  .env file already exists")
                if not self.confirm("  Overwrite existing .env file?", default=False):
                    self.info("  Skipping .env setup")
                    return True

            # Check if template exists
            if not template_path.exists():
                self.error("  .env.template not found!")
                return False

            # Copy template to .env
            shutil.copy(template_path, env_path)
            self.success(f"  Created .env from template")

            # Configure database
            if not await self._configure_database():
                return False

            return True

        except Exception as e:
            self.error(f"  Failed to setup environment: {e}")
            return False

    async def _configure_database(self) -> bool:
        """Configure database connection"""
        try:
            import os

            # Check if DB_CHOICE was set by docker-setup.sh
            db_choice = os.environ.get('DB_CHOICE')

            if not db_choice:
                # Ask user if not pre-selected
                self.line()
                self.info("Configure database:")
                self.line("  [1] SQLite (recommended for development)")
                self.line("  [2] PostgreSQL")
                self.line("  [3] MySQL")
                self.line()
                db_choice = self.ask("Select database type", default="1")
            else:
                self.line()
                self.info(f"Using pre-selected database type: {db_choice}")

            if db_choice == "2":
                # PostgreSQL - use Docker service defaults
                host = self.ask("PostgreSQL host", default="larasanic_db")
                port = self.ask("PostgreSQL port", default="5432")
                user = self.ask("PostgreSQL user", default="larasanic")

                # Use auto-generated password from environment if available
                default_password = os.environ.get('DB_PASSWORD', 'secret')
                password = self.ask("PostgreSQL password", default=default_password)

                database = self.ask("Database name", default="larasanic")
                db_url = f"postgres://{user}:{password}@{host}:{port}/{database}"

            elif db_choice == "3":
                # MySQL
                host = self.ask("MySQL host", default="localhost")
                port = self.ask("MySQL port", default="3306")
                user = self.ask("MySQL user", default="root")
                password = self.ask("MySQL password")
                database = self.ask("Database name", default="framework_db")
                db_url = f"mysql://{user}:{password}@{host}:{port}/{database}"

            else:
                # SQLite (default for choice "1" or any invalid choice)
                db_name = self.ask("Database name", default="database.sqlite3")
                db_path = Storage.database(db_name)
                db_url = f"sqlite://{db_path}"

            # Save to .env
            EnvHelper.set('DATABASE_URL', db_url)
            self.success(f"  Configured DATABASE_URL")
            return True

        except Exception as e:
            self.error(f"  Failed to configure database: {e}")
            return False

    async def _generate_secrets(self) -> bool:
        """Generate APP_SECRET_KEY and CSRF secret"""
        try:
            self.info("Step 3/5: Generating secrets...")

            # Generate APP_SECRET_KEY (used for sessions, cookies, signing)
            app_secret = Crypto.generate_secret(32)  # 64-char hex string
            EnvHelper.set('APP_SECRET_KEY', app_secret)
            self.success(f"  Generated APP_SECRET_KEY")

            # Generate CSRF secret
            csrf_secret = Crypto.generate_token(32)
            EnvHelper.set('CSRF_SECRET', csrf_secret)
            self.success(f"  Generated CSRF_SECRET")

            return True

        except Exception as e:
            self.error(f"  Failed to generate secrets: {e}")
            return False

    async def _setup_cache(self) -> bool:
        """Configure cache driver"""
        try:
            self.info("Step 5/5: Setting up cache...")

            # Import cache stores from config
            from config.cache import CACHE_STORES

            # Ask user to select cache store
            self.line()
            self.info("Configure cache store:")

            # Dynamically list available stores
            stores = list(CACHE_STORES.keys())
            for idx, store in enumerate(stores, 1):
                driver_type = CACHE_STORES[store]['driver']
                self.line(f"  [{idx}] {store} (driver: {driver_type})")

            self.line()
            choice = self.ask("Select cache store", default="1")

            # Map choice to store name
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(stores):
                    cache_choice = stores[choice_idx]
                else:
                    cache_choice = 'file'  # default
            except ValueError:
                cache_choice = 'file'  # default

            # Save CACHE_DRIVER to .env
            EnvHelper.set('CACHE_DRIVER', cache_choice)
            self.success(f"  Configured CACHE_DRIVER: {cache_choice}")

            # Configure Redis if selected
            if CACHE_STORES.get(cache_choice, {}).get('driver') == 'redis':
                if not await self._configure_redis(cache_choice):
                    return False

            return True

        except Exception as e:
            self.error(f"  Failed to setup cache: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _configure_redis(self, store_name: str) -> bool:
        """Configure Redis connection for cache store"""
        # Check if REDIS_URL already exists in .env
        existing_redis_url = EnvHelper.get('REDIS_URL')

        if existing_redis_url:
            self.line()
            self.warning(f"  Found existing REDIS_URL: {existing_redis_url}")
            if self.confirm("  Use existing Redis configuration?", default=True):
                # Test existing connection
                self.line()
                self.info("  Testing Redis connection...")
                if await self._test_redis_connection(existing_redis_url):
                    self.success("  ✓ Redis connection successful!")
                    return True
                else:
                    self.warning("  ✗ Redis connection failed!")
                    self.line()
                    self.line("  What would you like to do?")
                    self.line("    [1] Reconfigure Redis settings")
                    self.line("    [2] Continue anyway (skip Redis)")
                    self.line("    [3] Abort setup")
                    self.line()

                    action = self.ask("  Select option", default="1")

                    if action == "2":
                        self.warning("  Continuing with potentially invalid Redis configuration")
                        return True
                    elif action == "3":
                        self.error("  Redis configuration aborted")
                        return False
                    # If action == "1", fall through to reconfigure below

        # Configure Redis (new or reconfigure)
        while True:
            try:
                self.line()
                self.info(f"Configure Redis for '{store_name}' store:")

                # Ask user for Redis configuration
                host = self.ask("Redis host", default="localhost")
                port = self.ask("Redis port", default="6379")
                db = self.ask("Redis database number", default="0")

                # Ask for password (optional)
                self.line()
                has_password = self.confirm("Does Redis require a password?", default=False)

                if has_password:
                    password = self.ask("Redis password")
                    redis_url = f"redis://:{password}@{host}:{port}/{db}"
                else:
                    redis_url = f"redis://{host}:{port}/{db}"

                # Test connection
                self.line()
                self.info("  Testing Redis connection...")
                if await self._test_redis_connection(redis_url):
                    # Save to .env only if connection successful
                    EnvHelper.set('REDIS_URL', redis_url)
                    self.success("  ✓ Redis connection successful!")
                    self.success(f"  Configured REDIS_URL")
                    return True
                else:
                    self.warning("  ✗ Redis connection failed!")
                    self.line()
                    self.line("  What would you like to do?")
                    self.line("    [1] Reconfigure Redis settings")
                    self.line("    [2] Continue anyway (skip Redis)")
                    self.line("    [3] Abort setup")
                    self.line()

                    action = self.ask("  Select option", default="1")

                    if action == "1":
                        # Loop continues, reconfigure
                        continue
                    elif action == "2":
                        # Save configuration and continue
                        EnvHelper.set('REDIS_URL', redis_url)
                        self.warning("  Continuing with potentially invalid Redis configuration")
                        return True
                    else:
                        # Abort
                        self.error("  Redis configuration aborted")
                        return False

            except Exception as e:
                self.error(f"  Failed to configure Redis: {e}")
                import traceback
                traceback.print_exc()
                return False

    async def _test_redis_connection(self, redis_url: str) -> bool:
        """Test Redis connection"""
        try:
            import redis.asyncio as redis

            # Parse Redis URL and create client
            client = redis.from_url(redis_url, decode_responses=True)

            # Test connection with ping
            await client.ping()

            # Close connection
            await client.close()

            return True

        except ImportError:
            self.warning("  redis package not installed, skipping connection test")
            return True
        except Exception as e:
            self.error(f"  Connection error: {e}")
            return False
    
    async def _init_database(self) -> bool:
        """Initialize database"""
        try:
            self.info("Step 4/4: Initializing database...")

            # Initialize database manager
            db_manager = DatabaseManager(include_aerich=True)
            await db_manager.init()
            try:
                # Don't validate during setup - we're initializing for the first time
                # Run aerich init
                message = await db_manager.aerich_init()
                self.success(f"  {message}")
                return True

            finally:
                # Always close connections
                await db_manager.close()

        except Exception as e:
            self.error(f"  Failed to initialize database: {e}")
            import traceback
            traceback.print_exc()
            return False
