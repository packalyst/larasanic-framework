"""
Http Facade
Laravel-style facade for HTTP client operations
"""
from larasanic.support.facades.facade import Facade


class WebSocket(Facade):

    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'ws_manager'