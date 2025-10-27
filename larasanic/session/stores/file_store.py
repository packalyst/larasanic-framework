"""
File Session Store
Stores sessions as JSON files in the filesystem
"""
import json
import time
from typing import Any, Dict, TYPE_CHECKING
from larasanic.session.store import SessionStore

if TYPE_CHECKING:
    from pathlib import Path


class FileSessionStore(SessionStore):
    """File-based session storage"""

    def __init__(self, path: 'Path'):
        """
        Initialize file session store

        Args:
            path: Path to session storage directory
        """
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

    def _get_session_file(self, session_id: str) -> 'Path':
        """Get path to session file"""
        return self.path / f"session_{session_id}.json"

    async def read(self, session_id: str) -> Dict[str, Any]:
        """Read session from file"""
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            return {}

        try:
            with open(session_file, 'r') as f:
                data = json.load(f)

            # Check if expired
            if data.get('_expire_at', 0) < time.time():
                await self.destroy(session_id)
                return {}

            return data.get('data', {})
        except (json.JSONDecodeError, IOError):
            return {}

    async def write(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Write session to file"""
        session_file = self._get_session_file(session_id)

        try:
            from larasanic.defaults import DEFAULT_SESSION_LIFETIME
            session_data = {
                'data': data,
                '_created_at': time.time(),
                '_expire_at': data.get('_expire_at', time.time() + DEFAULT_SESSION_LIFETIME)
            }

            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)

            return True
        except (IOError, TypeError):
            return False

    async def destroy(self, session_id: str) -> bool:
        """Delete session file"""
        session_file = self._get_session_file(session_id)

        try:
            if session_file.exists():
                session_file.unlink()
            return True
        except IOError:
            return False

    async def gc(self, max_lifetime: int) -> int:
        """Remove expired session files"""
        current_time = time.time()
        deleted = 0

        try:
            for session_file in self.path.glob('session_*.json'):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)

                    if data.get('_expire_at', 0) < current_time:
                        session_file.unlink()
                        deleted += 1
                except (json.JSONDecodeError, IOError):
                    # Corrupted file, delete it
                    session_file.unlink()
                    deleted += 1
        except Exception:
            pass

        return deleted

    async def exists(self, session_id: str) -> bool:
        """Check if session file exists"""
        session_file = self._get_session_file(session_id)
        return session_file.exists()
