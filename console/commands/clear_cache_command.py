"""
Clear Cache Command
Clears all application cache (Laravel-style)
"""
from larasanic.console.command import Command
from larasanic.support.facades import Cache


class ClearCacheCommand(Command):
    """Clear application cache"""

    name = "cache:clear"
    description = "Clear all application cache"
    signature = "cache:clear"

    async def handle(self, **kwargs):
        """Clear all cache"""
        try:
            # Flush all cache using Cache facade
            if await Cache.flush():
                self.success("✅ Cache cleared successfully!")
            else:
                self.info("No cache to clear")

            return 0

        except Exception as e:
            self.error(f"❌ Failed to clear cache: {e}")
            return 1
