"""
CLI Formatter
Beautiful terminal formatting utilities with colors, boxes, and layouts

Provides ANSI colors, box-drawing characters, and formatting helpers
for creating beautiful CLI output.
"""
import os
import sys
import traceback
from typing import List

# ============================================================================
# ANSI COLORS
# ============================================================================

class CliColors:
    """ANSI color codes for terminal output"""
    # Reset
    RESET = '\033[0m'

    # Text styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

    # Standard colors
    BLACK = '\033[90m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


class CliBox:
    """
    Unicode box-drawing characters

    Supports multiple box styles: rounded, single line, double line
    """
    # Rounded corners (default)
    H = '─'      # Horizontal
    V = '│'      # Vertical
    TL = '╭'     # Top-left
    TR = '╮'     # Top-right
    BL = '╰'     # Bottom-left
    BR = '╯'     # Bottom-right
    L = '├'      # Left junction
    R = '┤'      # Right junction
    T = '┬'      # Top junction
    B = '┴'      # Bottom junction
    X = '┼'      # Cross junction

    # Single line style
    class Single:
        H = '─'
        V = '│'
        TL = '┌'
        TR = '┐'
        BL = '└'
        BR = '┘'
        L = '├'
        R = '┤'
        T = '┬'
        B = '┴'
        X = '┼'

    # Double line style
    class Double:
        H = '═'
        V = '║'
        TL = '╔'
        TR = '╗'
        BL = '╚'
        BR = '╝'
        L = '╠'
        R = '╣'
        T = '╦'
        B = '╩'
        X = '╬'


def _is_color_supported() -> bool:
    """Check if terminal supports colors"""
    return (
        hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
        os.getenv('TERM') != 'dumb'
    )


def _colorize(text: str, color: str) -> str:
    """Apply color to text if supported"""
    if _is_color_supported():
        return f"{color}{text}{CliColors.RESET}"
    return text


def _box_line(text: str, width: int = 70) -> str:
    """Create a centered text line in a box"""
    padding = width - len(text) - 4
    left_pad = padding // 2
    right_pad = padding - left_pad
    return f"{CliBox.V} {' ' * left_pad}{text}{' ' * right_pad} {CliBox.V}"


def _format_traceback() -> List[str]:
    """Format traceback with syntax highlighting"""
    tb_lines = traceback.format_exc().split('\n')
    formatted = []

    for line in tb_lines:
        if not line.strip():
            continue

        # File paths in cyan
        if 'File "' in line:
            formatted.append(_colorize(line, CliColors.CYAN))
        # Error type in bold red
        elif line.startswith(('ValueError', 'ImportError', 'FileNotFoundError',
                             'AttributeError', 'TypeError', 'KeyError')):
            parts = line.split(':', 1)
            if len(parts) == 2:
                error_type = _colorize(parts[0], CliColors.BOLD + CliColors.RED)
                message = _colorize(parts[1], CliColors.RED)
                formatted.append(f"{error_type}:{message}")
            else:
                formatted.append(_colorize(line, CliColors.RED))
        # Line numbers in yellow
        elif line.strip().startswith('line '):
            formatted.append(_colorize(f"  {line}", CliColors.YELLOW))
        # Code snippets in white
        else:
            formatted.append(_colorize(f"  {line}", CliColors.WHITE))

    return formatted