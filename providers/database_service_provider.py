"""
Database Service Provider
Registers database services and initializes Tortoise ORM
"""
from larasanic.service_provider import ServiceProvider
from larasanic.database.database_manager import DatabaseManager
from larasanic.support.facades import App


class DatabaseServiceProvider(ServiceProvider):
    """Database layer service provider"""

    def register(self):
        """Register database services"""
        # Create database manager
        db_manager = DatabaseManager()

        # Register as singleton
        App.singleton('db', db_manager)

    def boot(self):
        """Bootstrap database services"""
        # Database initialization happens in the application lifecycle
        # We'll register the startup/shutdown handlers
        db_manager = App.make('db')

        @self.app.sanic_app.before_server_start
        async def init_db(app, loop):
            """Initialize database on server start"""
            await db_manager.init()

        @self.app.sanic_app.after_server_stop
        async def close_db(app, loop):
            """Close database on server stop"""
            await db_manager.close()
