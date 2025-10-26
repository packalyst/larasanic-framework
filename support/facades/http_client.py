"""
Http Facade
Laravel-style facade for HTTP client operations
"""
from larasanic.support.facades.facade import Facade


class HttpClient(Facade):
    """
    Http Facade

    Provides static-like access to the HTTP client

    Usage:
        # Async HTTP requests
        response = await Http.get('https://api.example.com/data')
        json_data = await Http.get_json('https://api.example.com/users')
        
        response = await Http.post('https://api.example.com/submit', json={'key': 'value'})
        result = await Http.post_json('https://api.example.com/create', {'name': 'Test'})

        # Download files
        file_path = await Http.download_file('https://example.com/file.zip', '/path/to/save.zip')

        # Access client session
        client = Http.get_facade_root()
        await client.start()  # Manually start session if needed
        response = await client.get('https://example.com')
        await client.close()

        # Context manager
        async with Http.get_facade_root() as client:
            response = await client.get('https://example.com')

    Features:
        - Secure by default (SSRF protection, SSL verification)
        - Rate limiting support
        - Automatic retries
        - Request history for debugging
        - Multiple security levels (STRICT, BALANCED, RELAXED)
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'http_client'