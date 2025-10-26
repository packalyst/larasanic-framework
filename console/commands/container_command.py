"""
Container Commands
Commands for inspecting the service container
"""
from larasanic.console.command import Command


class ContainerCommand(Command):
    """Container inspection commands"""

    name = "container"
    description = "Container inspection operations"

    # List of subcommands for artisan display
    signature = [
        {"command": "container:list", "description": "List all registered container bindings"},
        {"command": "container:check", "args": "{binding}", "description": "Check if a specific binding exists"},
    ]

    async def handle(self, action: str = None, binding: str = None, **kwargs):
        """Handle container commands - routes to appropriate handler"""

        # Route to appropriate handler based on action
        if action == 'list':
            return await self.handle_list()
        elif action == 'check':
            return await self.handle_check(binding=binding)
        else:
            self.error(f"Unknown action: {action}")
            return 1

    async def handle_list(self, **kwargs):
        """List all container bindings"""
        from bootstrap.app import create_app

        self.info("🔍 Loading application and container bindings...")
        self.line()

        # Create app to load all service providers
        app = create_app()

        # Get all bindings
        bindings = app.get_bindings()

        if not bindings:
            self.error("❌ No bindings registered in container")
            return 1

        # Separate by type
        singletons = {}
        factories = {}
        legacy = {}

        for key, info in bindings.items():
            if info['type'] == 'singleton':
                singletons[key] = info
            elif info['type'] == 'factory':
                factories[key] = info
            else:
                legacy[key] = info

        total = len(bindings)
        self.success(f"✅ Found {total} bindings ({len(singletons)} singletons, {len(factories)} factories)")
        self.line()

        # Print Singletons
        if singletons:
            self.line("Singletons:")
            self.line("━" * 80)

            # Calculate max key length
            max_key_len = max(len(key) for key in singletons.keys())
            max_key_len = min(max_key_len, 40)

            for key in sorted(singletons.keys()):
                info = singletons[key]
                status = '✓ instantiated' if info['instantiated'] else '○ lazy'

                # Truncate key if needed
                display_key = key if len(key) <= max_key_len else key[:max_key_len-3] + '...'

                # Format the entire line at once
                self.line(f"  {display_key:<{max_key_len}}  {status}")

            self.line()

        # Print Factories
        if factories:
            self.line("Factories (bind):")
            self.line("━" * 80)

            for key in sorted(factories.keys()):
                self.line(f"  {key:<40}  [new instance each call]")

            self.line()

        # Print Legacy
        if legacy:
            self.line("Legacy format:")
            self.line("━" * 80)

            for key in sorted(legacy.keys()):
                self.line(f"  {key:<40}  [legacy format]")

            self.line()

        # Summary
        self.line("━" * 80)
        self.info(f"Total: {total} bindings")

        if singletons:
            instantiated_count = sum(1 for info in singletons.values() if info['instantiated'])
            lazy_count = len(singletons) - instantiated_count
            self.line(f"  • Singletons: {len(singletons)} ({instantiated_count} instantiated, {lazy_count} lazy)")

        if factories:
            self.line(f"  • Factories: {len(factories)}")

        if legacy:
            self.line(f"  • Legacy: {len(legacy)}")

        return 0

    async def handle_check(self, binding: str = None, **kwargs):
        """Check if binding exists"""
        from bootstrap.app import create_app

        if not binding:
            self.error("❌ Please provide a binding name")
            self.line()
            self.line("Usage: artisan container:check {binding_name}")
            return 1

        self.info(f"🔍 Checking for binding: {binding}")
        self.line()

        # Create app
        app = create_app()

        # Check if exists
        if not app.has(binding):
            self.error(f"❌ Binding '{binding}' not found in container")
            return 1

        # Get binding info
        bindings = app.get_bindings()
        info = bindings[binding]

        self.success(f"✅ Binding '{binding}' exists")
        self.line()

        # Display details
        self.line("Details:")
        self.line("━" * 80)
        self.line(f"  Type: {info['type']}")

        if info['type'] == 'singleton':
            status = 'instantiated' if info['instantiated'] else 'lazy (not yet created)'
            self.line(f"  Status: {status}")
        elif info['type'] == 'factory':
            self.line(f"  Behavior: Creates new instance on each make() call")

        return 0
