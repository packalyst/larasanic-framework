"""
Crypto - Centralized cryptography operations
Provides password hashing, token generation, signed data, and key management
"""
import secrets
import hmac
import hashlib
import bcrypt
import jwt
import os
import stat
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from typing import Tuple, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Thread pool for CPU-intensive bcrypt operations
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bcrypt_")


class SecurityError(Exception):
    """Exception raised for security violations"""
    pass


class Crypto:
    """Centralized cryptography helper"""

    # Dummy hash for timing attack prevention
    _DUMMY_HASH = '$2b$12$KIXbF3UGaGm.IhBW8D8VluZJMVZbF5aXpMJPgHw5Z3yE1xYvK5W0a'  # bcrypt hash of empty string

    # === Password Hashing (bcrypt) ===

    @staticmethod
    def hash_password(password: str, rounds: int = None) -> str:
        """
        Hash password using bcrypt (synchronous - use hash_password_async for async contexts)

        Args:
            password: Plain text password
            rounds: Number of bcrypt rounds (default: from config)

        Returns:
            Hashed password string
        """
        if rounds is None:
            from larasanic.support import Config
            rounds = Config.get('security.BCRYPT_ROUNDS')

        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds)).decode('utf-8')

    @staticmethod
    async def hash_password_async(password: str, rounds: int = None) -> str:
        """
        Hash password using bcrypt in thread pool (non-blocking async)

        Args:
            password: Plain text password
            rounds: Number of bcrypt rounds (default: from config)

        Returns:
            Hashed password string
        """
        if rounds is None:
            from larasanic.support import Config
            rounds = Config.get('security.BCRYPT_ROUNDS')

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds)).decode('utf-8')
        )

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against bcrypt hash (synchronous - use verify_password_async for async contexts)

        Args:
            password: Plain text password
            hashed: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except (ValueError, TypeError):
            return False

    @staticmethod
    async def verify_password_async(password: str, hashed: str) -> bool:
        """
        Verify password against bcrypt hash in thread pool (non-blocking async)

        Args:
            password: Plain text password
            hashed: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _executor,
                lambda: bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            )
        except (ValueError, TypeError):
            return False

    # === CSRF Token Generation (HMAC) ===

    @staticmethod
    def generate_csrf_token(secret_key: str) -> Tuple[str, str]:
        """
        Generate CSRF token and cookie using HMAC-SHA256

        Args:
            secret_key: Secret key for HMAC

        Returns:
            Tuple of (token, cookie)
        """
        cookie = secrets.token_hex(32)
        token = hmac.new(
            secret_key.encode(),
            cookie.encode(),
            hashlib.sha256
        ).hexdigest()
        return token, cookie

    @staticmethod
    def generate_csrf_token_from_cookie(cookie: str, secret_key: str) -> str:
        """
        Generate CSRF token from existing cookie value

        Used for token rotation - regenerate token from same cookie

        Args:
            cookie: Existing CSRF cookie value
            secret_key: Secret key for HMAC

        Returns:
            CSRF token (HMAC of cookie)
        """
        return hmac.new(
            secret_key.encode(),
            cookie.encode(),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_csrf_token(token: str, cookie: str, secret_key: str) -> bool:
        """
        Verify CSRF token against cookie using HMAC

        Args:
            token: CSRF token from header
            cookie: CSRF cookie value
            secret_key: Secret key for HMAC

        Returns:
            True if token is valid, False otherwise
        """
        try:
            expected = hmac.new(
                secret_key.encode(),
                cookie.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(token, expected)
        except Exception:
            return False

    # === Signed Data (itsdangerous) ===

    @staticmethod
    def create_serializer(secret_key: str) -> URLSafeTimedSerializer:
        """
        Create URL-safe timed serializer

        Args:
            secret_key: Secret key for signing

        Returns:
            URLSafeTimedSerializer instance
        """
        return URLSafeTimedSerializer(secret_key)

    @staticmethod
    def sign_data(data: str, secret_key: str) -> str:
        """
        Sign data with secret key using itsdangerous

        Args:
            data: Data to sign
            secret_key: Secret key

        Returns:
            Signed data string
        """
        serializer = Crypto.create_serializer(secret_key)
        return serializer.dumps(data)

    @staticmethod
    def verify_signed_data(signed_data: str, secret_key: str, max_age: int = None) -> Optional[str]:
        """
        Verify and extract signed data

        Args:
            signed_data: Signed data string
            secret_key: Secret key
            max_age: Maximum age in seconds

        Returns:
            Original data if valid, None otherwise
        """
        from larasanic.defaults import DEFAULT_CACHE_TTL
        if max_age is None:
            max_age = DEFAULT_CACHE_TTL
        serializer = Crypto.create_serializer(secret_key)
        try:
            return serializer.loads(signed_data, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None

    # === RSA Key Generation ===

    @staticmethod
    def generate_rsa_keypair(key_size: int = 2048) -> Tuple[bytes, bytes]:
        """
        Generate RSA key pair for JWT signing

        Args:
            key_size: Size of RSA key (default: 2048)

        Returns:
            Tuple of (private_key_pem, public_key_pem) as bytes
        """
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )

        # Serialize private key to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Generate public key
        public_key = private_key.public_key()

        # Serialize public key to PEM format
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem

    @staticmethod
    def save_rsa_keypair(
        private_pem: bytes,
        public_pem: bytes,
        private_key_path: 'Path',
        public_key_path: 'Path'
    ) -> None:
        """
        Save RSA key pair to files with secure permissions

        Args:
            private_pem: Private key in PEM format
            public_pem: Public key in PEM format
            private_key_path: Path to save private key
            public_key_path: Path to save public key
        """
        # Save private key
        private_key_path.write_bytes(private_pem)

        # Set secure permissions on private key (600 = owner read/write only)
        os.chmod(private_key_path, stat.S_IRUSR | stat.S_IWUSR)

        # Save public key
        public_key_path.write_bytes(public_pem)

        # Set public key permissions (644 = owner read/write, group/others read)
        os.chmod(public_key_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    @staticmethod
    def load_rsa_key(key_path: 'Path', is_private: bool = False) -> str:
        """
        Load RSA key from file with security checks

        Args:
            key_path: Path to key file
            is_private: Whether this is a private key (triggers permission check)

        Returns:
            Key content as string

        Raises:
            SecurityError: If private key has insecure permissions
            FileNotFoundError: If key file doesn't exist
        """
        if not key_path.exists():
            raise FileNotFoundError(f"Key file not found: {key_path}")

        # Check permissions for private keys
        if is_private:
            stat_info = key_path.stat()
            file_mode = stat_info.st_mode

            # Check if group or others have any permissions (should be 600)
            if file_mode & (stat.S_IRWXG | stat.S_IRWXO):
                current_perms = oct(file_mode & 0o777)
                raise SecurityError(
                    f"Private key {key_path} has insecure permissions ({current_perms}). "
                    f"Fix with: chmod 600 {key_path}"
                )

        return key_path.read_text()

    # === JWT Token Operations ===

    @staticmethod
    async def generate_jwt_token(
        user_id: int,
        private_key: str,
        algorithm: str,
        ttl_seconds: int,
        token_type: str
    ) -> str:
        """
        Generate JWT token in thread pool (non-blocking async)

        Args:
            user_id: User ID to encode
            private_key: RSA private key for signing
            algorithm: JWT algorithm (e.g., RS256)
            ttl_seconds: Time to live in seconds
            token_type: Token type (access/refresh)

        Returns:
            JWT token string
        """
        def _generate():
            payload = {
                "user_id": user_id,
                "type": token_type,
                "exp": datetime.utcnow() + timedelta(seconds=ttl_seconds),
                "iat": datetime.utcnow()
            }
            return jwt.encode(payload, private_key, algorithm=algorithm)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _generate)

    @staticmethod
    def verify_jwt_token(
        token: str,
        public_key: str,
        algorithm: str,
        expected_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token

        Args:
            token: JWT token to verify
            public_key: RSA public key for verification
            algorithm: JWT algorithm (e.g., RS256)
            expected_type: Expected token type (optional)

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, public_key, algorithms=[algorithm])

            # Check token type if specified
            if expected_type and payload.get("type") != expected_type:
                return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None

    @staticmethod
    def extract_jwt_user_id(
        token: str,
        public_key: str,
        algorithm: str,
        expected_type: Optional[str] = None
    ) -> Optional[int]:
        """
        Extract user ID from JWT token

        Args:
            token: JWT token
            public_key: RSA public key for verification
            algorithm: JWT algorithm (e.g., RS256)
            expected_type: Expected token type (optional)

        Returns:
            User ID if valid, None otherwise
        """
        if not token:
            return None

        payload = Crypto.verify_jwt_token(token, public_key, algorithm, expected_type)
        if payload:
            return payload.get("user_id")
        return None

    # === Random Token Generation ===

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate URL-safe random token

        Args:
            length: Length of token in bytes (default: 32)

        Returns:
            URL-safe random string
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_secret(length: int = 32) -> str:
        """
        Generate random hex secret

        Args:
            length: Length of secret in bytes (default: 32)

        Returns:
            Random hex string
        """
        return secrets.token_hex(length)

    # === Hash Functions ===

    @staticmethod
    def sha256(data: str) -> str:
        """
        Generate SHA256 hash of string

        Args:
            data: String to hash

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def sha256_bytes(data: bytes) -> str:
        """
        Generate SHA256 hash of bytes

        Args:
            data: Bytes to hash

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def md5(data: str) -> str:
        """
        Generate MD5 hash (use only for non-security purposes)

        Args:
            data: String to hash

        Returns:
            MD5 hex digest
        """
        return hashlib.md5(data.encode()).hexdigest()

    @staticmethod
    def calculate_file_hash(file_path: 'Path', chunk_size: int = None) -> str:
        """
        Calculate SHA256 hash of entire file

        Args:
            file_path: Path to file
            chunk_size: Chunk size for reading

        Returns:
            SHA256 hex digest
        """
        from larasanic.defaults import DEFAULT_FILE_CHUNK_SIZE
        if chunk_size is None:
            chunk_size = DEFAULT_FILE_CHUNK_SIZE
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    @staticmethod
    def calculate_partial_file_hash(file_path: 'Path', partial_size: int = 65536) -> str:
        """
        Calculate partial hash of file (first + last chunks + size)
        Much faster for large files, still catches most duplicates

        Args:
            file_path: Path to file
            partial_size: Size of chunks to hash from start/end (default: 64KB)

        Returns:
            SHA256 hex digest
        """
        sha256_hash = hashlib.sha256()
        file_size = file_path.stat().st_size

        # Include file size in hash
        sha256_hash.update(str(file_size).encode())

        with open(file_path, "rb") as f:
            # Hash first chunk
            first_chunk = f.read(partial_size)
            sha256_hash.update(first_chunk)

            # Hash last chunk if file is large enough
            if file_size > partial_size * 2:
                f.seek(-partial_size, 2)  # Seek from end
                last_chunk = f.read(partial_size)
                sha256_hash.update(last_chunk)

        return sha256_hash.hexdigest()
