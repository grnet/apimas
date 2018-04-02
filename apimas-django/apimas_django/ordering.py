import docular
from django.db.models.query import QuerySet
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas.errors import InvalidInput, AccessDeniedError


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
        if 'orderable' not in field_spec and 'fields' not in field_spec:
            continue
        propagate_fields[field_name] = field_spec

    value['fields'] = propagate_fields
    source = docular.doc_spec_get(instance.get('source', {})) or loc[-1]
    source = source.replace('.', '__')
    value['source'] = source
    docular.doc_spec_set(instance, value)


def no_constructor(instance):
    pass


ORDERING_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.field.collection.django': collect_constructor,
    '.field.struct': collect_constructor,
    '.field.*': field_constructor,

    '.flag.orderable': flag_constructor('orderable'),
}, default=no_constructor)


class OrderingProcessor(BaseProcessor):
    READ_KEYS = {
        'imported_ordering': 'imported/ordering',
        'queryset': 'backend/filtered_response',
    }

    WRITE_KEYS = (
        'backend/filtered_response',
    )

    # CONSTRUCTORS = {
    #     'choices':    Object(StringFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    # }

    def __init__(self, collection_loc, action_name, fields, source):
        self.fields = fields

    def get_ordering_source(self, ordering_path):
        spec = {'fields': self.fields}
        source_path = []
        for segment in ordering_path:
            spec = spec['fields']
            if segment not in spec:
                raise AccessDeniedError('%s not orderable (at %s)' %
                                        (str(ordering_path), segment))
            spec = spec[segment]
            source_path.append(spec['source'])

        if 'orderable' not in spec:
            raise AccessDeniedError('%s not orderable' % str(ordering_path))
        return '__'.join(source_path)

    def execute(self, context_data):
        imported_ordering = context_data['imported_ordering']
        queryset = context_data['queryset']

        if not queryset or not imported_ordering:
            return

        if not isinstance(queryset, QuerySet):
            msg = 'A queryset is expected, {!r} found'
            raise InvalidInput(msg.format(type(queryset)))

        orderings = []
        for ordering_path, reverse in imported_ordering:
            source = self.get_ordering_source(ordering_path)
            orderings.append('%s%s' % ('-' if reverse else '', source))

        # Ensure we always have a total order
        orderings.append('pk')

        if orderings:
            queryset = queryset.order_by(*orderings)
        return (queryset,)


Ordering = ProcessorConstruction(ORDERING_CONSTRUCTORS, OrderingProcessor)
