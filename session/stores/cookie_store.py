"""
Cookie Session Store
Stores session data encrypted in cookies using itsdangerous
"""
from typing import Any, Dict
from larasanic.session.store import SessionStore
from larasanic.support import Crypto


class CookieSessionStore(SessionStore):
    """Cookie-based session storage (encrypted)"""

    def __init__(self, secret_key: str):
        """
        Initialize cookie session store

        Args:
            secret_key: Secret key for encryption
        """
        self.secret_key = secret_key
        self.serializer = Crypto.create_serializer(secret_key)

    async def read(self, session_id: str) -> Dict[str, Any]:
        """
        Read session from encrypted cookie data

        Note: session_id here is the encrypted cookie value

        Args:
            session_id: Encrypted cookie data

        Returns:
            Session data dictionary
        """
        if not session_id:
            return {}

        try:
            # Deserialize and verify signature
            data = self.serializer.loads(session_id)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    async def write(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Write session - returns encrypted data

        Note: Actual cookie writing happens in middleware

        Args:
            session_id: Not used for cookie store
            data: Session data to encrypt

        Returns:
            True (always successful)
        """
        # Cookie store doesn't write here - middleware handles it
        return True

    def serialize(self, data: Dict[str, Any]) -> str:
        """
        Serialize session data for cookie

        Args:
            data: Session data

        Returns:
            Encrypted cookie value
        """
        return self.serializer.dumps(data)

    async def destroy(self, session_id: str) -> bool:
        """
        Destroy session (clear cookie)

        Note: Actual cookie deletion happens in middleware

        Args:
            session_id: Not used

        Returns:
            True
        """
        return True

    async def gc(self, max_lifetime: int) -> int:
        """
        Garbage collection not needed for cookie store

        Args:
            max_lifetime: Not used

        Returns:
            0 (no sessions to clean)
        """
        return 0

    async def exists(self, session_id: str) -> bool:
        """
        Check if session exists

        Args:
            session_id: Encrypted cookie data

        Returns:
            True if valid cookie data
        """
        if not session_id:
            return False

        try:
            self.serializer.loads(session_id)
            return True
        except Exception:
            return False
