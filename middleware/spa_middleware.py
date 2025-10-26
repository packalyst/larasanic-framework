from larasanic.middleware.base_middleware import Middleware
from sanic import Request
from typing import Optional
from larasanic.helpers import view
from larasanic.support.facades import HttpRequest
from larasanic.http import ResponseHelper
from larasanic.support import Config

class SpaMiddleware(Middleware):
    """
    SPA Middleware - Handles Single Page Application routing

    Flow:
    1. Direct browser request → Returns base layout with initial_partial set
    2. AJAX request → Returns partial HTML only (no layout)

    This allows the SPA to:
    - Load the shell on first visit
    - Fetch partials via AJAX for navigation
    - Support server-side rendering on direct access
    """

    @classmethod
    def _register_middleware(cls) -> Optional['SpaMiddleware']:
        return cls()

    async def before_request(self, request: Request):
        """
        Handle SPA requests with optimized header detection and SSR
        """
        # Check if we're already in SSR mode to prevent infinite recursion
        if HttpRequest.has('_ssr_mode'):
            return None

        # FAST PATH: Check dedicated SPA header (10x faster than HttpRequest.is_ajax())
        spa_mode = HttpRequest.has_spa_header()

        if HttpRequest.has_spa_header():
            # SPA navigation - let route handler return partial HTML
            return None

        # No SPA header = direct browser visit (first load)
        # OPTIMIZATION: Server-side render initial content (eliminates double-fetch)
        #   return await self._render_initial_page_ssr(request)
        return view(context={})

    async def _render_initial_page_ssr(self, request: Request):
        """
        Server-Side Render initial page with content (OPTIMIZATION)
        """
        # Mark request as SSR mode BEFORE calling handler to prevent infinite recursion
        HttpRequest.set('_ssr_mode', True)

        handler = HttpRequest.get('route').get_action() or None
      
        if handler and callable(handler):
            try:
                # Execute the route handler to get the view
                result = await handler(request)

                # If result is ViewResponseBuilder, render it as partial
                from larasanic.support.facades.http_response import ViewResponseBuilder
                if isinstance(result, ViewResponseBuilder):
                    # Build to get HTML (will render as partial based on SPA header)
                    partial_response = await result.build()
                    html_content = partial_response.body.decode('utf-8')

                    # Wrap in SPA base layout with pre-rendered content
                    return view(
                        context={Config.get('template.BLADE_VIEW_CONFIG.spa_content_variable'): html_content}
                    )
                else:
                    # Handler returned something else (redirect, HTTPResponse, etc)
                    # Let it pass through
                    return result

            except Exception as e:
                # If SSR fails, fall back to empty shell (graceful degradation)
                import traceback
                traceback.print_exc()

        # Fallback: Return empty SPA base (old behavior)
        return view(context={})