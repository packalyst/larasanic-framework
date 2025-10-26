"""
Route Facade
Provides static access to the Router instance
"""
from larasanic.support.facades.facade import Facade


class Route(Facade):
    """
    Route Facade

    Provides static access to the Router for defining routes.

    Example:
        from larasanic.support.facades import Route

        # Define routes
        Route.get('/users', handler)
        Route.post('/users', handler).name('users.store')

        # Route groups
        Route.prefix('admin').middleware('auth').group(lambda: [
            Route.get('/dashboard', handler)
        ])

        # View routes
        Route.view('/about', 'pages.about')

        # Resource routes
        Route.resource('photos', 'PhotoController')
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'router'
