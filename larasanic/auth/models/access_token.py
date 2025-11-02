"""
Access Token Model

Database-backed authentication tokens (like Laravel Sanctum).
Simpler than JWT - tokens are stored in database, logout = delete token.
"""
from tortoise import fields
from larasanic.database.model import Model
import secrets
import hashlib
import time


class AccessToken(Model):
    """
    Access tokens for API/web authentication

    Similar to Laravel Sanctum's personal_access_tokens table.
    When user logs in, we create a token record.
    When user logs out, we delete the token record.
    No JWT, no Redis blacklist - just simple database lookups.
    """

    id = fields.IntField(pk=True)
    user_id = fields.IntField(index=True, description="User who owns this token")
    token_hash = fields.CharField(max_length=64, unique=True, index=True,
                                  description="SHA-256 hash of the token")
    name = fields.CharField(max_length=255, default="auth-token",
                           description="Token name for identification")
    last_used_at = fields.IntField(null=True,
                                   description="Unix timestamp - Last time token was used")
    expires_at = fields.IntField(null=True,
                                 description="Unix timestamp - Token expiration time")
    created_at = fields.IntField(description="Unix timestamp - Token creation time")

    class Meta:
        table = "access_tokens"
        indexes = [
            ("user_id", "token_hash"),  # Composite index for fast lookups
        ]

    def __str__(self):
        return f"Token {self.name} for user {self.user_id}"

    @classmethod
    def generate_token(cls) -> str:
        """
        Generate a random secure token

        Returns:
            Random 64-character token (URL-safe)

        Example:
            >>> token = AccessToken.generate_token()
            >>> # Returns something like: "x7k9m2p4..."
        """
        return secrets.token_urlsafe(48)  # 48 bytes = 64 chars in base64

    @classmethod
    def hash_token(cls, token: str) -> str:
        """
        Hash a token using SHA-256

        We store the hash in the database, not the plain token.
        This way if database is compromised, tokens can't be used.

        Args:
            token: Plain token string

        Returns:
            SHA-256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    async def create_for_user(cls, user_id: int, name: str = "auth-token",
                             expires_in_seconds: int = 24 * 30) -> tuple[str, 'AccessToken']:
        """
        Create a new access token for a user

        Args:
            user_id: User ID
            name: Token name (e.g., "web-token", "mobile-token")
            expires_in_seconds: Token lifetime in seconds 

        Returns:
            Tuple of (plain_token, token_record)
            IMPORTANT: plain_token is only returned once, never stored!

        Example:
            >>> token, record = await AccessToken.create_for_user(user_id=1)
            >>> # Store token in cookie/response
            >>> response.set_cookie('auth_token', token)
        """
        # Generate plain token
        plain_token = cls.generate_token()

        # Hash it
        token_hash = cls.hash_token(plain_token)

        # Calculate expiration (current time + hours in seconds)
        now = int(time.time())
        expires_at = now + expires_in_seconds

        # Create database record
        token_record = await cls.create(
            user_id=user_id,
            token_hash=token_hash,
            name=name,
            expires_at=expires_at,
            created_at=now
        )

        # Return both plain token (to send to user) and record (for reference)
        return plain_token, token_record

    @classmethod
    async def find_by_token(cls, plain_token: str) -> 'AccessToken | None':
        """
        Find token record by plain token

        Args:
            plain_token: The plain token from cookie/header

        Returns:
            AccessToken record if found and valid, None otherwise

        Example:
            >>> token_record = await AccessToken.find_by_token(request.cookies['auth_token'])
            >>> if token_record:
            ...     user = await User.get(id=token_record.user_id)
        """
        token_hash = cls.hash_token(plain_token)

        # Find token and check expiration
        token = await cls.filter(token_hash=token_hash).first()

        if not token:
            return None

        # Check if expired
        now = int(time.time())
        if token.expires_at and token.expires_at < now:
            # Token expired, delete it
            await token.delete()
            return None

        # Update last used timestamp
        token.last_used_at = now
        await token.save()

        return token

    @classmethod
    async def revoke_by_token(cls, plain_token: str) -> bool:
        """
        Revoke (delete) a token

        This is how logout works - just delete the token record.

        Args:
            plain_token: The plain token to revoke

        Returns:
            True if token was found and deleted, False otherwise

        Example:
            >>> await AccessToken.revoke_by_token(request.cookies['auth_token'])
        """
        token_hash = cls.hash_token(plain_token)
        deleted_count = await cls.filter(token_hash=token_hash).delete()
        return deleted_count > 0

    @classmethod
    async def revoke_all_for_user(cls, user_id: int) -> int:
        """
        Revoke all tokens for a user

        Useful for "logout from all devices" feature.

        Args:
            user_id: User ID

        Returns:
            Number of tokens revoked

        Example:
            >>> count = await AccessToken.revoke_all_for_user(user_id=1)
            >>> print(f"Logged out from {count} devices")
        """
        return await cls.filter(user_id=user_id).delete()

    @classmethod
    async def cleanup_expired(cls) -> int:
        """
        Delete all expired tokens

        Run this periodically (e.g., daily cron job) to clean up old tokens.

        Returns:
            Number of tokens deleted

        Example:
            >>> deleted = await AccessToken.cleanup_expired()
            >>> print(f"Cleaned up {deleted} expired tokens")
        """
        now = int(time.time())
        return await cls.filter(expires_at__lt=now).delete()
