import docular
from django.db.models.query import QuerySet, Q
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas.errors import ValidationError


def no_constructor(instance):
    pass


PAGINATION_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
}, default=no_constructor)


class PaginationProcessor(BaseProcessor):
    READ_KEYS = {
        'imported_pagination': 'imported/pagination',
        'queryset': 'backend/filtered_response',
    }

    WRITE_KEYS = (
        'backend/filtered_response',
        'exportable/meta/count',
        'exportable/meta/next',
        'exportable/meta/previous',
    )

    def __init__(
            self, collection_loc, action_name, pagination_default_limit=None):
        self.default_limit = pagination_default_limit

    def execute(self, context_data):
        pagination_args = context_data['imported_pagination']
        queryset = context_data['queryset']

        if not queryset or not pagination_args:
            return

        if not isinstance(queryset, QuerySet):
            msg = 'A queryset is expected, {!r} found'
            raise InvalidInput(msg.format(type(queryset)))

        offset, limit = pagination_args
        if limit is None:
            limit = self.default_limit

        if limit is None:
            raise ValidationError("'limit' parameter is required.")

        if offset is None:
            offset = 0

        begin, end = offset, offset + limit
        if not queryset.ordered:
           queryset = queryset.order_by('pk')
        else:
            # It seems that looking up queryset.ordered somehow interferes with
            # the slicing below, causing the queryset to be evaluated.
            # Create a new queryset to bypass that.
            queryset = queryset.filter()

        count = queryset.count()
        next_page = ''
        previous_page = ''
        queryset = queryset[begin:end]
        return (queryset, count, next_page, previous_page)


Pagination = ProcessorConstruction(
    PAGINATION_CONSTRUCTORS, PaginationProcessor)
