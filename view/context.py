"""
View Context Builder
Handles template context construction with auth, flash, errors, CSRF
"""
import json
from typing import Optional, Dict, Any
from larasanic.support import Config
from larasanic.support.facades import HttpRequest

async def build_context(request=None,context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build complete template context

    Args:
        request: Sanic request object
        context: User-provided context
    Returns:
        Complete context dictionary
    """
    config = Config.as_object('template.BLADE_VIEW_CONFIG')
    template_context = {}

    # User context
    template_context.update(context or {})
    template_context[config.spa_initial_path] = HttpRequest.path_with_query()

    # CSRF token
    if HttpRequest.has('csrf_token'):
        template_context['csrf_token'] = HttpRequest.get('csrf_token')

    # Flash messages,Validation errors & old input
    try:
        session = HttpRequest.get_session()
        if session:
            if 'flash' in session:
                template_context['flash'] = session.get('flash')
                session.pop('flash', None)
            if 'errors' in session:
                template_context['errors'] = session.get('errors')
                session.pop('errors', None)
            if 'old' in session:
                template_context['old'] = session.get('old')
                session.pop('old', None)
    except Exception:
        pass

    return template_context