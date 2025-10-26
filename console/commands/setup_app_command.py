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

            # Step 3: Generate JWT keys
            if not await self._generate_keys():
                return 1

            # Step 4: Initialize database
            if not await self._init_database():
                return 1

            self.line()
            self.success("✅ Application setup completed successfully!")
            self.line()
            self.line("Next steps:")
            self.line("  1. Review and edit .env file with your configuration")
            self.line("  2. Run: python main.py")
            self.line()
            
            return 0
        except Exception as e:
            self.error(f"Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

    async def _setup_storage(self) -> bool:
        self.info("Step 0/4: Setting up storage ...")
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
            self.info("Step 1/4: Setting up environment file...")

            env_path = Storage.base('.env')
            template_path = Storage.base('.env.template')

            # Check if .env already exists
            if env_path.exists():
                self.warning(f"  .env file already exists")
                if not self.confirm("  Overwrite existing .env file?", default=False):
                    self.info("  Skipping .env setup")
                    return True

                # Backup existing .env
                backup_path = Storage.base('.env.backup')
                shutil.copy(env_path, backup_path)
                self.line(f"  Created backup: .env.backup")

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
        """Generate CSRF secret"""
        try:
            self.info("Step 2/4: Generating secrets...")

            # Generate CSRF secret
            csrf_secret = Crypto.generate_token(32)

            # Save to .env file
            EnvHelper.set('CSRF_SECRET', csrf_secret)

            self.success(f"  Generated CSRF_SECRET")
            return True

        except Exception as e:
            self.error(f"  Failed to generate secrets: {e}")
            return False

    async def _generate_keys(self) -> bool:
        """Generate JWT keys"""
        try:
            self.info("Step 3/4: Generating JWT keys...")

            # Get or generate JWT_KEY_NAME
            key_name = EnvHelper.get('JWT_KEY_NAME')

            if not key_name:
                # Generate random key name
                random_suffix = Crypto.generate_secret(8)
                key_name = f"jwt_{random_suffix}"

                # Save to .env file
                EnvHelper.set('JWT_KEY_NAME', key_name)
                self.line(f"  Generated JWT_KEY_NAME: {key_name}")

            public_key_path, private_key_path = Storage.get_jwt_paths()

            # Check if keys already exist
            if Storage.exists(private_key_path) or Storage.exists(public_key_path):
                self.warning("  JWT keys already exist")
                if not self.confirm("  Regenerate JWT keys?", default=False):
                    self.info("  Skipping JWT key generation")
                    return True

                # Delete existing keys
                if Storage.exists(private_key_path):
                    Storage.unlink(private_key_path)
                if Storage.exists(public_key_path):
                    Storage.unlink(public_key_path)

            # Ensure keys directory exists
            Storage.ensure_directory(Storage.keys())

            # Generate RSA key pair
            private_pem, public_pem = Crypto.generate_rsa_keypair(key_size=2048)

            # Save keys
            Crypto.save_rsa_keypair(private_pem, public_pem, private_key_path, public_key_path)

            self.success(f"  Generated JWT keys")
            self.line(f"    Private: {private_key_path}")
            self.line(f"    Public: {public_key_path}")
            return True

        except Exception as e:
            self.error(f"  Failed to generate keys: {e}")
            import traceback
            traceback.print_exc()
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
