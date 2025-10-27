"""
Secure HTTP Client
Provides both async (aiohttp) and sync (requests) HTTP clients with security features.
"""

import asyncio
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, urljoin
import ssl
import certifi
from larasanic.logging import getLogger

import aiohttp
import requests
from aiohttp import ClientTimeout, TCPConnector
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for HTTP clients"""
    STRICT = "strict"      # Maximum security, may break some sites
    BALANCED = "balanced"  # Good security with compatibility
    RELAXED = "relaxed"    # Minimal security for testing


class URLValidator:
    """URL validation and sanitization"""

    # Blocked URL patterns for security
    BLOCKED_PATTERNS = [
        'file://',
        'ftp://',
        'gopher://',
        'javascript:',
        'data:',
    ]

    # Private IP ranges to block SSRF attacks
    PRIVATE_IP_RANGES = [
        '10.',
        '172.16.', '172.17.', '172.18.', '172.19.',
        '172.20.', '172.21.', '172.22.', '172.23.',
        '172.24.', '172.25.', '172.26.', '172.27.',
        '172.28.', '172.29.', '172.30.', '172.31.',
        '192.168.',
        '127.',
        'localhost',
        '0.0.0.0',
    ]

    @classmethod
    def validate_url(cls, url: str, allow_private: bool = False) -> bool:
        """
        Validate URL for security issues

        Args:
            url: URL to validate
            allow_private: Whether to allow private IPs

        Returns:
            True if URL is safe
        """
        if not url:
            return False

        # Check for blocked protocols
        for pattern in cls.BLOCKED_PATTERNS:
            if url.lower().startswith(pattern):
                logger.warning(f"Blocked URL protocol: {pattern} in {url}")
                return False

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            return False

        # Ensure HTTP/HTTPS only
        if parsed.scheme not in ('http', 'https'):
            logger.warning(f"Invalid URL scheme: {parsed.scheme}")
            return False

        # Check for private IPs (SSRF prevention)
        if not allow_private and parsed.hostname:
            hostname = parsed.hostname.lower()
            for private_range in cls.PRIVATE_IP_RANGES:
                if hostname.startswith(private_range):
                    logger.warning(f"Blocked private IP: {hostname}")
                    return False

        return True

    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """
        Sanitize URL by removing dangerous characters

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL
        """
        # Remove null bytes and control characters
        url = ''.join(char for char in url if ord(char) >= 32)

        # Strip whitespace
        url = url.strip()

        # Ensure proper encoding
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return url

        # Try to fix missing scheme
        if not parsed.scheme and url.startswith('//'):
            url = 'https:' + url
        elif not parsed.scheme:
            url = 'https://' + url

        return url


class SecureHTTPClient:
    """Base class for secure HTTP clients"""

    # Secure default headers
    @staticmethod
    def _get_default_headers():
        from larasanic.defaults import DEFAULT_HTTP_USER_AGENT
        return {
            'User-Agent': DEFAULT_HTTP_USER_AGENT,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
        }

    SECURE_HEADERS = _get_default_headers.__func__()

    # Security headers to strip from responses
    STRIPPED_HEADERS = [
        'server',
        'x-powered-by',
        'x-aspnet-version',
        'x-aspnetmvc-version',
    ]

    def __init__(
        self,
        security_level: SecurityLevel = SecurityLevel.BALANCED,
        timeout: int = None,
        max_retries: int = 1,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        max_redirects: int = None,
        proxy: Optional[str] = None,
        rate_limit: Optional[Tuple[int, int]] = None,
    ):
        """
        Initialize secure HTTP client

        Args:
            security_level: Security level to use
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            verify_ssl: Whether to verify SSL certificates
            follow_redirects: Whether to follow redirects
            max_redirects: Maximum number of redirects
            proxy: Proxy URL
            rate_limit: (max_requests, window_seconds)
        """
        from larasanic.defaults import DEFAULT_HTTP_TIMEOUT, DEFAULT_HTTP_MAX_REDIRECTS
        self.security_level = security_level
        self.timeout = timeout if timeout is not None else DEFAULT_HTTP_TIMEOUT
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects if max_redirects is not None else DEFAULT_HTTP_MAX_REDIRECTS
        self.proxy = proxy
        self.rate_limit = rate_limit

        # Rate limiting
        if rate_limit:
            self.rate_limiter = RateLimiter(rate_limit[0], rate_limit[1])
        else:
            self.rate_limiter = None

        # Request history for debugging
        self.request_history: List[Dict[str, Any]] = []
        self.max_history = 100

    def _get_secure_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get secure headers with custom overrides"""
        headers = self.SECURE_HEADERS.copy()

        # Add security headers based on level
        if self.security_level == SecurityLevel.STRICT:
            headers.update({
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Referrer-Policy': 'no-referrer',
            })
        elif self.security_level == SecurityLevel.BALANCED:
            headers.update({
                'X-Content-Type-Options': 'nosniff',
                'Referrer-Policy': 'strict-origin-when-cross-origin',
            })

        # Apply custom headers
        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _log_request(self, method: str, url: str, status: Optional[int] = None, error: Optional[str] = None):
        """Log request for debugging"""
        entry = {
            'timestamp': time.time(),
            'method': method,
            'url': url,
            'status': status,
            'error': error,
        }

        self.request_history.append(entry)

        # Limit history size
        if len(self.request_history) > self.max_history:
            self.request_history.pop(0)

    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()


class RateLimiter:
    """Simple rate limiter"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[float] = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()

        # Remove old requests
        self.requests = [t for t in self.requests if t > now - self.window_seconds]

        # Check if we need to wait
        if len(self.requests) >= self.max_requests:
            oldest = min(self.requests)
            wait_time = self.window_seconds - (now - oldest) + 0.1
            if wait_time > 0:
                time.sleep(wait_time)

        self.requests.append(now)


class AsyncHTTPClient(SecureHTTPClient):
    """Secure async HTTP client using aiohttp"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Start the client session"""
        if self.session:
            return

        # Configure SSL
        ssl_context = None
        if self.verify_ssl:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            if self.security_level == SecurityLevel.STRICT:
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        # Configure connector
        from larasanic.defaults import DEFAULT_HTTP_CONNECTION_LIMIT, DEFAULT_HTTP_LIMIT_PER_HOST, DEFAULT_HTTP_DNS_CACHE_TTL
        connector = TCPConnector(
            ssl=ssl_context,
            limit=DEFAULT_HTTP_CONNECTION_LIMIT,
            limit_per_host=DEFAULT_HTTP_LIMIT_PER_HOST,
            ttl_dns_cache=DEFAULT_HTTP_DNS_CACHE_TTL,
            enable_cleanup_closed=True,
        )

        # Configure timeout
        timeout = ClientTimeout(total=self.timeout)

        # Create session
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=True if self.proxy else False,
        )

    async def close(self):
        """Close the client session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make a secure GET request

        Args:
            url: URL to request
            params: Query parameters
            headers: Custom headers
            **kwargs: Additional arguments for aiohttp

        Returns:
            Response object
        """
        return await self._request('GET', url, params=params, headers=headers, **kwargs)

    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make a secure POST request

        Args:
            url: URL to request
            data: Form data
            json: JSON data
            headers: Custom headers
            **kwargs: Additional arguments for aiohttp

        Returns:
            Response object
        """
        return await self._request('POST', url, data=data, json=json, headers=headers, **kwargs)

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make a secure request

        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Additional arguments

        Returns:
            Response object
        """
        # Validate and sanitize URL
        url = URLValidator.sanitize_url(url)
        if not URLValidator.validate_url(url, allow_private=(self.security_level == SecurityLevel.RELAXED)):
            raise ValueError(f"Invalid or unsafe URL: {url}")

        # Check rate limit
        self._check_rate_limit()

        # Ensure session is started
        if not self.session:
            await self.start()

        # Prepare headers
        headers = self._get_secure_headers(kwargs.pop('headers', None))

        # Configure request
        request_kwargs = {
            'headers': headers,
            'allow_redirects': self.follow_redirects,
            'max_redirects': self.max_redirects,
            **kwargs
        }

        # Add proxy if configured
        if self.proxy:
            request_kwargs['proxy'] = self.proxy

        # Make request with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.session.request(method, url, **request_kwargs)

                # Log successful request
                self._log_request(method, url, response.status)

                # Check status
                response.raise_for_status()

                return response

            except aiohttp.ClientError as e:
                last_error = e
                self._log_request(method, url, error=str(e))

                # Wait before retry
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")

        # All retries failed
        raise last_error or Exception("Request failed")

    async def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """Get JSON response"""
        response = await self.get(url, **kwargs)
        return await response.json()

    async def post_json(self, url: str, json_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Post JSON and get JSON response"""
        response = await self.post(url, json=json_data, **kwargs)
        return await response.json()

    async def download_file(
        self,
        url: str,
        destination: Union[str, Path],
        chunk_size: int = None,
        progress_callback: Optional[callable] = None,
    ) -> Path:
        from larasanic.defaults import DEFAULT_FILE_CHUNK_SIZE
        if chunk_size is None:
            chunk_size = DEFAULT_FILE_CHUNK_SIZE
        """
        Download file securely

        Args:
            url: URL to download
            destination: Destination file path
            chunk_size: Download chunk size
            progress_callback: Optional progress callback(downloaded, total)

        Returns:
            Path to downloaded file
        """
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        response = await self.get(url)

        # Get total size
        total_size = int(response.headers.get('Content-Length', 0))
        downloaded = 0

        # Download file
        with open(destination, 'wb') as file:
            async for chunk in response.content.iter_chunked(chunk_size):
                file.write(chunk)
                downloaded += len(chunk)

                if progress_callback:
                    progress_callback(downloaded, total_size)

        return destination


class SyncHTTPClient(SecureHTTPClient):
    """Secure sync HTTP client using requests"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a secure requests session"""
        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )

        from larasanic.defaults import DEFAULT_HTTP_POOL_CONNECTIONS, DEFAULT_HTTP_POOL_MAXSIZE
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=DEFAULT_HTTP_POOL_CONNECTIONS,
            pool_maxsize=DEFAULT_HTTP_POOL_MAXSIZE
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Configure SSL verification
        session.verify = certifi.where() if self.verify_ssl else False

        # Configure proxy
        if self.proxy:
            session.proxies = {'http': self.proxy, 'https': self.proxy}

        return session

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make a secure GET request

        Args:
            url: URL to request
            params: Query parameters
            headers: Custom headers
            **kwargs: Additional arguments for requests

        Returns:
            Response object
        """
        return self._request('GET', url, params=params, headers=headers, **kwargs)

    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make a secure POST request

        Args:
            url: URL to request
            data: Form data
            json: JSON data
            headers: Custom headers
            **kwargs: Additional arguments for requests

        Returns:
            Response object
        """
        return self._request('POST', url, data=data, json=json, headers=headers, **kwargs)

    def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        Make a secure request

        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Additional arguments

        Returns:
            Response object
        """
        # Validate and sanitize URL
        url = URLValidator.sanitize_url(url)
        if not URLValidator.validate_url(url, allow_private=(self.security_level == SecurityLevel.RELAXED)):
            raise ValueError(f"Invalid or unsafe URL: {url}")

        # Check rate limit
        self._check_rate_limit()

        # Prepare headers
        headers = self._get_secure_headers(kwargs.pop('headers', None))

        # Configure request
        request_kwargs = {
            'headers': headers,
            'timeout': self.timeout,
            'allow_redirects': self.follow_redirects,
            **kwargs
        }

        # Make request
        try:
            response = self.session.request(method, url, **request_kwargs)

            # Log successful request
            self._log_request(method, url, response.status_code)

            # Check status
            response.raise_for_status()

            return response

        except requests.RequestException as e:
            self._log_request(method, url, error=str(e))
            raise

    def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """Get JSON response"""
        response = self.get(url, **kwargs)
        return response.json()

    def post_json(self, url: str, json_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Post JSON and get JSON response"""
        response = self.post(url, json=json_data, **kwargs)
        return response.json()

    def download_file(
        self,
        url: str,
        destination: Union[str, Path],
        chunk_size: int = None,
        progress_callback: Optional[callable] = None,
    ) -> Path:
        """
        Download file securely

        Args:
            url: URL to download
            destination: Destination file path
            chunk_size: Download chunk size
            progress_callback: Optional progress callback(downloaded, total)

        Returns:
            Path to downloaded file
        """
        from larasanic.defaults import DEFAULT_FILE_CHUNK_SIZE
        if chunk_size is None:
            chunk_size = DEFAULT_FILE_CHUNK_SIZE
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        response = self.get(url, stream=True)

        # Get total size
        total_size = int(response.headers.get('Content-Length', 0))
        downloaded = 0

        # Download file
        with open(destination, 'wb') as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total_size)

        return destination

    def close(self):
        """Close the session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()