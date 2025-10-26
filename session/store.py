"""
Session Store Interface
Base class for all session storage drivers
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class SessionStore(ABC):
    """Base session store interface"""

    @abstractmethod
    async def read(self, session_id: str) -> Dict[str, Any]:
        """
        Read session data from storage

        Args:
            session_id: Session identifier

        Returns:
            Session data dictionary
        """
        pass

    @abstractmethod
    async def write(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Write session data to storage

        Args:
            session_id: Session identifier
            data: Session data to store

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def destroy(self, session_id: str) -> bool:
        """
        Delete session from storage

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def gc(self, max_lifetime: int) -> int:
        """
        Garbage collection - remove expired sessions

        Args:
            max_lifetime: Maximum session lifetime in seconds

        Returns:
            Number of sessions deleted
        """
        pass

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """
        Check if session exists

        Args:
            session_id: Session identifier

        Returns:
            True if session exists
        """
        pass
