"""
View Engine
Smart, unified rendering engine with automatic detection
"""
import json
from typing import Optional, Dict, Any, TYPE_CHECKING
from blade.exceptions import TemplateNotFoundException
from larasanic.support import Config
from larasanic.view.context import build_context
from larasanic.support.facades import TemplateBlade, App
from larasanic.support.facades import HttpRequest


class ViewEngine:
    """
    Unified view rendering engine
    """
    def __init__(
        self,
        template: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize view engine with template and context
       """
        # Store template and context
        self.template = template
        self.context = context or {}
        self.config = Config.as_object('template.BLADE_VIEW_CONFIG')

    async def render(self) -> str:
        """
        Render the view template to HTML string
        """
        if not App.has('template_blade'):
            raise RuntimeError(
                "Blade engine not initialized. "
            )
        blade_template_engine = TemplateBlade

        spa_mode = HttpRequest.has_spa_header()

        if self.template is None and spa_mode:
            # Return JSON immediately without template rendering
            return json.dumps(self.context or {})

        # Build context (only when needed for template rendering)
        template_context = await build_context(context=self.context)

        try:
            # Add to layout context
            layout_context = template_context.copy()

            # Run Blade rendering in thread pool to avoid blocking event loop
            import asyncio

            if self.template is None and not spa_mode:
                # Render SPA base layout
                content = await asyncio.to_thread(
                    blade_template_engine.render,
                    self.config.spa_layout,
                    layout_context
                )
                return content
            else:  # 'direct'
                # Render template directly (no layout)
                content = await asyncio.to_thread(
                    blade_template_engine.render,
                    self.template,
                    template_context
                )
                return {'html': content} if spa_mode else content

        except TemplateNotFoundException as e:
            print(f"Template not found: {e}")
            return f"<div>Template not found: {self.template}</div>"

        except Exception as e:
            print(f"Render error: {e}")
            import traceback
            traceback.print_exc()
            return f"<div>Error rendering template: {self.template}<br>Error: {str(e)}</div>"