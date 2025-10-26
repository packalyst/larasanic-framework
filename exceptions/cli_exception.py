import os
import sys
from larasanic.exceptions.cli_formatter import CliColors, CliBox, _colorize, _box_line, _format_traceback

def handle_cli_exceptions(error: Exception):
    """
    Handle errors during app startup with beautiful formatting
    Shows specific help messages based on error type
    """
    is_dev = os.getenv('APP_ENV', 'local') in ['local', 'development']
    width = 70

    # Header
    print("\n" + _colorize(CliBox.TL + CliBox.H * (width - 2) + CliBox.TR, CliColors.RED))
    title = _colorize("⚠️  APPLICATION STARTUP FAILED", CliColors.BOLD + CliColors.RED)
    print(_box_line(title, width))
    print(_colorize(CliBox.BL + CliBox.H * (width - 2) + CliBox.BR, CliColors.RED))

    # Error-specific messages
    print("\n" + _colorize(CliBox.TL + CliBox.H * (width - 2) + CliBox.TR, CliColors.YELLOW))

    if isinstance(error, ValueError) and "JWT_KEY_NAME" in str(error):
        print(_box_line(_colorize("❌ Missing Security Keys", CliColors.BOLD + CliColors.YELLOW), width))
        print(_colorize(CliBox.L + CliBox.H * (width - 2) + CliBox.R, CliColors.YELLOW))
        print(_box_line("", width))
        print(_box_line(_colorize("Please generate security keys first:", CliColors.WHITE), width))
        print(_box_line("", width))
        print(_box_line(_colorize("  python app/artisan.py generate-keys", CliColors.GREEN), width))
        print(_box_line("", width))

    elif isinstance(error, ValueError) and "CSRF_SECRET" in str(error):
        print(_box_line(_colorize("❌ Missing CSRF Secret", CliColors.BOLD + CliColors.YELLOW), width))
        print(_colorize(CliBox.L + CliBox.H * (width - 2) + CliBox.R, CliColors.YELLOW))
        print(_box_line("", width))
        print(_box_line(_colorize("Please run setup:", CliColors.WHITE), width))
        print(_box_line("", width))
        print(_box_line(_colorize("  python app/artisan.py setup", CliColors.GREEN), width))
        print(_box_line("", width))

    elif isinstance(error, FileNotFoundError):
        print(_box_line(_colorize(f"❌ File Not Found", CliColors.BOLD + CliColors.YELLOW), width))
        print(_colorize(CliBox.L + CliBox.H * (width - 2) + CliBox.R, CliColors.YELLOW))
        print(_box_line("", width))
        print(_box_line(_colorize(str(error), CliColors.WHITE), width))
        print(_box_line("", width))

    elif isinstance(error, ImportError):
        print(_box_line(_colorize(f"❌ Import Error", CliColors.BOLD + CliColors.YELLOW), width))
        print(_colorize(CliBox.L + CliBox.H * (width - 2) + CliBox.R, CliColors.YELLOW))
        print(_box_line("", width))
        print(_box_line(_colorize(str(error), CliColors.WHITE), width))
        print(_box_line("", width))
        print(_box_line(_colorize("Install dependencies:", CliColors.WHITE), width))
        print(_box_line("", width))
        print(_box_line(_colorize("  pip install -r requirements.txt", CliColors.GREEN), width))
        print(_box_line("", width))

    else:
        error_title = f"❌ {type(error).__name__}"
        print(_box_line(_colorize(error_title, CliColors.BOLD + CliColors.YELLOW), width))
        print(_colorize(CliBox.L + CliBox.H * (width - 2) + CliBox.R, CliColors.YELLOW))
        print(_box_line("", width))

        # Wrap long error messages
        error_msg = str(error)
        if len(error_msg) > 60:
            words = error_msg.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= 60:
                    current_line += word + " "
                else:
                    lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())

            for line in lines:
                print(_box_line(_colorize(line, CliColors.WHITE), width))
        else:
            print(_box_line(_colorize(error_msg, CliColors.WHITE), width))

        print(_box_line("", width))

    print(_colorize(CliBox.BL + CliBox.H * (width - 2) + CliBox.BR, CliColors.YELLOW))

    # Show traceback in dev mode
    if is_dev:
        print("\n" + _colorize(CliBox.TL + CliBox.H * (width - 2) + CliBox.TR, CliColors.BLUE))
        print(_box_line(_colorize("📋 FULL TRACEBACK (APP_ENV=local)", CliColors.BOLD + CliColors.BLUE), width))
        print(_colorize(CliBox.BL + CliBox.H * (width - 2) + CliBox.BR, CliColors.BLUE))
        print()
        for line in _format_traceback():
            print(line)
        print()
    else:
        print("\n" + _colorize(CliBox.TL + CliBox.H * (width - 2) + CliBox.TR, CliColors.CYAN))
        tip = _colorize("💡 Tip: Set APP_ENV=local for full traceback", CliColors.CYAN)
        print(_box_line(tip, width))
        print(_colorize(CliBox.BL + CliBox.H * (width - 2) + CliBox.BR, CliColors.CYAN))
    print()
    sys.exit(1)


def install_cli_error_handler():
    """
    Install beautiful exception handler for CLI (artisan commands)
    This overrides traceback printing to beautify all exceptions
    """
    import sys
    import traceback as tb_module

    # Store original functions
    original_print_exc = tb_module.print_exc
    original_excepthook = sys.excepthook

    def beautiful_print_exc(limit=None, file=None, chain=True):
        """Override traceback.print_exc to use beautiful formatting"""
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_value and exc_type is not KeyboardInterrupt:
            handle_cli_exceptions(exc_value)
        else:
            # Fallback to original for KeyboardInterrupt
            original_print_exc(limit=limit, file=file, chain=chain)

    def cli_exception_hook(exc_type, exc_value, exc_traceback):
        """Custom exception hook for beautiful CLI errors"""
        if issubclass(exc_type, KeyboardInterrupt):
            original_excepthook(exc_type, exc_value, exc_traceback)
            return
        handle_cli_exceptions(exc_value)

    # Override both traceback.print_exc and sys.excepthook
    tb_module.print_exc = beautiful_print_exc
    sys.excepthook = cli_exception_hook