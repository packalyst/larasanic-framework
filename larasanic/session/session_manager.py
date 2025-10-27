"""
Session Manager
Laravel-style session management with multiple storage drivers
"""
import time
from typing import Any, Dict, List, Optional
from larasanic.session.store import SessionStore
from larasanic.support import Crypto


class SessionManager:
    """
    Laravel-style session manager

    Provides dictionary-like interface with additional methods:
    - get(), put(), has(), all(), pull(), forget(), flush()
    - flash(), reflash(), keep()
    - regenerate(), invalidate()
    - increment(), decrement(), push()
    """

    def __init__(self, store: SessionStore, session_id: str, lifetime: int = None):
        """
        Initialize session manager

        Args:
            store: Session storage driver
            session_id: Session identifier
            lifetime: Session lifetime in seconds
        """
        if lifetime is None:
            from larasanic.defaults import DEFAULT_SESSION_LIFETIME
            lifetime = DEFAULT_SESSION_LIFETIME
        self.store = store
        self.session_id = session_id
        self.lifetime = lifetime
        self._data: Dict[str, Any] = {}
        self._flash_data: Dict[str, Any] = {}
        self._loaded = False
        self._dirty = False

    async def start(self):
        """Load session data from storage"""
        if self._loaded:
            return

        self._data = await self.store.read(self.session_id)
        self._process_flash_data()
        self._loaded = True

    def _process_flash_data(self):
        """Process flash data (move old flash to delete, keep new flash)"""
        # Get flash keys
        old_flash = self._data.pop('_flash.old', [])
        new_flash = self._data.pop('_flash.new', [])

        # Remove old flash data
        for key in old_flash:
            if key not in new_flash:
                self._data.pop(key, None)

        # Move new flash to old
        self._data['_flash.old'] = new_flash
        self._data['_flash.new'] = []

    # === Data Retrieval ===

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get session value

        Args:
            key: Session key
            default: Default value if key doesn't exist

        Returns:
            Session value or default
        """
        return self._data.get(key, default)

    def all(self) -> Dict[str, Any]:
        """
        Get all session data

        Returns:
            All session data
        """
        # Filter out internal keys
        return {k: v for k, v in self._data.items() if not k.startswith('_')}

    def has(self, key: str) -> bool:
        """
        Check if key exists in session

        Args:
            key: Session key

        Returns:
            True if key exists
        """
        return key in self._data

    def exists(self, key: str) -> bool:
        """Alias for has()"""
        return self.has(key)

    def missing(self, key: str) -> bool:
        """Check if key is missing"""
        return not self.has(key)

    # === Data Storage ===

    def put(self, key: str, value: Any) -> None:
        """
        Store value in session

        Args:
            key: Session key
            value: Value to store
        """
        self._data[key] = value
        self._dirty = True

    def push(self, key: str, value: Any) -> None:
        """
        Push value onto array in session

        Args:
            key: Session key
            value: Value to push
        """
        array = self.get(key, [])
        if not isinstance(array, list):
            array = [array]
        array.append(value)
        self.put(key, array)

    def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment session value

        Args:
            key: Session key
            amount: Amount to increment

        Returns:
            New value
        """
        value = self.get(key, 0)
        new_value = int(value) + amount
        self.put(key, new_value)
        return new_value

    def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement session value

        Args:
            key: Session key
            amount: Amount to decrement

        Returns:
            New value
        """
        return self.increment(key, -amount)

    # === Data Removal ===

    def forget(self, keys: str | List[str]) -> None:
        """
        Remove key(s) from session

        Args:
            keys: Single key or list of keys to remove
        """
        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            self._data.pop(key, None)

        self._dirty = True

    def pull(self, key: str, default: Any = None) -> Any:
        """
        Get and remove value from session

        Args:
            key: Session key
            default: Default value

        Returns:
            Session value or default
        """
        value = self.get(key, default)
        self.forget(key)
        return value

    def flush(self) -> None:
        """Clear all session data"""
        self._data.clear()
        self._dirty = True

    # === Flash Data ===

    def flash(self, key: str, value: Any) -> None:
        """
        Flash data for next request only

        Args:
            key: Flash key
            value: Flash value
        """
        self.put(key, value)
        flash_keys = self._data.get('_flash.new', [])
        if key not in flash_keys:
            flash_keys.append(key)
        self._data['_flash.new'] = flash_keys
        self._dirty = True

    def now(self, key: str, value: Any) -> None:
        """Flash data for current request only"""
        self.put(key, value)
        flash_keys = self._data.get('_flash.old', [])
        if key not in flash_keys:
            flash_keys.append(key)
        self._data['_flash.old'] = flash_keys
        self._dirty = True

    def reflash(self) -> None:
        """Keep all flash data for another request"""
        old_flash = self._data.get('_flash.old', [])
        self._data['_flash.new'] = old_flash
        self._dirty = True

    def keep(self, keys: str | List[str] = None) -> None:
        """
        Keep specific flash data for another request

        Args:
            keys: Keys to keep (None to keep all)
        """
        if keys is None:
            self.reflash()
            return

        if isinstance(keys, str):
            keys = [keys]

        old_flash = self._data.get('_flash.old', [])
        new_flash = self._data.get('_flash.new', [])

        for key in keys:
            if key in old_flash and key not in new_flash:
                new_flash.append(key)

        self._data['_flash.new'] = new_flash
        self._dirty = True

    # === Session Management ===

    def regenerate(self, destroy_old: bool = False) -> str:
        """
        Regenerate session ID

        Args:
            destroy_old: Whether to destroy old session

        Returns:
            New session ID
        """
        from larasanic.defaults import DEFAULT_SESSION_ID_LENGTH
        old_id = self.session_id
        self.session_id = Crypto.generate_token(DEFAULT_SESSION_ID_LENGTH)

        if destroy_old:
            # Will be destroyed in save()
            self._data['_destroy_old_id'] = old_id

        self._dirty = True
        return self.session_id

    async def invalidate(self) -> str:
        """
        Flush session and regenerate ID

        Returns:
            New session ID
        """
        self.flush()
        return self.regenerate(destroy_old=True)

    def get_id(self) -> str:
        """Get current session ID"""
        return self.session_id

    def set_id(self, session_id: str) -> None:
        """Set session ID"""
        self.session_id = session_id

    # === Persistence ===

    async def save(self) -> bool:
        """
        Save session data to storage

        Returns:
            True if successful
        """
        if not self._dirty:
            return True

        # Set expiration
        self._data['_expire_at'] = time.time() + self.lifetime

        # Save to store
        success = await self.store.write(self.session_id, self._data)

        # Destroy old session if regenerated
        if '_destroy_old_id' in self._data:
            old_id = self._data.pop('_destroy_old_id')
            await self.store.destroy(old_id)

        self._dirty = False
        return success

    async def migrate(self, destroy: bool = False) -> bool:
        """
        Migrate session (alias for regenerate + save)

        Args:
            destroy: Destroy old session

        Returns:
            True if successful
        """
        self.regenerate(destroy)
        return await self.save()

    # === Dictionary Interface ===

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style get"""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Dictionary-style set"""
        self.put(key, value)

    def __delitem__(self, key: str) -> None:
        """Dictionary-style delete"""
        self.forget(key)

    def __contains__(self, key: str) -> bool:
        """Dictionary-style contains"""
        return self.has(key)

    def __repr__(self) -> str:
        """String representation"""
        return f"<SessionManager id={self.session_id[:8]}... data={len(self._data)} keys>"
