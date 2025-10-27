"""
Array Session Store
Stores sessions in memory (for testing only)
"""
from typing import Any, Dict
from larasanic.session.store import SessionStore


class ArraySessionStore(SessionStore):
    """
    In-memory session storage

    WARNING: Not suitable for production use.
    Sessions are lost when the application restarts.
    """

    def __init__(self):
        """Initialize array session store"""
        self._sessions: Dict[str, Dict[str, Any]] = {}

    async def read(self, session_id: str) -> Dict[str, Any]:
        """Read session from memory"""
        return self._sessions.get(session_id, {}).copy()

    async def write(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Write session to memory"""
        self._sessions[session_id] = data.copy()
        return True

    async def destroy(self, session_id: str) -> bool:
        """Delete session from memory"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        return True

    async def gc(self, max_lifetime: int) -> int:
        """Garbage collection not needed for array store"""
        return 0

    async def exists(self, session_id: str) -> bool:
        """Check if session exists in memory"""
        return session_id in self._sessions

    def clear_all(self):
        """Clear all sessions (useful for testing)"""
        self._sessions.clear()
