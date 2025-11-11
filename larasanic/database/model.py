"""
Base Model
Provides Laravel-style base model with helper methods
"""
from tortoise.models import Model as TortoiseModel
from tortoise.queryset import QuerySet
from tortoise.exceptions import DoesNotExist
from larasanic.database.pagination import PaginationMixin
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import json


class LaravelQuerySet(QuerySet):
    """Extended QuerySet with Laravel-style methods"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._random_order = False

    def inRandomOrder(self):
        """
        Order results randomly

        Returns:
            QuerySet ordered randomly

        Example:
            users = await User.filter(active=True).inRandomOrder().all()
        """
        queryset = self._clone()
        queryset._random_order = True
        return queryset

    def _clone(self):
        """Override clone to preserve random order flag"""
        queryset = super()._clone()
        queryset._random_order = getattr(self, '_random_order', False)
        return queryset

    async def _execute(self):
        """Override execute to add RANDOM() ordering if needed"""
        if getattr(self, '_random_order', False):
            # Clear existing orderings and use raw SQL
            self._orderings = []
            # Modify the query to add ORDER BY RANDOM()
            self.query = self.query.orderby('RANDOM()')
        return await super()._execute()


class ModelNotFoundException(Exception):
    """Exception raised when a model is not found"""
    pass


class Model(TortoiseModel, PaginationMixin):
    """
    Laravel-style base model class with helper methods

    All application models should inherit from this class
    instead of Tortoise's Model directly

    Examples:
        # Find by ID or fail
        user = await User.find_or_fail(1)

        # Get first or fail
        user = await User.where(email='test@test.com').first_or_fail()

        # Get or create
        user, created = await User.first_or_create(
            email='test@test.com',
            defaults={'password_hash': 'hash'}
        )

        # Update or create
        user = await User.update_or_create(
            email='test@test.com',
            defaults={'password_hash': 'new_hash'}
        )

        # Get latest/oldest
        users = await User.latest()
        users = await User.oldest()

        # Random order
        users = await User.inRandomOrder().all()
        users = await User.where(active=True).inRandomOrder().limit(10)

        # Pluck values
        emails = await User.pluck('email')

        # Check existence
        exists = await User.where(email='test@test.com').exists()

        # Chunk processing
        async for chunk in User.chunk(100):
            # Process 100 records at a time
            pass

        # Laravel-style hidden fields
        class User(Model):
            hidden = ['password_hash', 'secret_key']

        # Laravel-style casts
        class User(Model):
            casts = {
                'is_active': 'bool',
                'metadata': 'json',
                'created_at': 'datetime'
            }
    """

    # Laravel-style properties
    hidden: List[str] = []  # Fields to hide in serialization
    casts: Dict[str, str] = {}  # Field type casting

    class Meta:
        abstract = True

    # Override to use custom QuerySet
    @classmethod
    def _init_meta(cls, **kwargs):
        """Initialize meta with custom QuerySet"""
        super()._init_meta(**kwargs)
        cls._meta.queryset_class = LaravelQuerySet

    # ====================
    # Query Builder Helpers
    # ====================

    @classmethod
    def where(cls, **filters):
        """
        Laravel-style where clause (alias for filter)

        Args:
            **filters: Field filters

        Returns:
            LaravelQuerySet

        Example:
            users = await User.where(email='test@test.com').all()
        """
        return LaravelQuerySet(model=cls).filter(**filters)

    @classmethod
    def filter(cls, *args, **kwargs):
        """Override filter to return LaravelQuerySet"""
        return LaravelQuerySet(model=cls).filter(*args, **kwargs)

    @classmethod
    def all(cls):
        """Override all to return LaravelQuerySet"""
        return LaravelQuerySet(model=cls)

    @classmethod
    async def raw(cls, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query and return results as list of dictionaries

        Args:
            query: Raw SQL query string
            params: Optional list of parameters for parameterized queries

        Returns:
            List of dictionaries with query results

        Example:
            results = await User.raw(
                "SELECT * FROM users WHERE created_at > ?",
                [datetime(2024, 1, 1)]
            )

            duplicates = await Files.raw('''
                SELECT artist, title, COUNT(*) as count
                FROM files
                WHERE status = ?
                GROUP BY artist, title
                HAVING COUNT(*) > 1
            ''', ['analyzing'])
        """
        connection = cls._meta.db
        params = params or []

        return await connection.execute_query_dict(query, params)

    @classmethod
    async def find(cls, pk: Any) -> Optional['Model']:
        """
        Find record by primary key

        Args:
            pk: Primary key value

        Returns:
            Model instance or None

        Example:
            user = await User.find(1)
        """
        return await cls.get_or_none(pk=pk)

    @classmethod
    async def find_or_fail(cls, pk: Any) -> 'Model':
        """
        Find record by primary key or raise exception

        Args:
            pk: Primary key value

        Returns:
            Model instance

        Raises:
            ModelNotFoundException: If record not found

        Example:
            user = await User.find_or_fail(1)
        """
        instance = await cls.get_or_none(pk=pk)
        if not instance:
            raise ModelNotFoundException(
                f"{cls.__name__} with primary key {pk} not found"
            )
        return instance

    @classmethod
    async def first_or_fail(cls, **filters) -> 'Model':
        """
        Get first record matching filters or raise exception

        Args:
            **filters: Field filters

        Returns:
            Model instance

        Raises:
            ModelNotFoundException: If no record found

        Example:
            user = await User.first_or_fail(email='test@test.com')
        """
        instance = await cls.filter(**filters).first()
        if not instance:
            raise ModelNotFoundException(
                f"{cls.__name__} matching filters {filters} not found"
            )
        return instance

    @classmethod
    async def first_or_create(
        cls,
        defaults: Optional[Dict[str, Any]] = None,
        **filters
    ) -> tuple['Model', bool]:
        """
        Get first record or create if doesn't exist

        Args:
            defaults: Additional fields for creation
            **filters: Lookup filters

        Returns:
            Tuple of (instance, created boolean)

        Example:
            user, created = await User.first_or_create(
                email='test@test.com',
                defaults={'password_hash': 'hash'}
            )
        """
        instance = await cls.filter(**filters).first()
        if instance:
            return instance, False

        # Create new instance with filters and defaults
        create_data = {**filters, **(defaults or {})}
        instance = await cls.create(**create_data)
        return instance, True

    @classmethod
    async def update_or_create(
        cls,
        defaults: Optional[Dict[str, Any]] = None,
        **filters
    ) -> 'Model':
        """
        Update existing record or create new one

        Args:
            defaults: Fields to update or create with
            **filters: Lookup filters

        Returns:
            Model instance

        Example:
            user = await User.update_or_create(
                email='test@test.com',
                defaults={'password_hash': 'new_hash'}
            )
        """
        instance = await cls.filter(**filters).first()

        if instance:
            # Update existing
            if defaults:
                await instance.update_from_dict(defaults).save()
            return instance

        # Create new
        create_data = {**filters, **(defaults or {})}
        return await cls.create(**create_data)

    # ====================
    # Query Shortcuts
    # ====================

    @classmethod
    async def latest(cls, field: str = 'created_at', limit: Optional[int] = None):
        """
        Get records ordered by field descending (newest first)

        Args:
            field: Field to order by (default: created_at)
            limit: Optional limit

        Returns:
            List of model instances or QuerySet if no limit

        Example:
            users = await User.latest()
            recent_users = await User.latest(limit=10)
        """
        queryset = cls.all().order_by(f'-{field}')
        if limit:
            return await queryset.limit(limit)
        return queryset

    @classmethod
    async def oldest(cls, field: str = 'created_at', limit: Optional[int] = None):
        """
        Get records ordered by field ascending (oldest first)

        Args:
            field: Field to order by (default: created_at)
            limit: Optional limit

        Returns:
            List of model instances or QuerySet if no limit

        Example:
            users = await User.oldest()
        """
        queryset = cls.all().order_by(field)
        if limit:
            return await queryset.limit(limit)
        return queryset

    @classmethod
    def inRandomOrder(cls):
        """
        Order records randomly (Laravel-style)

        Returns:
            QuerySet ordered randomly

        Example:
            users = await User.inRandomOrder().all()
            users = await User.inRandomOrder().limit(10)
            pending = await Files.where(status='pending').inRandomOrder().all()
        """
        from tortoise.expressions import RawSQL
        return cls.all().order_by(RawSQL('RANDOM()'))

    @classmethod
    async def pluck(cls, field: str, **filters) -> List[Any]:
        """
        Get list of values for a specific field

        Args:
            field: Field name to pluck
            **filters: Optional filters

        Returns:
            List of field values

        Example:
            emails = await User.pluck('email')
            active_emails = await User.pluck('email', is_active=True)
        """
        queryset = cls.filter(**filters) if filters else cls.all()
        records = await queryset.values_list(field, flat=True)
        return list(records)

    @classmethod
    async def exists(cls, **filters) -> bool:
        """
        Check if any record matching filters exists

        Args:
            **filters: Field filters

        Returns:
            True if exists, False otherwise

        Example:
            if await User.exists(email='test@test.com'):
                print("Email taken")
        """
        return await cls.filter(**filters).exists()

    @classmethod
    async def chunk(cls, size: int = 100, **filters):
        """
        Process records in chunks (generator)

        Args:
            size: Chunk size
            **filters: Optional filters

        Yields:
            Lists of model instances

        Example:
            async for chunk in User.chunk(100):
                for user in chunk:
                    await user.process()
        """
        queryset = cls.filter(**filters) if filters else cls.all()
        offset = 0

        while True:
            records = await queryset.offset(offset).limit(size)
            if not records:
                break
            yield records
            offset += size

    # ====================
    # Instance Methods
    # ====================

    async def fresh(self, fields: Optional[List[str]] = None) -> Optional['Model']:
        """
        Get a fresh instance from database

        Args:
            fields: Specific fields to fetch (optional)

        Returns:
            Fresh model instance or None if deleted

        Example:
            fresh_user = await user.fresh()
        """
        if not self.pk:
            return None

        if fields:
            return await self.__class__.get_or_none(pk=self.pk).only(*fields)
        return await self.__class__.get_or_none(pk=self.pk)

    async def refresh(self, fields: Optional[List[str]] = None) -> 'Model':
        """
        Refresh the current instance from database

        Args:
            fields: Specific fields to refresh (optional)

        Returns:
            Self (refreshed)

        Example:
            await user.refresh()
        """
        if not self.pk:
            return self

        fresh = await self.fresh(fields=fields)
        if fresh:
            # Update current instance attributes
            for field in self._meta.fields_map.keys():
                if fields is None or field in fields:
                    setattr(self, field, getattr(fresh, field))
        return self

    async def increment(self, field: str, amount: int = 1) -> 'Model':
        """
        Increment a field value

        Args:
            field: Field name
            amount: Amount to increment (default: 1)

        Returns:
            Self

        Example:
            await user.increment('login_count')
        """
        current_value = getattr(self, field, 0) or 0
        setattr(self, field, current_value + amount)
        await self.save(update_fields=[field])
        return self

    async def decrement(self, field: str, amount: int = 1) -> 'Model':
        """
        Decrement a field value

        Args:
            field: Field name
            amount: Amount to decrement (default: 1)

        Returns:
            Self

        Example:
            await product.decrement('stock', 5)
        """
        return await self.increment(field, -amount)

    async def touch(self, field: str = 'updated_at') -> 'Model':
        """
        Update timestamp field to now

        Args:
            field: Timestamp field name (default: updated_at)

        Returns:
            Self

        Example:
            await user.touch()
        """
        if hasattr(self, field):
            setattr(self, field, datetime.utcnow())
            await self.save(update_fields=[field])
        return self

    def fill(self, **attributes) -> 'Model':
        """
        Mass assign attributes (doesn't save)

        Args:
            **attributes: Attributes to set

        Returns:
            Self

        Example:
            user.fill(email='new@test.com', name='New Name')
            await user.save()
        """
        for key, value in attributes.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self

    def only(self, *fields) -> Dict[str, Any]:
        """
        Get only specified attributes

        Args:
            *fields: Field names to include

        Returns:
            Dictionary with only specified fields

        Example:
            data = user.only('id', 'email')
        """
        return {field: getattr(self, field, None) for field in fields}

    def except_fields(self, *fields) -> Dict[str, Any]:
        """
        Get all attributes except specified ones

        Args:
            *fields: Field names to exclude

        Returns:
            Dictionary without specified fields

        Example:
            data = user.except_fields('password_hash')
        """
        all_fields = self._meta.fields_map.keys()
        return {
            field: getattr(self, field, None)
            for field in all_fields
            if field not in fields
        }

    # ====================
    # Serialization
    # ====================

    def to_dict(self, exclude: Optional[List[str]] = None, include_hidden: bool = False) -> Dict[str, Any]:
        """
        Convert model to dictionary (respects Laravel-style 'hidden' attribute)

        Args:
            exclude: Additional fields to exclude
            include_hidden: If True, include fields marked as hidden (default: False)

        Returns:
            Dictionary representation

        Example:
            data = user.to_dict()  # Excludes fields in user.hidden
            data = user.to_dict(exclude=['email'])  # Also excludes email
            data = user.to_dict(include_hidden=True)  # Includes hidden fields
        """
        exclude = exclude or []

        # Combine exclude list with hidden fields (unless include_hidden=True)
        if not include_hidden:
            hidden_fields = getattr(self.__class__, 'hidden', [])
            exclude = list(set(exclude + hidden_fields))

        data = {}

        for field in self._meta.fields_map.keys():
            if field not in exclude:
                value = getattr(self, field, None)

                # Apply casts if defined
                casts = getattr(self.__class__, 'casts', {})
                if field in casts:
                    value = self._cast_attribute(field, value, casts[field])
                # Default: Convert datetime to ISO format
                elif isinstance(value, datetime):
                    value = value.isoformat()

                data[field] = value

        return data

    def _cast_attribute(self, field: str, value: Any, cast_type: str) -> Any:
        """
        Cast attribute to specified type (Laravel-style casting)

        Args:
            field: Field name
            value: Field value
            cast_type: Type to cast to ('bool', 'int', 'float', 'string', 'json', 'datetime')

        Returns:
            Casted value
        """
        if value is None:
            return None

        cast_type = cast_type.lower()

        if cast_type == 'bool' or cast_type == 'boolean':
            return bool(value)
        elif cast_type == 'int' or cast_type == 'integer':
            return int(value)
        elif cast_type == 'float' or cast_type == 'double':
            return float(value)
        elif cast_type == 'string' or cast_type == 'str':
            return str(value)
        elif cast_type == 'json':
            # If already dict/list, return as-is; if string, parse it
            if isinstance(value, (dict, list)):
                return value
            return json.loads(value) if isinstance(value, str) else value
        elif cast_type == 'datetime':
            if isinstance(value, datetime):
                return value.isoformat()
            return value

        return value

    def to_json(self, exclude: Optional[List[str]] = None, indent: Optional[int] = None) -> str:
        """
        Convert model to JSON string

        Args:
            exclude: Fields to exclude
            indent: JSON indentation

        Returns:
            JSON string

        Example:
            json_str = user.to_json(exclude=['password_hash'])
        """
        return json.dumps(self.to_dict(exclude=exclude), indent=indent, default=str)

    # ====================
    # Magic Methods
    # ====================

    def __repr__(self) -> str:
        """String representation"""
        if hasattr(self, 'id'):
            return f"<{self.__class__.__name__} id={self.id}>"
        return f"<{self.__class__.__name__}>"


class BaseModel(Model):
    """
    Alias for Model - for compatibility with different naming conventions
    """

    class Meta:
        abstract = True
