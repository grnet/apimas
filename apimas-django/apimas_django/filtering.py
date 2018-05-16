import docular
from django.db.models.query import QuerySet
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas.errors import ValidationError, InvalidInput, GenericFault, \
    AccessDeniedError


class Filter(object):

    def filter(self, queryset, source, operator, value):
        """
        Filter a given queryset based on a specific lookup operator, and a
        value.
        """
        operators = getattr(self, 'OPERATORS', [])
        if operator and operator not in operators:
            raise AccessDeniedError("No such operator")

        kwargs = {
            source + ('__' + operator if operator else ''): value
        }
        return queryset.filter(**kwargs)


class BooleanFilter(Filter):
    pass


class DateFilter(Filter):
    OPERATORS = (
        'gt',
        'gte',
        'lt',
        'lte',
        'range',
    )


class DateTimeFilter(DateFilter):
    pass


class StringFilter(Filter):
    OPERATORS = (
        'contains',
        'startswith',
        'endswith',
        'regex',
    )


class IntegerFilter(Filter):
    OPERATORS = (
        'gt',
        'gte',
        'lt',
        'lte',
    )


class FloatFilter(IntegerFilter):
    pass



def filter_obj(cls):
    def constructor(context, instance, loc):
        docular.construct_last(context)
        value = docular.doc_spec_get(instance) or {}
        source = docular.doc_spec_get(instance.get('source', {})) or loc[-1]
        source = source.replace('.', '__')
        value['source'] = source

        if value.get('filterable'):
            value['filter'] = cls()

        docular.doc_spec_set(instance, value)
    return constructor


def flag_constructor(flag):
    def constructor(instance, loc):
        value = docular.doc_spec_get(instance, default={})
        value[flag] = True
        docular.doc_spec_set(instance, value)
    return constructor


def collect_constructor(context, instance, loc):
    field_filters = dict(docular.doc_spec_iter_values(instance['fields']))
    filters = {}
    for field_name, field_spec in field_filters.iteritems():
        if not field_spec:
            continue
        if 'filter' not in field_spec and 'filters' not in field_spec:
            continue
        filters[field_name] = field_spec

    source = docular.doc_spec_get(instance.get('source', {})) or loc[-1]
    source = source.replace('.', '__')
    value = {
        'filters': filters,
        'source': source,
    }
    docular.doc_spec_set(instance, value)


def no_constructor(instance):
    pass


FILTERING_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.field.collection.django': collect_constructor,
    '.field.struct': collect_constructor,
    '.field.string': filter_obj(StringFilter),
    '.field.serial': filter_obj(Filter),
    '.field.identity': filter_obj(Filter),
    '.field.ref': filter_obj(Filter),
    '.field.integer': filter_obj(IntegerFilter),
    '.field.float': filter_obj(FloatFilter),
    '.field.uuid': filter_obj(Filter),
    '.field.text': filter_obj(StringFilter),
    '.field.email': filter_obj(StringFilter),
    '.field.boolean': filter_obj(Filter),
    '.field.datetime': filter_obj(DateTimeFilter),
    '.field.date': filter_obj(DateFilter),
    '.field.choices': filter_obj(Filter),

    '.flag.filterable': flag_constructor('filterable'),
}, default=no_constructor)



class FilteringProcessor(BaseProcessor):
    """
    A django processor responsible for the filtering of a response, based
    on a query string.
    """
    READ_KEYS = {
        'imported_filters': 'imported/filters',
        'queryset': 'backend/filtered_response',
    }

    WRITE_KEYS = (
        'backend/filtered_response',
    )

    # CONSTRUCTORS = {
    #     'choices':    Object(StringFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    # }

    def __init__(self, collection_loc, action_name, filters, source):
        self.filters = filters

    def prepare_filter(self, filter_path):
        spec = {'filters': self.filters}
        source_path = []
        for segment in filter_path:
            spec = spec['filters']
            if segment not in spec:
                raise AccessDeniedError('%s not filterable (at %s)' %
                                        (str(filter_path), segment))
            spec = spec[segment]
            source_path.append(spec['source'])

        if 'filter' not in spec:
            raise AccessDeniedError('%s not filterable' % str(filter_path))
        return spec['filter'], '__'.join(source_path)

    def execute(self, context_data):
        imported_filters = context_data['imported_filters']
        queryset = context_data['queryset']

        if not queryset or not imported_filters:
            return

        if not isinstance(queryset, QuerySet):
            msg = 'A queryset is expected, {!r} found'
            raise InvalidInput(msg.format(type(queryset)))

        for filter_path, (operator, value) in docular.doc_iter_leaves(
                imported_filters):
            filter_obj, source = self.prepare_filter(filter_path)
            queryset = filter_obj.filter(queryset, source, operator, value)

        queryset = queryset.distinct()
        return (queryset,)


Filtering = ProcessorConstruction(FILTERING_CONSTRUCTORS, FilteringProcessor)
