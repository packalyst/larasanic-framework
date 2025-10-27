"""
URL Facade
Generate URLs for routes, paths, and controller actions
"""
from larasanic.support.facades.facade import Facade


class URL(Facade):
    """
    URL Generation Facade

    Provides Laravel-style URL generation using the UrlGenerator service.
    Uses HttpRequest facade for request context automatically.

    Usage:
        from larasanic.support.facades import URL

        URL.route('users.show', {'id': 1})
        URL.to('/users', {'page': 2})
        URL.current()
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        """Get the registered name of the component"""
        return 'url_generator'
