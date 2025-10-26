"""
Blade Template Engine Integration
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from blade import BladeEngine

if TYPE_CHECKING:
    from pathlib import Path


class BladeTemplateEngine:
    """Blade template engine wrapper for the framework"""

    def __init__(
        self,
        template_dir: 'Path',
        cache_enabled: bool = True,
        cache_storage_type: str = 'memory',
        cache_dir: Optional['Path'] = None,
        cache_max_size: int = None,
        cache_ttl: int = None,
        track_mtime: bool = True,
        file_extension: str = None,
        allow_python_blocks: bool = False
    ):
        from larasanic.defaults import DEFAULT_BLADE_CACHE_MAX_SIZE, DEFAULT_BLADE_CACHE_TTL, DEFAULT_BLADE_FILE_EXTENSION
        if cache_max_size is None:
            cache_max_size = DEFAULT_BLADE_CACHE_MAX_SIZE
        if cache_ttl is None:
            cache_ttl = DEFAULT_BLADE_CACHE_TTL
        if file_extension is None:
            file_extension = DEFAULT_BLADE_FILE_EXTENSION
        """
        Initialize Blade template engine

        Args:
            template_dir: Path object to directory containing templates
            cache_enabled: Enable template caching
            cache_storage_type: 'memory' (fast) or 'disk' (persistent)
            cache_dir: Path object to directory for disk cache (required if storage_type='disk')
            cache_max_size: Max cache entries
            cache_ttl: Cache time-to-live in seconds
            track_mtime: Auto-reload templates when modified
            file_extension: Template file extension (.blade.php or .html)
            allow_python_blocks: Allow @php blocks (disabled for security)
        """
        # template_dir and cache_dir are Path objects from Storage
        self.template_dir = template_dir
        self.cache_dir = cache_dir

        # Ensure template directory exists
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Ensure cache directory exists if using disk cache
        if cache_storage_type == 'disk' and self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Blade Engine
        self.engine = BladeEngine(
            template_dir=str(self.template_dir),
            cache_enabled=cache_enabled,
            cache_storage_type=cache_storage_type,
            cache_dir=str(self.cache_dir) if self.cache_dir else None,
            cache_max_size=cache_max_size,
            cache_ttl=cache_ttl,
            track_mtime=track_mtime,
            file_extension=file_extension,
            allow_python_blocks=allow_python_blocks
        )

        # Global context (available in all templates)
        self.globals = {}

    def render(self, template_path: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render a template
        Returns:
            Rendered HTML string
        """
      
        # Merge context with globals
        template_context = {}
        template_context.update(self.globals)
        template_context.update(context or {})

        return self.engine.render(template_path, template_context)

    def add_global(self, key: str, value: Any):
        """Add a global variable available in all templates"""
        self.globals[key] = value

    def add_globals(self, globals_dict: Dict[str, Any]):
        """Add multiple global variables"""
        self.globals.update(globals_dict)

    def get_globals(self) -> Dict[str, Any]:
        """Get all global variables"""
        return self.globals.copy()

    def register_directive(self, name: str, handler):
        """Register a custom Blade directive"""
        self.engine.register_directive(name, handler)

    def clear_cache(self):
        """Clear template cache"""
        self.engine.clear_cache()

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return self.engine.get_stats()

    def view_exists(self, template_path: str) -> bool:
        """
        Check if a view/template exists
        Example:
            if blade.view_exists('errors.404'):
                return blade.render('errors.404')
        """
        try:
            # Use the engine's internal method to resolve the template path
            resolved_path = self.engine._resolve_template_path(template_path)
            # Check if the resolved path exists
            import os
            return os.path.exists(resolved_path)
        except Exception:
            # If any error occurs (SecurityError, etc.), consider view as non-existent
            return False