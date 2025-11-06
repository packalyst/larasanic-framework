"""
User Model
Base user model for authentication
"""
from tortoise import fields
from larasanic.database.model import Model


class User(Model):
    """Base user model with email/password authentication"""

    hidden = ['password_hash', 'remember_token', 'two_factor_secret', 'two_factor_recovery_codes']

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255, unique=True, index=True)
    email_verified_at = fields.DatetimeField(null=True)
    password_hash = fields.CharField(max_length=255)
    remember_token = fields.CharField(max_length=100, null=True)
    profile_photo_path = fields.CharField(max_length=2048, null=True)
    two_factor_secret = fields.TextField(null=True)
    two_factor_recovery_codes = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"

    def __str__(self):
        return self.email

    @classmethod
    async def find_by_email(cls, email: str):
        """
        Find user by email

        Args:
            email: User email

        Returns:
            User instance or None
        """
        return await cls.filter(email=email).first()
