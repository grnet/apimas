import docular
from django.db.models.query import QuerySet, Q
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas.errors import InvalidInput


def field_constructor(context, instance, loc):
    docular.construct_last(context)
    value = docular.doc_spec_get(instance) or {}
    source = docular.doc_spec_get(instance.get('source', {})) or loc[-1]
    source = source.replace('.', '__')
    value['source'] = source

    docular.doc_spec_set(instance, value)


def flag_constructor(flag):
    def constructor(instance, loc):
        value = docular.doc_spec_get(instance, default={})
        value[flag] = True
        docular.doc_spec_set(instance, value)
    return constructor


def collect_constructor(context, instance, loc):
    field_data = dict(docular.doc_spec_iter_values(instance['fields']))
    value = docular.doc_spec_get(instance) or {}
    propagate_fields = {}
    for field_name, field_spec in field_data.iteritems():
        if not field_spec:
            continue
        if 'searchable' not in field_spec and 'fields' not in field_spec:
            continue
        propagate_fields[field_name] = field_spec

    value['fields'] = propagate_fields
    source = docular.doc_spec_get(instance.get('source', {})) or loc[-1]
    source = source.replace('.', '__')
    value['source'] = source
    docular.doc_spec_set(instance, value)


def no_constructor(instance):
    pass


SEARCH_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.field.collection.django': collect_constructor,
    '.field.struct': collect_constructor,
    '.field.string': field_constructor,
    '.field.text': field_constructor,
    '.field.email': field_constructor,

    '.flag.searchable': flag_constructor('searchable'),
}, default=no_constructor)


def collect_filters(fields, prefix):
    filters = []
    for key, spec in fields.iteritems():
        source = spec['source']
        path = prefix + (source,)
        if spec.get('searchable', False):
            filters.append('__'.join(path))

        subfields = spec.get('fields', {})
        filters.extend(collect_filters(subfields, path))
    return filters


def make_query(search_filters, value, operator='contains'):
    query = Q()
    for search_filter in search_filters:
        kwarg = {'%s__%s' % (search_filter, operator): value}
        query |= Q(**kwarg)
    return query


class SearchProcessor(BaseProcessor):
    READ_KEYS = {
        'imported_search': 'imported/search',
        'queryset': 'backend/filtered_response',
    }

    WRITE_KEYS = (
        'backend/filtered_response',
    )

    def __init__(self, collection_loc, action_name, fields, source):
        self.fields = fields
        self.search_filters = collect_filters(fields, ())

    def execute(self, context_data):
        search_value = context_data['imported_search']
        queryset = context_data['queryset']

        if not queryset or not search_value:
            return

        if not isinstance(queryset, QuerySet):
            msg = 'A queryset is expected, {!r} found'
            raise InvalidInput(msg.format(type(queryset)))

        search_query = make_query(self.search_filters, search_value)
        queryset = queryset.filter(search_query)
        queryset = queryset.distinct()
        return (queryset,)


Search = ProcessorConstruction(SEARCH_CONSTRUCTORS, SearchProcessor)
