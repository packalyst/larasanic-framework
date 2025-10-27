"""
Blade Service Provider
"""
from larasanic.service_provider import ServiceProvider
from larasanic.support import Storage, EnvHelper, Config,BladeTemplateEngine
from larasanic.support.facades import App,TemplateBlade
from blade.utils.safe_string import SafeString
import re
from pathlib import Path

from typing import Callable
from larasanic.helpers import route as route_helper, url as url_helper, asset as asset_helper

class BladeServiceProvider(ServiceProvider):
    """Service provider for Blade template engine"""
    def register(self):
        """Register Blade engine in the container"""
        # Get paths from Storage
        views_dir = Storage.views()
        cache_dir = Storage.cache('blade')

        # Get configuration from config/template.py using Config utility
        blade_config = Config.get('template.BLADE_ENGINE_CONFIG', {}).copy()

        # Add paths to config
        blade_config['template_dir'] = views_dir
        blade_config['cache_dir'] = cache_dir

        # Initialize Blade engine with config
        blade_engine = BladeTemplateEngine(**blade_config)

        # Register in container using App facade
        App.singleton('template_blade', blade_engine)

    def boot(self):
        """Bootstrap Blade engine (add global variables, directives, etc.)"""
        # Register default directives (@icon, @route, @asset, @csrf_field, etc.)
        register_default_directives(TemplateBlade.engine)

        # Add framework helpers as globals
        from larasanic.helpers import auth as auth_helper
        TemplateBlade.add_globals({
            'app_name': EnvHelper.get('APP_NAME', 'Framework'),
            'app_env': EnvHelper.get('APP_ENV', 'production'),
            'icon': load_icon,
            'url': url_helper,
            'asset': asset_helper,
            'route': route_helper,
            'safe': safe_helper,
            'auth': auth_helper,
            # **global_helpers  # Merge helper functions
        })


# ============================================================================
# Core Helper Functions (used by both directives and globals)
# ============================================================================

def safe_helper(html: str) -> SafeString:
    return SafeString(html)

def load_icon(name, library='tabler', variant='outline', css_class='', width=20, height=20, **attrs):
    """
    Load SVG icon from node_modules package and return as inline HTML
    Args:
        name: Icon name (e.g., 'home', 'settings')
        library: Icon library ('tabler', 'heroicons', 'lucide', 'feather')
        variant: Icon variant ('outline', 'filled', 'solid') - depends on library support
        css_class: CSS classes to apply to the SVG
        width: Width of the icon (default: 20)
        height: Height of the icon (default: 20)
        **attrs: Additional HTML attributes for the SVG

    Returns:
        str: Inline SVG HTML or fallback icon if not found
    """
    # Get the library config
    lib_config = Config.get(f'template.BLADE_ICONS.packages.{library}', None)

    if not lib_config:
        svg_content = Config.get('template.BLADE_ICONS.fallback', None)
        return SafeString(f'<!-- Icon {library}:{name} not found -->\n{svg_content}')
    
    # Handle libraries with variants vs those without
    if isinstance(lib_config, dict):
        # Library supports variants
        if variant not in lib_config:
            # Try default variant if specified variant not found
            variant = 'outline' if 'outline' in lib_config else list(lib_config.keys())[0]
        base_path = lib_config[variant]
    else:
        # Library doesn't support variants
        base_path = lib_config
    
    # Build icon file path
    icon_path = Path(base_path) / f"{name}.svg"

    # Check if file exists
    if not icon_path.exists():
        svg_content = Config.get('template.BLADE_ICONS.fallback', None)
        svg_content = f'<!-- Icon {library}:{name} not found -->\n{svg_content}'
    else:
        # Read the SVG content
        with open(icon_path, 'r') as f:
            svg_content = f.read()
    
    # Add/update width and height on the SVG element only
    if re.search(r'<svg[^>]*\swidth=', svg_content):
        svg_content = re.sub(r'(<svg[^>]*\s)width="[^"]*"', f'\\1width="{width}"', svg_content, count=1)
    else:
        svg_content = svg_content.replace('<svg', f'<svg width="{width}"', 1)

    if re.search(r'<svg[^>]*\sheight=', svg_content):
        svg_content = re.sub(r'(<svg[^>]*\s)height="[^"]*"', f'\\1height="{height}"', svg_content, count=1)
    else:
        svg_content = svg_content.replace('<svg', f'<svg height="{height}"', 1)

    # Add/update classes
    if css_class:
        if 'class="' in svg_content:
            svg_content = svg_content.replace('class="', f'class="{css_class} ')
        elif 'class=' in svg_content:
            svg_content = svg_content.replace("class='", f"class='{css_class} ")
        else:
            svg_content = svg_content.replace('<svg', f'<svg class="{css_class}"', 1)

    # Add any extra attributes
    for key, value in attrs.items():
        # Convert underscore to hyphen for HTML attributes (e.g., aria_label -> aria-label)
        html_key = key.replace('_', '-')
        svg_content = svg_content.replace('<svg', f'<svg {html_key}="{value}"', 1)
    
    # Return as SafeString to prevent HTML escaping in templates
    return SafeString(svg_content)

# ============================================================================
# Directive Registration
# ============================================================================

def register_default_directives(engine):
    # Helper to create directive wrapper from function
    def make_directive(func: Callable, *expected_args):
        """Create a directive handler from a regular function"""
        def directive_handler(args, context):
            if not args and expected_args:
                return ''
            # Map args to function parameters
            return func(*args[:len(expected_args)] if expected_args else args)
        return directive_handler

    # @route - Generate route URL
    engine.register_directive('route', make_directive(route_helper, 'name', 'parameters'))

    # Note: @auth is available as a global function auth() in templates
    # No need for @auth directive since auth() helper provides facade access

    # @asset - Generate asset URL
    engine.register_directive('asset', make_directive(asset_helper, 'path'))
    
    # @csrf_field - Output CSRF token field
    def csrf_field_directive(args, context):
        csrf_token = context.get('csrf_token', '')
        if csrf_token:
            return f'<input type="hidden" name="_csrf_token" value="{csrf_token}">'
        return ''
    
    engine.register_directive('csrf_field', csrf_field_directive)
    
    # @old - Get old input value (for form repopulation)
    def old_directive(args, context):
        """
        @old('field_name', 'default')
        Example:
            <input name="email" value="@old('email')">
            <input name="name" value="@old('name', 'Default Name')">
        """
        if not args:
            return ''
        
        field = args[0]
        default = args[1] if len(args) > 1 else ''
        
        old_data = context.get('old', {})
        return old_data.get(field, default)
    
    engine.register_directive('old', old_directive)
    
    # @error_message - Display validation error for field
    def error_message_directive(args, context):
        """
        @error_message('field_name')
        Example:
            @error_message('email')
        """
        if not args:
            return ''
        
        field = args[0]
        errors = context.get('errors', {})
        
        if field in errors:
            error = errors[field]
            # Handle both string and list errors
            if isinstance(error, list):
                error = error[0] if error else ''
            return f'<span class="error-message">{error}</span>'
        
        return ''
    
    engine.register_directive('error_message', error_message_directive)
    
    # @has_error - Check if field has error (returns class name)
    def has_error_directive(args, context):
        """
        @has_error('field_name', 'error-class')
        Example:
            <input class="form-control @has_error('email', 'is-invalid')" name="email">
        """
        if not args:
            return ''
        field = args[0]
        error_class = args[1] if len(args) > 1 else 'error'
        
        errors = context.get('errors', {})
        return error_class if field in errors else ''
    
    engine.register_directive('has_error', has_error_directive)
    
    # @flash_message - Display flash message
    def flash_message_directive(args, context):
        """
        @flash_message - Display flash message if exists
        
        Example:
            @flash_message
        """
        flash = context.get('flash', {})
        if not flash:
            return ''
        
        message_type = flash.get('type', 'info')
        message = flash.get('message', '')
        
        if message:
            return f'<div class="alert alert-{message_type}">{message}</div>'
        return ''
    
    engine.register_directive('flash_message', flash_message_directive)
    
    # @dd - Dump and die (for debugging)
    def dd_directive(args, context):
        """
        @dd($variable) - Dump variable and stop
        
        Example:
            @dd(user)
        """
        if not args:
            return '<pre>No variable provided to @dd</pre>'
        
        import json
        try:
            dumped = json.dumps(args[0], indent=2, default=str)
            return f'<pre style="background:#f5f5f5;padding:1rem;border:1px solid #ddd;"><strong>DD:</strong>\n{dumped}</pre>'
        except Exception as e:
            return f'<pre>DD Error: {str(e)}\nValue: {repr(args[0])}</pre>'
    
    engine.register_directive('dd', dd_directive)
    
    # @dump - Dump variable (continue execution)
    def dump_directive(args, context):
        """
        @dump($variable) - Dump variable for debugging
        
        Example:
            @dump(user)
        """
        if not args:
            return '<pre>No variable provided to @dump</pre>'
        
        import json
        try:
            dumped = json.dumps(args[0], indent=2, default=str)
            return f'<pre style="background:#fff3cd;padding:0.5rem;border:1px solid #ffc107;font-size:0.875rem;">{dumped}</pre>'
        except Exception as e:
            return f'<pre>Dump Error: {str(e)}</pre>'
    
    engine.register_directive('dump', dump_directive)