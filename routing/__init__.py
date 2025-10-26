"""
Routing Package
Core routing classes (NOT facades)

Note: Route facade is available from larasanic.support.facades
      from larasanic.support.facades import Route

      URL facade is available from larasanic.support.facades
      from larasanic.support.facades import URL

Moved to framework.http:
- UrlGenerator → framework.http.url (URL generation is HTTP concern)
- ResourceRegistrar → framework.http.resource (RESTful CRUD is HTTP concern)
"""
# Core routing classes
from larasanic.routing.router import Router, RouteRegistrar
from larasanic.routing.route import Route as RouteClass
from larasanic.routing.route_collection import RouteCollection
from larasanic.routing.route_middleware_registry import RouteMiddlewareRegistry

__all__ = [
    'Router',
    'RouteClass',
    'RouteCollection',
    'RouteRegistrar',
    'RouteMiddlewareRegistry',
]
