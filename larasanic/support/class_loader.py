"""
Class Loader
Dynamic class loading utility for importing classes and functions from dotted paths
"""
from typing import Type, Callable, Union


class ClassLoader:
    """
    Utility for dynamically loading classes and functions from string paths

    Example:
        # Load a class
        cls = ClassLoader.load('larasanic.middleware.CorsMiddleware')

        # Load a function
        func = ClassLoader.load_callable('routes.laravel.home_handler')

        # Create instance
        instance = cls()
    """

    @staticmethod
    def load(class_path: str) -> Type:
        """
        Load a class from a dotted path string

        Args:
            class_path: Full dotted path to class (e.g., 'larasanic.middleware.CorsMiddleware')

        Returns:
            The class object (not instantiated)

        Raises:
            ImportError: If module cannot be imported
            AttributeError: If class doesn't exist in module

        Example:
            >>> cls = ClassLoader.load('larasanic.middleware.CorsMiddleware')
            >>> instance = cls()
        """
        # Split module path and class name
        module_path, class_name = class_path.rsplit('.', 1)

        # Import the module
        module = __import__(module_path, fromlist=[class_name])

        # Get the class from module
        return getattr(module, class_name)

    @staticmethod
    def load_callable(callable_path: str) -> Union[Callable, Type]:
        """
        Load a callable (function or class) from a dotted path string

        Args:
            callable_path: Full dotted path to callable (e.g., 'routes.laravel.home_handler')

        Returns:
            The callable object (function or class)

        Raises:
            ImportError: If module cannot be imported
            AttributeError: If callable doesn't exist in module

        Example:
            >>> func = ClassLoader.load_callable('routes.laravel.home_handler')
            >>> result = func(request)
        """
        # Split module path and callable name
        module_path, callable_name = callable_path.rsplit('.', 1)

        # Import the module
        module = __import__(module_path, fromlist=[callable_name])

        # Get the callable from module
        return getattr(module, callable_name)
