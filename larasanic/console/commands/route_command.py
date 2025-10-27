"""
Route List Command
Display all registered routes in a table
"""
from larasanic.console.command import Command


class RouteListCommand(Command):
    """List all registered routes"""

    name = "route:list"
    description = "List all registered routes"

    async def handle(self, **kwargs):
        """List all routes"""
        from bootstrap.app import create_app
        from larasanic.support.facades import Route
        self.info("🔍 Loading application and routes...")
        self.line()

        # Create app to load routes
        app = create_app()

        # Get routes from Sanic router (actual registered routes with prefixes)
        app_routes = Route.routes.to_dict()

        if not app_routes:
            self.error("❌ No routes registered")
            return 1

        # Prepare table data
        table_data = []
        for routes in Route.routes.to_dict()['routes']:
            middleware = ', '.join(routes['middleware']) if routes['middleware'] else '-'
            table_data.append({
                'method': '|'.join(sorted(routes['methods'])),
                'uri': routes['uri'],
                'name': routes['name'],
                'action': routes['action'],
                'middleware': middleware
            })
        # Sort by URI
        table_data.sort(key=lambda x: x['uri'])

        # Calculate column widths
        max_method = max(len(r['method']) for r in table_data)
        max_uri = max(len(r['uri']) for r in table_data)
        max_name = max(len(r['name']) for r in table_data)
        max_action = max(len(r['action']) for r in table_data)
        max_middleware = max(len(r['middleware']) for r in table_data)

        # Ensure minimum widths
        max_method = max(max_method, len('Method'))
        max_uri = max(max_uri, len('URI'))
        max_name = max(max_name, len('Name'))
        max_action = max(max_action, len('Action'))
        max_middleware = max(max_middleware, len('Middleware'))

        # Limit max widths
        max_method = min(max_method, 20)
        max_uri = min(max_uri, 50)
        max_name = min(max_name, 30)
        max_action = min(max_action, 40)
        max_middleware = min(max_middleware, 30)

        # Print header
        separator = (
            '+-' + '-' * max_method +
            '-+-' + '-' * max_uri +
            '-+-' + '-' * max_name +
            '-+-' + '-' * max_action +
            '-+-' + '-' * max_middleware +
            '-+'
        )

        self.line(separator)
        self.line(
            f"| {'Method'.ljust(max_method)} "
            f"| {'URI'.ljust(max_uri)} "
            f"| {'Name'.ljust(max_name)} "
            f"| {'Action'.ljust(max_action)} "
            f"| {'Middleware'.ljust(max_middleware)} |"
        )
        self.line(separator)

        # Print rows
        for row in table_data:
            method = self._truncate(row['method'], max_method)
            uri = self._truncate(row['uri'], max_uri)
            name = self._truncate(row['name'], max_name)
            action = self._truncate(row['action'], max_action)
            middleware = self._truncate(row['middleware'], max_middleware)

            self.line(
                f"| {method.ljust(max_method)} "
                f"| {uri.ljust(max_uri)} "
                f"| {name.ljust(max_name)} "
                f"| {action.ljust(max_action)} "
                f"| {middleware.ljust(max_middleware)} |"
            )

        self.line(separator)
        self.line()
        self.success(f"Showing {app_routes['total']} routes")
        return 0

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max length with ellipsis"""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + '...'
