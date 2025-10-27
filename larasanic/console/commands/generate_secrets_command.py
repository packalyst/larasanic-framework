"""
Generate Secrets Command
Generates random secrets for CSRF and session
"""
from larasanic.console.command import Command
from larasanic.support import Crypto
from larasanic.support.env_helper import EnvHelper

class GenerateSecretsCommand(Command):
    """Generate random secrets for application"""

    name = "secret:generate"
    description = "Generate random secrets for CSRF and session"
    signature = "secret:generate"

    async def handle(self, **kwargs):
        """Generate secrets"""
        from larasanic.defaults import DEFAULT_CSRF_TOKEN_LENGTH
        random_suffix = Crypto.generate_secret(8)  # 16 characters
        csrf = Crypto.generate_token(DEFAULT_CSRF_TOKEN_LENGTH)
        secret = Crypto.generate_token(DEFAULT_CSRF_TOKEN_LENGTH)

        # Save to .env file
        EnvHelper.set('CSRF_SECRET', csrf)

        self.info("Generating secrets...")
        self.line()
        self.line("Add these to your .env file:")
        self.line()
        self.line(f"CSRF_SECRET={csrf}")
        self.line()

        return 0
