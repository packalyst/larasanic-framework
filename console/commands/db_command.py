"""
Database Manager Command
All database and migration operations in one class
"""
from larasanic.console.command import Command

class DbManagerCommand(Command):
    """Database and migration management - all operations in one command"""

    name = "db:manager"
    description = "Database and migration operations"

    # List of subcommands - artisan will display these nicely
    signature = [
        {"command": "db:init", "description": "Initialize database (create tables)"},
        {"command": "db:migrate", "description": "Run pending migrations"},
        {"command": "db:make", "args": "{name}", "description": "Create new migration"},
        {"command": "db:rollback", "args": "{--version=}", "description": "Rollback migrations"},
        {"command": "db:status", "description": "Show migration status"},
        {"command": "db:fresh", "description": "Drop all tables and re-run migrations"},
        {"command": "db:reset", "description": "Rollback all migrations"},
    ]


    async def _handleInit(self):
        """
        Initialize resources before command execution
        Override in subclass if needed for custom initialization
        """
        # Initialize database manager if not already set
        if self.db_manager is None:
            from larasanic.database.database_manager import DatabaseManager
            try:
                self.db_manager = DatabaseManager(include_aerich=True)
                await self.db_manager.init()
            except Exception:
                # Database might not be needed for all commands
                pass
        from larasanic.validation import ValidateApp

    async def _handleClose(self):
        """
        Cleanup resources after command execution
        Override in subclass if needed for custom cleanup
        """
        # Close database manager if it exists
        if self.db_manager:
            try:
                await self.db_manager.close()
            except Exception:
                pass

    async def handle(self, action: str = None, name: str = None, version: int = -1, **kwargs):
        """Handle database commands"""

        if not action:
            self.show_help()
            return 0

        # Route to appropriate handler
        handlers = {
            'init': self.handle_init,
            'migrate': self.handle_migrate,
            'make': self.handle_make,
            'rollback': self.handle_rollback,
            'status': self.handle_status,
            'fresh': self.handle_fresh,
            'reset': self.handle_reset,
        }

        handler = handlers.get(action)
        if not handler:
            self.error(f"Unknown action: {action}")
            self.show_help()
            return 1

        return await handler(name=name, version=version, **kwargs)


    def show_help(self):
        """Show available database commands"""
        self.line("Database Commands:")
        for sig in self.signature:
            cmd = sig['command']
            args = sig.get('args', '')
            desc = sig['description']
            self.line(f"  {cmd} {args:<20} {desc}")

    async def handle_init(self, **kwargs):
        """Initialize database (create tables from models)"""
        try:
            message = await self.db_manager.aerich_init()
            self.success(message)
            return 0

        except Exception as e:
            self.error(f"Failed to initialize database: {e}")
            import traceback
            traceback.print_exc()
            return 1

    async def handle_migrate(self, **kwargs):
        """Run pending migrations"""
        try:
            self.info("Running migrations...")

            # TODO: Implement migrate logic with aerich
            await self.db_manager.aerich_migrate()
            self.success("Migrations completed successfully!")
            return 0

        except Exception as e:
            self.error(f"Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

    async def handle_make(self, name: str = None, **kwargs):
        """Create a new migration"""
        try:
            if not name:
                name = self.ask("Enter migration name")
                if not name:
                    self.error("Migration name is required")
                    return 1

            self.info(f"Creating migration: {name}")
            path = await self.db_manager.aerich_make_migration(name)
            if path:
                self.success(f"📄 Created migration: {path}")
            else:
                self.error("ℹ️ No changes detected.")
            return 0

        except Exception as e:
            self.error(f"Failed to create migration: {e}")
            import traceback
            traceback.print_exc()
            return 1

    async def handle_rollback(self, version: int = -1, **kwargs):
        """Rollback migrations"""
        try:
            if not self.confirm(f"⚠️  Rollback migrations? This may delete data.", default=False):
                self.info("Rollback cancelled.")
                return 0

            self.info(f"Rolling back migrations (version: {version})...")

            await self.db_manager.aerich_rollback()
            
            self.success("Rollback completed successfully!")
            return 0

        except Exception as e:
            self.error(f"Rollback failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

    async def handle_status(self, **kwargs):
        """Show migration status"""
        try:
            self.info("Checking migration status...")

            message = await self.db_manager.aerich_status()
            self.success(message)

            return 0

        except Exception as e:
            self.error(f"Status check failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

    async def handle_fresh(self, **kwargs):
        """Drop all tables and re-run migrations"""
        try:
            self.warning("⚠️  WARNING: This will DROP ALL TABLES and delete all data!")
            self.line()

            if not self.confirm("Are you absolutely sure?", default=False):
                self.info("Fresh migration cancelled.")
                return 0

            confirm_text = self.ask("Type 'yes' to confirm")
            if confirm_text.lower() != 'yes':
                self.info("Fresh migration cancelled.")
                return 0

            self.info("Dropping all tables and running fresh migrations...")

            await self.db_manager.aerich_fresh()

            self.success("Fresh migration completed successfully!")
            return 0

        except Exception as e:
            self.error(f"Fresh migration failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

    async def handle_reset(self, **kwargs):
        """Rollback all migrations"""
        try:
            self.warning("⚠️  This will rollback ALL migrations!")

            if not self.confirm("Are you sure?", default=False):
                self.info("Reset cancelled.")
                return 0

            self.info("Resetting all migrations...")

            await self.db_manager.aerich_reset()

            self.success("Reset completed successfully!")
            return 0

        except Exception as e:
            self.error(f"Reset failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
