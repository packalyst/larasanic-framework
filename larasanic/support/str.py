"""
String Helper Functions
Laravel-style string manipulation utilities
"""
import re
from typing import Optional


class Str:
    """
    String manipulation helper class (Laravel-style)

    Provides static methods for common string operations:
    - snake_case conversion
    - camelCase conversion
    - StudlyCase conversion
    - slug generation
    - string manipulation utilities
    """

    @staticmethod
    def snake(value: str, delimiter: str = '_') -> str:
        """
        Convert a string to snake_case

        Args:
            value: String to convert
            delimiter: Delimiter to use (default: '_')

        Returns:
            Snake cased string

        Example:
            Str.snake('FrameworkApp')  # 'framework_app'
            Str.snake('Framework App')  # 'framework_app'
            Str.snake('frameworkApp')  # 'framework_app'
        """
        if not value:
            return value

        # Replace spaces with delimiter
        value = value.replace(' ', delimiter)

        # Insert delimiter before uppercase letters
        value = re.sub('(.)([A-Z][a-z]+)', r'\1' + delimiter + r'\2', value)
        value = re.sub('([a-z0-9])([A-Z])', r'\1' + delimiter + r'\2', value)

        # Lowercase and remove duplicate delimiters
        value = value.lower()
        value = re.sub(f'{delimiter}+', delimiter, value)

        return value.strip(delimiter)

    @staticmethod
    def camel(value: str) -> str:
        """
        Convert a string to camelCase

        Args:
            value: String to convert

        Returns:
            Camel cased string

        Example:
            Str.camel('framework_app')  # 'frameworkApp'
            Str.camel('Framework App')  # 'frameworkApp'
        """
        if not value:
            return value

        # Convert to studly case first
        studly = Str.studly(value)

        # Lowercase first character
        return studly[0].lower() + studly[1:] if studly else ''

    @staticmethod
    def studly(value: str) -> str:
        """
        Convert a string to StudlyCase (PascalCase)

        Args:
            value: String to convert

        Returns:
            Studly cased string

        Example:
            Str.studly('framework_app')  # 'FrameworkApp'
            Str.studly('framework app')  # 'FrameworkApp'
        """
        if not value:
            return value

        # Replace underscores and hyphens with spaces
        value = value.replace('_', ' ').replace('-', ' ')

        # Capitalize each word and remove spaces
        return ''.join(word.capitalize() for word in value.split())

    @staticmethod
    def slug(value: str, separator: str = '-') -> str:
        """
        Generate a URL-friendly slug from a string

        Args:
            value: String to convert
            separator: Separator to use (default: '-')

        Returns:
            URL-friendly slug

        Example:
            Str.slug('Framework App!')  # 'framework-app'
            Str.slug('Hello World', '_')  # 'hello_world'
        """
        if not value:
            return value

        # Convert to lowercase
        value = value.lower()

        # Remove special characters except alphanumeric and spaces
        value = re.sub(r'[^a-z0-9\s-]', '', value)

        # Replace spaces and multiple hyphens with separator
        value = re.sub(r'[\s-]+', separator, value)

        return value.strip(separator)

    @staticmethod
    def kebab(value: str) -> str:
        """
        Convert a string to kebab-case

        Args:
            value: String to convert

        Returns:
            Kebab cased string

        Example:
            Str.kebab('FrameworkApp')  # 'framework-app'
            Str.kebab('Framework App')  # 'framework-app'
        """
        return Str.snake(value, '-')

    @staticmethod
    def title(value: str) -> str:
        """
        Convert a string to Title Case

        Args:
            value: String to convert

        Returns:
            Title cased string

        Example:
            Str.title('framework_app')  # 'Framework App'
            Str.title('hello-world')  # 'Hello World'
        """
        if not value:
            return value

        # Replace underscores and hyphens with spaces
        value = value.replace('_', ' ').replace('-', ' ')

        # Title case
        return value.title()

    @staticmethod
    def lower(value: str) -> str:
        """Convert string to lowercase"""
        return value.lower() if value else value

    @staticmethod
    def upper(value: str) -> str:
        """Convert string to uppercase"""
        return value.upper() if value else value

    @staticmethod
    def length(value: str) -> int:
        """Get string length"""
        return len(value) if value else 0

    @staticmethod
    def limit(value: str, limit: int = 100, end: str = '...') -> str:
        """
        Limit the number of characters in a string

        Args:
            value: String to limit
            limit: Maximum length
            end: String to append if limited (default: '...')

        Returns:
            Limited string

        Example:
            Str.limit('Hello World', 5)  # 'Hello...'
        """
        if not value or len(value) <= limit:
            return value

        return value[:limit].rstrip() + end

    @staticmethod
    def contains(haystack: str, needle: str | list) -> bool:
        """
        Check if a string contains a substring or any of the substrings

        Args:
            haystack: String to search in
            needle: String or list of strings to search for

        Returns:
            True if found, False otherwise

        Example:
            Str.contains('Hello World', 'World')  # True
            Str.contains('Hello', ['Hi', 'Hello'])  # True
        """
        if not haystack:
            return False

        if isinstance(needle, list):
            return any(n in haystack for n in needle)

        return needle in haystack

    @staticmethod
    def starts_with(haystack: str, needle: str | list) -> bool:
        """
        Check if a string starts with a substring

        Args:
            haystack: String to check
            needle: String or list of strings to check

        Returns:
            True if starts with needle

        Example:
            Str.starts_with('Framework', 'Frame')  # True
        """
        if not haystack:
            return False

        if isinstance(needle, list):
            return any(haystack.startswith(n) for n in needle)

        return haystack.startswith(needle)

    @staticmethod
    def ends_with(haystack: str, needle: str | list) -> bool:
        """
        Check if a string ends with a substring

        Args:
            haystack: String to check
            needle: String or list of strings to check

        Returns:
            True if ends with needle

        Example:
            Str.ends_with('Framework', 'work')  # True
        """
        if not haystack:
            return False

        if isinstance(needle, list):
            return any(haystack.endswith(n) for n in needle)

        return haystack.endswith(needle)

    @staticmethod
    def replace(search: str, replace: str, subject: str) -> str:
        """
        Replace all occurrences of a string

        Args:
            search: String to search for
            replace: String to replace with
            subject: String to search in

        Returns:
            String with replacements

        Example:
            Str.replace('world', 'Python', 'Hello world')  # 'Hello Python'
        """
        if not subject:
            return subject

        return subject.replace(search, replace)

    @staticmethod
    def random(length: int = 16) -> str:
        """
        Generate a random alphanumeric string

        Args:
            length: Length of random string

        Returns:
            Random string

        Example:
            Str.random(10)  # 'aB3xK9mP2q'
        """
        import string
        import secrets

        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
