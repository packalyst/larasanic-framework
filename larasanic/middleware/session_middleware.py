"""
Session Middleware
Starts and saves sessions automatically
"""
import random
from sanic import Request, response as sanic_response
from larasanic.middleware.base_middleware import Middleware
from larasanic.session.session_manager import SessionManager
from larasanic.session.stores import FileSessionStore, CookieSessionStore, ArraySessionStore
from larasanic.support import Storage, Crypto, Config
from larasanic.support.facades import HttpRequest, HttpResponse

class SessionMiddleware(Middleware):
    """Session management middleware"""

    # Configuration mapping for MiddlewareConfigMixin
    @staticmethod
    def _get_config_defaults():
        from larasanic.defaults import DEFAULT_SESSION_LIFETIME, DEFAULT_SESSION_COOKIE_NAME, DEFAULT_SESSION_LOTTERY
        return {
            'driver': ('session.DRIVER', 'file'),
            'lifetime': ('session.LIFETIME', DEFAULT_SESSION_LIFETIME),
            'cookie_name': ('session.COOKIE_NAME', DEFAULT_SESSION_COOKIE_NAME),
            'cookie_path': ('session.COOKIE_PATH', '/'),
            'cookie_domain': ('session.COOKIE_DOMAIN', None),
            'cookie_secure': ('session.COOKIE_SECURE', False),
            'cookie_http_only': ('session.COOKIE_HTTP_ONLY', True),
            'cookie_same_site': ('session.COOKIE_SAME_SITE', 'Lax'),
            'lottery': ('session.SESSION_LOTTERY', DEFAULT_SESSION_LOTTERY),
        }

    CONFIG_MAPPING = _get_config_defaults.__func__()
    DEFAULT_ENABLED = True

    @classmethod
    def _is_enabled(cls) -> bool:
        """Check if middleware should be enabled"""
        import sys

        # Disable for setup commands (they need to run before secrets exist)
        if 'main.py' in sys.argv[0] and len(sys.argv) > 1:
            if sys.argv[1] in ['app:setup', 'setup_app']:
                return False

        # Check if APP_SECRET_KEY exists for cookie driver
        from larasanic.support import Config
        driver = Config.get('session.DRIVER', 'file')

        if driver == 'cookie':
            secret = Config.get('app.APP_SECRET_KEY')
            if not secret:
                # Only raise error if not in setup mode
                raise ValueError(
                    "APP_SECRET_KEY is required for cookie session driver!\n"
                    "Run: python main.py app:setup\n"
                    "Or manually set APP_SECRET_KEY in .env file"
                )

        return True

    def __init__(self, driver='file', lifetime=None, cookie_name=None,
                 cookie_path='/', cookie_domain=None, cookie_secure=False,
                 cookie_http_only=True, cookie_same_site='Lax', lottery=None):
        """Initialize session middleware"""
        from larasanic.defaults import DEFAULT_SESSION_LIFETIME, DEFAULT_SESSION_COOKIE_NAME, DEFAULT_SESSION_LOTTERY
        self.config = {
            'driver': driver,
            'lifetime': lifetime or DEFAULT_SESSION_LIFETIME,
            'cookie_name': cookie_name or DEFAULT_SESSION_COOKIE_NAME,
            'cookie_path': cookie_path,
            'cookie_domain': cookie_domain,
            'cookie_secure': cookie_secure,
            'cookie_http_only': cookie_http_only,
            'cookie_same_site': cookie_same_site,
            'lottery': lottery or DEFAULT_SESSION_LOTTERY,
        }
        self.store = self._create_store()

    def _load_config(self) -> dict:
        """Load session configuration - deprecated, kept for compatibility"""
        return self.config

    def _create_store(self):
        """Create session store based on driver"""
        driver = self.config['driver']

        if driver == 'file':
            path = Storage.sessions()
            return FileSessionStore(path)

        elif driver == 'cookie':
            # Use APP_SECRET_KEY from app config (shared across all features)
            secret = Config.get('app.APP_SECRET_KEY')

            if not secret:
                raise ValueError(
                    "APP_SECRET_KEY is required for cookie session driver!\n"
                    "Run: python main.py setup_app\n"
                    "Or manually set APP_SECRET_KEY in .env file"
                )

            return CookieSessionStore(secret)

        elif driver == 'array':
            return ArraySessionStore()

        else:
            # Default to array for unknown drivers
            return ArraySessionStore()

    def _get_session_id(self, request: Request) -> str:
        """Get session ID from cookie or generate new one"""
        cookie_name = self.config['cookie_name']

        # Try to get from cookie
        session_id = HttpRequest.get_cookie(cookie_name)

        if not session_id:
            # Generate new session ID
            session_id = Crypto.generate_token(40)

        return session_id

    async def before_request(self, request: Request):
        """Start session before request"""
        # Get or generate session ID
        session_id = self._get_session_id(request)

        # Create session manager
        session = SessionManager(
            store=self.store,
            session_id=session_id,
            lifetime=self.config['lifetime']
        )

        # Load session data
        await session.start()

        # Attach to request context
        HttpRequest.set_session(session)

        return None

    async def after_response(self, request: Request, response):
        """Save session after response"""
        # Get session from request context
        session = HttpRequest.get_session()
        if not session:
            return response

        # Save session
        await session.save()

        # Set session cookie
        self._set_session_cookie(response, session)

        # Run garbage collection (with lottery)
        self._maybe_run_gc()

        return response

    def _set_session_cookie(self, response, session: SessionManager):
        """Set session cookie on response"""
        cookie_name = self.config['cookie_name']

        # For cookie driver, serialize data
        if isinstance(self.store, CookieSessionStore):
            cookie_value = self.store.serialize(session._data)
        else:
            cookie_value = session.get_id()

        # Set cookie using HttpResponse facade
        HttpResponse.add_cookie(
            key=cookie_name,
            value=cookie_value,
            path=self.config['cookie_path'],
            domain=self.config['cookie_domain'],
            secure=self.config['cookie_secure'],
            httponly=self.config['cookie_http_only'],
            samesite=self.config['cookie_same_site'],
            max_age=self.config['lifetime']
        )

    def _maybe_run_gc(self):
        """Maybe run garbage collection based on lottery"""
        lottery = self.config['lottery']
        if random.randint(1, lottery[1]) <= lottery[0]:
            # Run GC in background (non-blocking)
            import asyncio
            asyncio.create_task(self.store.gc(self.config['lifetime']))
