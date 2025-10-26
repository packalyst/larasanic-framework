"""
Base Command Class
Laravel-style command base class for Artisan CLI
"""
from abc import ABC, abstractmethod
from typing import Optional


class Command(ABC):

    # Command name (e.g., "make:migration", "db:seed")
    name: str = ""

    # Command description
    description: str = ""

    # Command signature (for help display)
    signature: Optional[str] = None

    def __init__(self):
        if not self.signature:
            self.signature = self.name
        self.db_manager = None  # Will be injected by Artisan

    

    @abstractmethod
    async def handle(self, *args, **kwargs):
        """
        Execute the command logic

        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        pass

    # Output helpers
    def info(self, message: str):
        """Print info message"""
        print(f"ℹ {message}")

    def success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")

    def error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")

    def warning(self, message: str):
        """Print warning message"""
        print(f"⚠ {message}")

    def line(self, message: str = ""):
        """Print plain line"""
        print(message)

    def ask(self, question: str, default: str = "") -> str:
        """Ask for user input"""
        if default:
            prompt = f"{question} [{default}]: "
        else:
            prompt = f"{question}: "

        response = input(prompt).strip()
        return response if response else default

    def confirm(self, question: str, default: bool = False) -> bool:
        """Ask for yes/no confirmation"""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{question} [{default_str}]: ").strip().lower()

        if not response:
            return default

        return response in ['y', 'yes']

    def choice(self, question: str, choices: list, default: str = None) -> str:
        """Ask user to choose from options"""
        self.line(question)
        for i, choice in enumerate(choices, 1):
            marker = " (default)" if choice == default else ""
            self.line(f"  [{i}] {choice}{marker}")

        while True:
            response = input("Select option: ").strip()

            if not response and default:
                return default

            try:
                idx = int(response) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
            except ValueError:
                pass

            self.error("Invalid choice. Please try again.")

    def table(self, headers: list, rows: list):
        """Print a simple table"""
        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))

        # Print header
        header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        self.line(header_line)
        self.line("-" * len(header_line))

        # Print rows
        for row in rows:
            row_line = " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
            self.line(row_line)
