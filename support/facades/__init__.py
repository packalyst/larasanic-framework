"""
Facades Package
Laravel-style facades for static access to services
"""
from larasanic.support.facades.facade import Facade
from larasanic.support.facades.app import App
from larasanic.support.facades.http_request import HttpRequest
from larasanic.support.facades.http_response import HttpResponse
from larasanic.support.facades.http_client import HttpClient
from larasanic.support.facades.auth import Auth
from larasanic.support.facades.route import Route
from larasanic.support.facades.template_blade import TemplateBlade
from larasanic.support.facades.url import URL
from larasanic.support.facades.cache import Cache
from larasanic.support.facades.websocket import WebSocket

__all__ = [
    'Facade',
    'App',
    'HttpRequest',
    'HttpResponse',
    'HttpClient',
    'Auth',
    'Route',
    'TemplateBlade',
    'URL',
    'Cache',
    'WebSocket'
]
