"""
User Model
Base user model for authentication
"""
from tortoise import fields
from larasanic.database.model import Model


class User(Model):
    """Base user model with email/password authentication"""

    hidden = ['password_hash','created_at']

    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, unique=True, index=True)
    password_hash = fields.CharField(max_length=255)
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
