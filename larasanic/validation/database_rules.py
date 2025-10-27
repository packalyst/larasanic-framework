"""
Database Validation Rules
Rules that interact with the database (unique, exists)
"""
from typing import Any, Optional
from larasanic.validation.rules import ValidationRule
from larasanic.support.facades import App


class Unique(ValidationRule):
    """
    Field value must be unique in database table

    Usage:
        'email': 'unique:users'
        'email': 'unique:users,email_address'  # Custom column name
        'email': 'unique:users,email,id,5'     # Ignore ID 5 (for updates)
    """

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Parse parameters: table, column (optional), except_column (optional), except_value (optional)
        if len(self.parameters) < 1:
            raise ValueError("Unique rule requires at least table name parameter")

        table = self.parameters[0]
        column = self.parameters[1] if len(self.parameters) > 1 else field
        except_column = self.parameters[2] if len(self.parameters) > 2 else None
        except_value = self.parameters[3] if len(self.parameters) > 3 else None

        try:
            # Get database manager from container
            db_manager = App.make('db')

            # Get the model
            model = db_manager.get_model(table)
            if not model:
                return False, f"Model '{table}' not found in database"

            # Build query
            query = model.filter(**{column: value})

            # Add exception if provided (for updates)
            if except_column and except_value is not None:
                query = query.exclude(**{except_column: except_value})

            # Check if exists
            exists = await query.exists()

            if exists:
                return False, self.message(field)

            return True, None

        except Exception as e:
            # If we can't check database, fail validation for safety
            return False, f"Database validation error for {field}: {str(e)}"

    def message(self, field: str) -> str:
        return f"The {field} has already been taken."


class Exists(ValidationRule):
    """
    Field value must exist in database table

    Usage:
        'user_id': 'exists:users,id'
        'category_id': 'exists:categories'  # Assumes field name matches column
    """

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Parse parameters: table, column (optional)
        if len(self.parameters) < 1:
            raise ValueError("Exists rule requires at least table name parameter")

        table = self.parameters[0]
        column = self.parameters[1] if len(self.parameters) > 1 else 'id'

        try:
            # Get database manager from container
            db_manager = App.make('db')

            # Get the model
            model = db_manager.get_model(table)
            if not model:
                return False, f"Model '{table}' not found in database"

            # Check if value exists
            exists = await model.filter(**{column: value}).exists()

            if not exists:
                return False, self.message(field)

            return True, None

        except Exception as e:
            # If we can't check database, fail validation for safety
            return False, f"Database validation error for {field}: {str(e)}"

    def message(self, field: str) -> str:
        return f"The selected {field} is invalid."
