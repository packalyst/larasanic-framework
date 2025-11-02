"""
Framework Default Values
All hardcoded values should be defined here and accessed via Config.get()
This file contains sensible defaults that can be overridden in .env or other config files
"""

# ============================================================================
# NETWORK DEFAULTS
# ============================================================================

# Application Server
DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8000

# ============================================================================
# REDIS DEFAULTS
# ============================================================================

DEFAULT_REDIS_URL = 'redis://localhost:6379/0'

# ============================================================================
# HTTP CLIENT DEFAULTS
# ============================================================================

DEFAULT_HTTP_USER_AGENT = 'LarasanicFramework/1.0'
DEFAULT_HTTP_TIMEOUT = 30  # seconds
DEFAULT_HTTP_MAX_REDIRECTS = 10
DEFAULT_HTTP_CONNECTION_LIMIT = 100
DEFAULT_HTTP_LIMIT_PER_HOST = 30
DEFAULT_HTTP_DNS_CACHE_TTL = 300  # seconds
DEFAULT_HTTP_POOL_CONNECTIONS = 10
DEFAULT_HTTP_POOL_MAXSIZE = 20

# ============================================================================
# SESSION DEFAULTS
# ============================================================================

DEFAULT_SESSION_LIFETIME = 7200  # seconds (2 hours)
DEFAULT_SESSION_COOKIE_NAME = 'framework_session'
DEFAULT_SESSION_ID_LENGTH = 40
DEFAULT_SESSION_LOTTERY = [2, 100]  # [chances, out_of] for garbage collection

# ============================================================================
# CACHE DEFAULTS
# ============================================================================

DEFAULT_CACHE_TTL = 3600  # seconds (1 hour)
DEFAULT_CORS_MAX_AGE = 3600  # seconds (for CORS preflight cache)

# ============================================================================
# SECURITY DEFAULTS
# ============================================================================

# CSRF
DEFAULT_CSRF_TOKEN_LENGTH = 32

# HSTS
DEFAULT_HSTS_MAX_AGE = 31536000  # 1 year

# ============================================================================
# RATE LIMITING DEFAULTS
# ============================================================================

DEFAULT_RATE_LIMIT = 100  # requests
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds
DEFAULT_AUTH_RATE_LIMIT = 20  # requests per minute for auth endpoints

# ============================================================================
# COMPRESSION DEFAULTS
# ============================================================================

DEFAULT_COMPRESSION_MIN_SIZE = 1024  # bytes
DEFAULT_COMPRESSION_LEVEL = 6  # 1-9
DEFAULT_MINIFY_HTML = True

# ============================================================================
# WEBSOCKET DEFAULTS
# ============================================================================

DEFAULT_WS_PATH = '/ws'

# ============================================================================
# BLADE TEMPLATE ENGINE DEFAULTS
# ============================================================================

DEFAULT_BLADE_CACHE_MAX_SIZE = 1000  # templates
DEFAULT_BLADE_CACHE_TTL = 3600  # seconds
DEFAULT_BLADE_FILE_EXTENSION = '.html'

# ============================================================================
# AUTHENTICATION DEFAULTS
# ============================================================================

DEFAULT_TOKEN_LIFETIME_SECONDS = 2592000  # seconds (30 days)

# ============================================================================
# LOGGING DEFAULTS
# ============================================================================

DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_LOG_BACKUP_COUNT = 5

# ============================================================================
# PAGINATION DEFAULTS
# ============================================================================

DEFAULT_PAGINATION_PER_PAGE = 20

# ============================================================================
# FILE OPERATION DEFAULTS
# ============================================================================

DEFAULT_FILE_CHUNK_SIZE = 8192  # bytes (8KB)