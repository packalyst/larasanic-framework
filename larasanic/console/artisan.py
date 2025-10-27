import os

# Import framework support classes
from larasanic.support import Storage, EnvHelper

from larasanic.console.command import Command
import importlib.util
import inspect

class Artisan:
    # Paths to scan for commands
    COMMAND_PATHS = [
        Storage.framework('console', 'commands'),  # Framework built-in commands
        Storage.app('console'),  # User's application commands
    ]

    # Cache key for artisan commands
    CACHE_KEY = 'artisan_commands'

    def __init__(self, use_cache=False):
        self.commands = {}
        self.command_files = {}  # Map command names to file paths
        self.use_cache = use_cache  # Disabled for CLI (requires async)
        self._discover_commands()

    def _discover_commands(self):
        """Auto-discover commands"""
        # Note: Caching removed for CLI simplicity
        # Web requests use Cache facade (async)
        command_data = []

        for command_path in self.COMMAND_PATHS:
            if not command_path.exists():
                continue

            # Scan directory for .py files
            for py_file in command_path.glob('*.py'):
                # Skip __init__.py
                if py_file.name.startswith('__'):
                    continue

                # Store file info for caching
                command_data.append({
                    'file': str(py_file),
                    'mtime': py_file.stat().st_mtime
                })

                # Load the module dynamically
                try:
                    module_name = py_file.stem
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Find all Command subclasses in the module
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(obj, Command) and
                                obj is not Command and
                                hasattr(obj, 'name') and
                                obj.name):

                                # Instantiate and register
                                command_instance = obj()

                                # Check if signature is a list (multi-command)
                                if isinstance(command_instance.signature, list):
                                    # Register each subcommand separately
                                    for sig in command_instance.signature:
                                        cmd_name = sig['command']
                                        # Extract action from command name (db:init -> init)
                                        action = cmd_name.split(':')[-1] if ':' in cmd_name else cmd_name
                                        # Create a wrapper that passes the action
                                        self.commands[cmd_name] = command_instance
                                        self.command_files[cmd_name] = str(py_file)
                                else:
                                    # Regular single command
                                    self.commands[command_instance.name] = command_instance
                                    self.command_files[command_instance.name] = str(py_file)

                except Exception as e:
                    # Silently skip files that can't be loaded
                    pass


    def show_help(self):
        """Show available commands"""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║  Artisan - Laravel-style CLI                             ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()

        if not self.commands:
            print("No commands available.")
            return

        # Group commands by category
        categories = {}
        displayed_instances = set()  # Track displayed command instances by id

        for name, cmd in self.commands.items():
            # Extract category from command name (e.g., "db:init" -> "db")
            if ':' in name:
                category = name.split(':')[0]
            else:
                category = 'general'

            if category not in categories:
                categories[category] = []

            # For multi-commands, only add once (avoid duplicates)
            if isinstance(cmd.signature, list):
                cmd_id = id(cmd)
                if cmd_id not in displayed_instances:
                    displayed_instances.add(cmd_id)
                    categories[category].append((name, cmd))
            else:
                categories[category].append((name, cmd))

        # Display commands grouped by category
        for category in sorted(categories.keys()):
            print(f"{category.upper()}:")
            for name, cmd in sorted(categories[category]):
                # Check if signature is a list (multi-command)
                if isinstance(cmd.signature, list):
                    # Display all subcommands from the list
                    for sig in cmd.signature:
                        cmd_name = sig['command']
                        args = sig.get('args', '')
                        desc = sig['description']
                        print(f"  {cmd_name} {args:<27} {desc}")
                else:
                    # Display as normal (single command)
                    print(f"  {cmd.signature:<35} {cmd.description}")
            print()

        print("Run 'artisan help <command>' for detailed information")

    async def run(self, argv):
        """Run the CLI application"""
        if len(argv) < 2:
            self.show_help()
            return 0

        command_name = argv[1]

        if command_name in ['help', '--help', '-h']:
            if len(argv) > 2:
                # Help for specific command
                cmd_name = argv[2]
                if cmd_name in self.commands:
                    cmd = self.commands[cmd_name]
                    print(f"\nCommand: {cmd.name}")
                    print(f"Description: {cmd.description}")
                    print(f"Signature: {cmd.signature}")
                    return 0
                else:
                    print(f"Unknown command: {cmd_name}\n")
                    self.show_help()
                    return 1
            else:
                self.show_help()
                return 0

        if command_name not in self.commands:
            print(f"❌ Unknown command: {command_name}\n")
            self.show_help()
            return 1

        # Get command instance
        command = self.commands[command_name]

        # Parse arguments
        args, kwargs = self._parse_args(argv[2:])

        try:
            # Initialize command resources
            if hasattr(command, '_handleInit') and callable(command._handleInit):
                await command._handleInit()

            # Check if this is a multi-command (has list signature)
            if isinstance(command.signature, list):
                # Extract action from command name (db:init -> init)
                action = command_name.split(':')[-1] if ':' in command_name else command_name
                # Pass action as first argument
                exit_code = await command.handle(action, *args, **kwargs)
            else:
                # Regular single command
                exit_code = await command.handle(*args, **kwargs)

            # Call cleanup hook if command has a close() method
            if hasattr(command, '_handleClose') and callable(command._handleClose):
                try:
                    if inspect.iscoroutinefunction(command._handleClose):
                        await command._handleClose()
                    else:
                        command._handleClose()
                except Exception as cleanup_error:
                    print(f"⚠️  Warning: Cleanup failed: {cleanup_error}")

            return exit_code if exit_code is not None else 0

        except KeyboardInterrupt:
            print("\n\n⚠ Command interrupted by user")
            # Try cleanup even on interrupt
            if hasattr(command, '_handleClose') and callable(command._handleClose):
                try:
                    if inspect.iscoroutinefunction(command._handleClose):
                        await command._handleClose()
                    else:
                        command._handleClose()
                except:
                    pass
            return 130
        except Exception as e:
            print(f"\n❌ Error executing command: {e}\n")
            import traceback
            traceback.print_exc()
            # Try cleanup even on error
            if hasattr(command, 'close') and callable(command.close):
                try:
                    if inspect.iscoroutinefunction(command.close):
                        await command.close()
                    else:
                        command.close()
                except:
                    pass
            return 1

    def _parse_args(self, argv):
        """
        Parse command line arguments
        Returns tuple of (positional_args, keyword_args)
        """
        args = []
        kwargs = {}

        for arg in argv:
            if arg.startswith('--'):
                # Long option (--verbose, --name=value)
                if '=' in arg:
                    key, value = arg[2:].split('=', 1)
                    # Try to convert to int
                    try:
                        kwargs[key] = int(value)
                    except ValueError:
                        # Try to convert to bool
                        if value.lower() in ('true', 'false'):
                            kwargs[key] = value.lower() == 'true'
                        else:
                            kwargs[key] = value
                else:
                    # Boolean flag
                    kwargs[arg[2:]] = True
            elif arg.startswith('-'):
                # Short option
                kwargs[arg[1:]] = True
            else:
                # Positional argument
                args.append(arg)

        return args, kwargs