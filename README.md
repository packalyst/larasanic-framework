# Larasanic Framework

A Laravel-inspired async web framework built on Sanic for Python.

## Features

- **Laravel-Like Architecture**: Service providers, facades, middleware, routing
- **Async-First**: Built on Sanic for high-performance async
- **Tortoise ORM**: Async ORM with Aerich migrations
- **Built-in Auth**: JWT-based authentication
- **Session Management**: File, cookie, and Redis drivers
- **Caching**: File and Redis backends
- **WebSocket Support**: Real-time communication
- **Blade-Inspired Templates**: Laravel-style template engine
- **Security**: CSRF, CORS, headers, rate limiting
- **HTTP Client**: Secure async and sync clients
- **CLI Console**: Artisan-style commands

## Installation

```bash
pip install larasanic
```

## Quick Start

```python
from larasanic import Application

app = Application(base_path='/path/to/project')
app.register_provider(DatabaseServiceProvider)
app.boot()
app.run()
```

## Requirements

- Python 3.8+
- Sanic 23.0+
- Tortoise ORM 0.19+

## License

MIT License
