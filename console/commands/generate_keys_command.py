"""
Generate JWT Keys Command
Creates RSA key pair for JWT authentication
"""
from larasanic.console.command import Command


class GenerateKeysCommand(Command):
    """Generate RSA key pair for JWT authentication"""

    name = "key:generate"
    description = "Generate RSA key pair for JWT authentication"
    signature = "key:generate"

    async def handle(self, **kwargs):
        """Generate JWT keys"""
        try:
            from larasanic.support import Storage, Crypto
            from larasanic.support.env_helper import EnvHelper

            self.info("Generating JWT keys...")

            # Get or generate JWT_KEY_NAME
            key_name = EnvHelper.get('JWT_KEY_NAME')

            if not key_name:
                # Generate random key name
                random_suffix = Crypto.generate_secret(8)  # 16 characters
                key_name = f"jwt_{random_suffix}"

                # Save to .env file
                EnvHelper.set('JWT_KEY_NAME', key_name)
                self.line(f"  Generated JWT_KEY_NAME: {key_name}")
                self.line(f"  Saved to .env file")

            public_key_path,private_key_path = Storage.get_jwt_paths()

            # Check if keys already exist
            if Storage.exists(private_key_path) or Storage.exists(public_key_path):
                self.error("JWT keys already exist:")
                if Storage.exists(private_key_path):
                    self.line(f"  Private key: {private_key_path}")
                if Storage.exists(public_key_path):
                    self.line(f"  Public key: {public_key_path}")

                if not self.confirm("Do you want to delete and recreate them?", default=False):
                    self.info("Key generation cancelled.")
                    return 0

                # Delete existing keys
                if Storage.exists(private_key_path):
                    Storage.unlink(private_key_path)
                    self.line(f"  Deleted: {private_key_path}")
                if Storage.exists(public_key_path):
                    Storage.unlink(public_key_path)
                    self.line(f"  Deleted: {public_key_path}")

            # Generate RSA key pair using Crypto helper
            private_pem, public_pem = Crypto.generate_rsa_keypair(key_size=2048)

            # Save keys using Crypto helper
            Crypto.save_rsa_keypair(private_pem, public_pem, private_key_path, public_key_path)

            self.success("JWT keys generated successfully!")
            self.line(f"  Private key: {private_key_path}")
            self.line(f"  Public key: {public_key_path}")

            return 0

        except Exception as e:
            self.error(f"Failed to generate keys: {e}")
            return 1
