"""
Pagination Utilities
Provides pagination capabilities for Tortoise ORM models
"""
from typing import TypeVar, Generic, List, Dict, Any, Optional
from tortoise.models import Model
from tortoise.queryset import QuerySet
from math import ceil
import asyncio
import inspect


T = TypeVar('T', bound=Model)


class PaginatedResult(Generic[T]):
    """Container for paginated results"""

    def __init__(
        self,
        items: List[T],
        total_items: int,
        page: int,
        per_page: int,
        total_pages: int
    ):
        self.items = items
        self.total_items = total_items
        self.page = page
        self.per_page = per_page
        self.total_pages = total_pages
        self.has_next = page < total_pages
        self.has_prev = page > 1
        self.next_page = page + 1 if self.has_next else None
        self.prev_page = page - 1 if self.has_prev else None
        self.active_filters = {}

    async def map_items(self, converter):
        """
        Map items through a converter function (supports async)

        Args:
            converter: Function to convert each item (can be async or sync)

        Returns:
            New PaginatedResult with converted items
        """
        if inspect.iscoroutinefunction(converter):
            # Async converter - process all items concurrently
            converted_items = await asyncio.gather(*[converter(item) for item in self.items])
        else:
            # Sync converter
            converted_items = [converter(item) for item in self.items]

        # Return new PaginatedResult with converted items
        return PaginatedResult(
            items=converted_items,
            total_items=self.total_items,
            page=self.page,
            per_page=self.per_page,
            total_pages=self.total_pages
        )

    def to_dict(self, item_converter=None, items_key: str = 'items') -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization

        Args:
            item_converter: Optional function to convert items to dict
            items_key: Key name for items in the result (default: 'items')
        """
        if item_converter:
            items_data = [item_converter(item) for item in self.items]
        else:
            items_data = []
            for item in self.items:
                if hasattr(item, 'to_dict'):
                    items_data.append(item.to_dict())
                elif hasattr(item, 'dict'):
                    items_data.append(item.dict())
                else:
                    items_data.append(str(item))

        return {
            items_key: items_data,
            'pagination': {
                'total_items': self.total_items,
                'total_pages': self.total_pages,
                'current_page': self.page,
                'per_page': self.per_page,
                'has_next': self.has_next,
                'has_prev': self.has_prev,
                'next_page': self.next_page,
                'prev_page': self.prev_page,
                'start_index': ((self.page - 1) * self.per_page) + 1 if self.total_items > 0 else 0,
                'end_index': min(self.page * self.per_page, self.total_items)
            }
        }

    async def to_response(
        self,
        item_converter=None,
        items_key: str = 'items',
        include_filters: bool = True
    ) -> Dict[str, Any]:
        """
        Convert to API response format with data wrapper

        Args:
            item_converter: Optional async/sync function to convert items
            items_key: Key name for items in the result
            include_filters: Include active filters in response

        Returns:
            Dict with items and pagination
        """
        # Convert items if converter provided
        if item_converter:
            if inspect.iscoroutinefunction(item_converter):
                items_data = await asyncio.gather(*[item_converter(item) for item in self.items])
            else:
                items_data = [item_converter(item) for item in self.items]
        else:
            # Try default conversion methods
            items_data = []
            for item in self.items:
                if hasattr(item, 'to_dict'):
                    if inspect.iscoroutinefunction(item.to_dict):
                        items_data.append(await item.to_dict())
                    else:
                        items_data.append(item.to_dict())
                elif hasattr(item, 'dict'):
                    items_data.append(item.dict())
                else:
                    items_data.append(str(item))

        response_data = {
            items_key: items_data,
            'pagination': {
                'total_items': self.total_items,
                'total_pages': self.total_pages,
                'current_page': self.page,
                'per_page': self.per_page,
                'has_next': self.has_next,
                'has_prev': self.has_prev
            }
        }

        # Include active filters if requested
        if include_filters:
            response_data['filters'] = self.active_filters

        return response_data


class PaginationMixin:
    """Mixin to add pagination capabilities to Tortoise models"""

    @staticmethod
    def _process_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process filters to handle list values automatically

        Args:
            filters: Dictionary of filters

        Returns:
            Processed filters with __in suffix for list values
        """
        processed = {}
        for key, value in filters.items():
            # If value is a list, use __in lookup
            if isinstance(value, list):
                if len(value) == 1:
                    # Single item list, use direct filter
                    processed[key] = value[0]
                else:
                    # Multiple items, use __in
                    processed[f"{key}__in"] = value
            else:
                processed[key] = value
        return processed

    @classmethod
    async def paginate(
        cls,
        page: int = None,
        per_page: int = None,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        queryset: Optional[QuerySet] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> PaginatedResult:
        """
        Paginate model results

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            order_by: Field to order by (e.g., '-created_at' for descending)
            filters: Dictionary of filters to apply
            queryset: Optional pre-built queryset to paginate
            params: Optional dict from parse_pagination_params

        Returns:
            PaginatedResult object containing items and pagination info
        """
        # If params dict is provided, extract values from it
        if params:
            page = params.get('page', page) if page is None else page
            per_page = params.get('per_page', per_page) if per_page is None else per_page
            order_by = params.get('order_by', order_by) if order_by is None else order_by
            # Merge filters - params filters take precedence
            if 'filters' in params and params['filters']:
                filters = {**(filters or {}), **params['filters']}

        # Apply defaults
        page = page if page is not None else 1
        per_page = per_page if per_page is not None else 20

        # Ensure page is at least 1
        page = max(1, page)

        # Ensure per_page is reasonable
        per_page = min(max(1, per_page), 100)  # Max 100 items per page

        # Start with provided queryset or all items
        if queryset is not None:
            qs = queryset
        else:
            qs = cls.all()

        # Apply filters if provided
        if filters:
            qs = qs.filter(**cls._process_filters(filters))

        # Apply ordering
        if order_by:
            qs = qs.order_by(order_by)
        elif hasattr(cls, 'Meta') and hasattr(cls.Meta, 'ordering'):
            # Use model's default ordering if available
            qs = qs.order_by(*cls.Meta.ordering)
        else:
            # Default to ordering by id descending (newest first)
            qs = qs.order_by('-id')

        # Get total count
        total_items = await qs.count()

        # Calculate total pages
        total_pages = ceil(total_items / per_page) if total_items > 0 else 1

        # If requesting a page beyond available pages, return empty results
        if page > total_pages:
            return PaginatedResult(
                items=[],
                total_items=total_items,
                page=page,
                per_page=per_page,
                total_pages=total_pages
            )

        # Calculate offset
        offset = (page - 1) * per_page

        # Get items for current page
        items = await qs.offset(offset).limit(per_page)

        return PaginatedResult(
            items=items,
            total_items=total_items,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    @classmethod
    async def paginate_from_request(
        cls,
        request,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        default_order: Optional[str] = '-created_at',
        session_key: Optional[str] = None,
        filter_config: Optional[Dict[str, Any]] = None,
        use_session: bool = True
    ) -> PaginatedResult:
        """
        Convenience method to paginate directly from a request object

        Args:
            request: Sanic request object
            order_by: Override order_by from request
            filters: Additional filters to apply
            default_order: Default ordering if not specified in request
            session_key: Optional custom key for session state (auto-generated from table name if not provided)
            filter_config: Optional filter configuration for building filters from request
            use_session: Whether to use session state persistence (default: True)

        Returns:
            PaginatedResult object
        """
        from larasanic.helpers import session

        params = parse_pagination_params(request)
        
        # Build filters from request if filter_config provided
        if filter_config:
            request_filters = build_filters_from_request(request, filter_config)
        else:
            request_filters = {}

        # Auto-generate session key from table name if not provided
        if use_session and session_key is None:
            # Get table name from model's Meta class
            if hasattr(cls, '_meta') and hasattr(cls._meta, 'db_table'):
                session_key = cls._meta.db_table
            elif hasattr(cls, 'Meta') and hasattr(cls.Meta, 'table'):
                session_key = cls.Meta.table
            else:
                # Fallback to model class name
                session_key = cls.__name__.lower()

        # Handle session state if enabled
        if use_session and session_key:
            session_state_key = f'table_state_{session_key}'
            saved_state = session(session_state_key, {})

            # Restore pagination if not in request params
            if 'page' not in request.args:
                params['page'] = saved_state.get('page', params['page'])
            if 'per_page' not in request.args:
                params['per_page'] = saved_state.get('per_page', params['per_page'])

            # Check if explicitly clearing filters
            if request.args.get('clear_filters') == 'true':
                # Don't restore saved filters
                request_filters = {}
            else:
                # Restore filters if not in request params
                if filter_config and not any(field in request.args for field in filter_config.keys()):
                    # No filter params in request, use saved filters
                    saved_filters = saved_state.get('filters', {})
                    for key, value in saved_filters.items():
                        if key not in request_filters:
                            request_filters[key] = value

            # Save current state to session
            session().put(session_state_key, {
                'page': params['page'],
                'per_page': params['per_page'],
                'filters': request_filters
            })

        # Merge provided filters with request filters
        final_filters = {**(filters or {}), **request_filters}

        # Apply default ordering if not specified
        if not params.get('order_by') and not order_by:
            order_by = default_order

        result = await cls.paginate(
            params=params,
            order_by=order_by,
            filters=final_filters
        )

        # Attach the active filters to the result for reference
        result.active_filters = request_filters

        return result

    @classmethod
    async def paginate_with_search(
        cls,
        page: int = 1,
        per_page: int = None,
        search: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> PaginatedResult:
        from larasanic.defaults import DEFAULT_PAGINATION_PER_PAGE
        if per_page is None:
            per_page = DEFAULT_PAGINATION_PER_PAGE
        """
        Paginate with search capability

        Args:
            page: Page number
            per_page: Items per page
            search: Search query string
            search_fields: Fields to search in
            order_by: Ordering field
            filters: Additional filters

        Returns:
            PaginatedResult with search applied
        """
        qs = cls.all()

        # Apply filters
        if filters:
            qs = qs.filter(**cls._process_filters(filters))

        # Apply search if provided
        if search and search_fields:
            from tortoise.query_utils import Q

            # Build OR query for search fields
            search_query = Q()
            for field in search_fields:
                search_query |= Q(**{f"{field}__icontains": search})

            qs = qs.filter(search_query)

        # Use the regular paginate with the built queryset
        return await cls.paginate(
            page=page,
            per_page=per_page,
            order_by=order_by,
            queryset=qs
        )


def parse_pagination_params(request) -> Dict[str, Any]:
    """
    Parse pagination parameters from request

    Args:
        request: Sanic request object

    Returns:
        Dictionary with page, per_page, search, and order_by
    """
    from larasanic.support.facades import HttpRequest

    params = {}

    # Get page number
    try:
        params['page'] = int(HttpRequest.input('page', 1))
    except (ValueError, TypeError):
        params['page'] = 1

    # Get items per page
    try:
        params['per_page'] = int(HttpRequest.input('per_page', 20))
    except (ValueError, TypeError):
        params['per_page'] = 20

    # Get search query
    params['search'] = HttpRequest.input('search', '').strip()

    # Get ordering
    params['order_by'] = HttpRequest.input('order_by', None)

    return params


def build_filters_from_request(request, filter_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build filters from request parameters based on configuration

    Args:
        request: Sanic request object
        filter_config: Dict defining filterable fields and their options
            Example: {
                'status': {'type': 'list'},
                'source': {'type': 'list', 'default': ['download']},
                'created_after': {'type': 'date', 'field': 'created_at__gte'},
            }

    Returns:
        Dictionary of filters ready for Tortoise ORM
    """
    from larasanic.support.facades import HttpRequest

    filters = {}

    for param_name, config in filter_config.items():
        filter_type = config.get('type', 'single')
        field_name = config.get('field', param_name)
        default = config.get('default', None)

        if filter_type == 'list':
            # Handle list values (can be single or multiple)
            values = HttpRequest.input_list(param_name)
            if values:
                filters[field_name] = values
            elif default is not None:
                filters[field_name] = default

        elif filter_type == 'single':
            # Handle single value
            value = HttpRequest.input(param_name)
            if value:
                filters[field_name] = value
            elif default is not None:
                filters[field_name] = default

        elif filter_type == 'boolean':
            # Handle boolean values
            value = HttpRequest.input(param_name)
            if value is not None:
                filters[field_name] = value.lower() in ('true', '1', 'yes')

        elif filter_type == 'range':
            # Handle range filters (e.g., price_min, price_max)
            min_param = f"{param_name}_min"
            max_param = f"{param_name}_max"

            min_value = HttpRequest.input(min_param)
            max_value = HttpRequest.input(max_param)

            if min_value:
                filters[f"{field_name}__gte"] = min_value
            if max_value:
                filters[f"{field_name}__lte"] = max_value

    return filters


async def paginate_queryset(
    queryset: QuerySet,
    page: int = 1,
    per_page: int = None
) -> PaginatedResult:
    from larasanic.defaults import DEFAULT_PAGINATION_PER_PAGE
    if per_page is None:
        per_page = DEFAULT_PAGINATION_PER_PAGE
    """
    Paginate any queryset

    Args:
        queryset: The queryset to paginate
        page: Page number
        per_page: Items per page

    Returns:
        PaginatedResult object
    """
    page = max(1, page)
    per_page = min(max(1, per_page), 100)

    total_items = await queryset.count()
    total_pages = ceil(total_items / per_page) if total_items > 0 else 1
    page = min(page, total_pages)

    offset = (page - 1) * per_page
    items = await queryset.offset(offset).limit(per_page)

    return PaginatedResult(
        items=items,
        total_items=total_items,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )
