from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import FieldDoesNotExist
from django.db.models  import Model
from django.db.models.query import QuerySet
from apimas import documents as doc, utils
from apimas.errors import (AccessDeniedError, ConflictError, InvalidInput,
                           InvalidSpec)
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas_django import utils as django_utils
from apimas.serializers import Date, DateTime, Integer, Float, Boolean, List
import docular


REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='


def no_constructor(instance):
    pass


def copy_fields_constructor(instance):
    docular.doc_spec_set(instance,
                         dict(docular.doc_spec_iter(instance['fields'])))

def construct_field(instance, loc):
    source = docular.doc_spec_get(instance.get('source', {}),
                                  default=loc[-1])
    v = {'source': source}
    docular.doc_spec_set(instance, v)


def construct_resource(instance):
    v = dict(docular.doc_spec_iter_values(instance))
    docular.doc_spec_set(instance, v)


def construct_struct(instance, loc):
    source = docular.doc_spec_get(instance.get('source', {}),
                                  default=loc[-1])
    fields = docular.doc_spec_get(instance['fields'])
    v = {'source': source, 'fields': fields, 'field_type': 'struct'}
    docular.doc_spec_set(instance, v)


def construct_collection(instance, loc, context):
    docular.construct_last(context)
    source = docular.doc_spec_get(instance.get('source', {}),
                                  default=loc[-1])
    fields = docular.doc_spec_get(instance['fields'])
    value = {'source': source, 'fields': fields, 'field_type': 'collection'}
    docular.doc_spec_set(instance, value)


def construct_action(instance, loc):
    on_collection = docular.doc_spec_get(instance['on_collection'])
    value = {'on_collection': on_collection}
    docular.doc_spec_set(instance, value)


INSTANCETODICT_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    {'.field.*': construct_field,
     '.resource': construct_resource,
     '.action': construct_action,
     '.field.collection.django': construct_collection,
    },
    default=no_constructor)


class InstanceToDictProcessor(BaseProcessor):
    name = 'apimas_django.processors.InstanceToDict'

    READ_KEYS = {
        'instance': 'backend/content',
    }

    WRITE_KEYS = (
        'response/content',
    )

    def __init__(self, collection_loc, action_name,
                 source, fields, field_type, on_collection):
        self.collection_spec = {'source': source,
                                'fields': fields,
                                'field_type': field_type}
        self.on_collection = on_collection
        self.field_spec = fields

    # def _extract_many(self, instance, field_name):
    #     """
    #     Extracts the value of a many to many or one to many django model
    #     relation.
    #     """
    #     try:
    #         return getattr(instance, field_name).all()
    #     except AttributeError:
    #         return getattr(instance, field_name + '_set').all()

    # def _extract_rel_id(self, instance, field_name):
    #     """
    #     Extracts the id of a one to one or many to one django model
    #     relation.
    #     """
    #     try:
    #         return getattr(instance, field_name + '_id')
    #     except AttributeError:
    #         return getattr(instance, field_name)

    # def _extract_rel(self, orm_model, instance, field, field_spec):
    #     """
    #     Helper function to get the python native format of a django
    #     related field.
    #     """
    #     many = field.many_to_many or field.one_to_many
    #     source = docular.doc_spec_get(field_spec['source']) or field.name
    #     if many:
    #         value = self._extract_many(instance, source)
    #         if REF in field_spec[ARRAY_OF]:
    #             return [getattr(v, 'pk') for v in value]
    #         return [
    #             self.to_dict(
    #                 field.related_model, v,
    #                 field_spec[ARRAY_OF][STRUCT]
    #             ) for v in value
    #         ]
    #     if not hasattr(instance, field.name):
    #         return None
    #     if REF in field_spec:
    #         return self._extract_rel_id(instance, field.name)
    #     return self.to_dict(field.related_model, getattr(instance, source),
    #                         field_spec['.struct='])

    def to_dict(self, instance, spec):
        """
        Constructs a given model instance a python dict.

        Only the model attributes which are declared on specification are
        included in the returned dictionary.

        Args:
            orm_model: Django model associated with the instance.
            instance: Model instance to be converted into a python dict.
            spec (dict): Specification of collection.

        Returns:
            dict: Dictionary format of a model instance.
        """
        if instance is None:
            return None

        data = {}
        for k, v in spec.iteritems():
            source = v['source'] if v else k
            fields = v.get('fields') if v else None
            fields_type = v.get('field_type') if v else None
            value = instance
            for elem in source.split('.'):
                if value is None:
                    break
                value = getattr(value, elem)

            if fields:
                if fields_type == 'collection':
                    subvalues = value.all()
                    value = [self.to_dict( subvalue, spec=fields)
                             for subvalue in subvalues]
                elif fields_type == 'struct':
                    value = self.to_dict(value, spec=fields)

            # try:
            #     field = orm_model._meta.get_field(source)
            #     print k, field.related_model
            #     if field.related_model is None:
            #         value = getattr(instance, field.name)
            #     else:
            #         value = self._extract_rel(orm_model, instance, field,
            #                                   v)
            # except FieldDoesNotExist:
            #     # If instance does not have any field with that name, then
            #     # check if there is any property-like.
            #     value = getattr(instance, source)
            #     print "GOT VALUE", value, "from source", source
            data[k] = value
        return data

    def process(self, collection, url, action, context):
        """
        A processor which is responsible for converting a
        `django.db.models.Model` or a `django.db.models.query.QuerySet`
        instance into a python dict.

        This dict holds only the information specified by the spec.
        """
        processor_data = self.read(context)
        instance = processor_data['instance']
        if instance is None:
            self.write(None, context)
            return

        if instance and (not isinstance(instance, Model) and not
                       isinstance(instance, QuerySet)):
            msg = 'A model instance or a queryset is expected. {!r} found.'
            raise InvalidInput(msg.format(type(instance)))

        if not self.on_collection:
            instance = None if instance is None else self.to_dict(
                instance, self.field_spec)
        else:
            instance = [self.to_dict(inst, self.field_spec) for inst in instance]
        self.write((instance,), context)


InstanceToDict = ProcessorConstruction(
    INSTANCETODICT_CONSTRUCTORS, InstanceToDictProcessor)


def _get_filter_spec(params):
    """
    Extracts field name, operator and value from a query string.
    """
    filter_spec = {}
    for k, v in params.iteritems():
        field_name, _, spec = k.partition('__')
        filter_spec[field_name] = (spec, v)
    return filter_spec


class Filter(object):
    """
    A class to filter a queryset based on a condition.

    Typically, a condition consists of three parts:
        * The field (aka column) based on which filter is executed.
        * Lookup operators, e.g. regex, contains, etc. An absence of a
          lookup operator means exact match.
        * The value which must be satified.

    Args:
        source (string): The name of the field, as it is specified in the
            django models.
    """

    def __init__(self, source=None, **serializer_kwargs):
        self.source = source
        self.serializer_kwargs = serializer_kwargs

    def _get_serializer(self, operator):
        serializer_cls = getattr(self, 'SERIALIZER', None)
        if serializer_cls:
            return serializer_cls(**self.serializer_kwargs)
        return None

    def to_native(self, value, operator):
        """
        Converts value of query parameter into a native represenation, using
        an appropriate serializer.

        If a serializer class is not specified, then the given value is used
        as is.
        """
        serializer = self._get_serializer(operator)
        if serializer:
            return serializer.deserialize(value)
        return value

    def filter(self, operator, queryset, value):
        """
        Filter a given queryset based on a specific lookup operator, and a
        value.
        """
        operators = getattr(self, 'OPERATORS', [])
        if operator and operator not in operators:
            return queryset
        value = self.to_native(value, operator)
        kwargs = {
            self.source + ('__' + operator if operator else ''): value
        }
        return queryset.filter(**kwargs)

    def __call__(self, operator, queryset, value):
        return self.filter(operator, queryset, value)


class BooleanFilter(Filter):
    SERIALIZER = Boolean


class DateFilter(Filter):
    OPERATORS = (
        'gt',
        'gte',
        'lt',
        'lte',
        'range',
    )
    SERIALIZER = Date

    def to_native(self, value, operator):
        """
        Override the conversion of a query parameter to handle the case when
        the 'range' lookup operator is given. This operator expects two dates
        (comma seperated).

        Example:
            /?datefield__range=2015-01-01,2017-01-01
        """
        if operator != 'range':
            return super(DateFilter, self).to_native(value, operator)
        # Then we expect multiple values (comma seperated).
        values = value.split(',')
        if len(values) != 2:
            msg = "Operator 'range' requires two values."
            raise InvalidInput(msg)
        serializer = List(Date(self.serializer_kwargs))
        return serializer.deserialize(values)


class DateTimeFilter(DateFilter):
    SERIALIZER = DateTime


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
    SERIALIZER = Integer


class FloatFilter(IntegerFilter):
    SERIALIZER = Float


class StructFilter(Filter):
    """
    This class allows nested filtering, i.e. to filter based on the fields
    of a struct entity.
    """
    def __init__(self, filters, source=None, **kwargs):
        super(StructFilter, self).__init__(source=source, **kwargs)
        self.filters = filters

    def filter(self, operator, queryset, value):
        nested_field, _, operator = operator.partition('__')
        filter_obj = self.filters.get(nested_field)
        if not filter_obj:
            return queryset
        filter_obj.source = self.source + '__' + nested_field
        return filter_obj(operator, queryset, value)


# def _construct_meta(context):
#     node = docu.doc_get(context.top_spec, context.loc[:-1])
#     meta = node.get('.meta', {})
#     source = meta.get('source', context.parent_name)

#     if 'source' in context.spec:
#         msg = 'Key {!r} has already been set. ({!s})'
#         raise ConflictError(msg.format('source', ','.join(context.loc)))
#     return {'source': source}


def filter_obj(cls):
    def constructor(context, instance, loc):
        docular.construct_last(context)
        source = docular.doc_spec_get(instance.get('source', {}),
                                  default=loc[-1])
        source = source.replace('.', '__')
        value = docular.doc_spec_get(instance) or {}
        filterclass = cls(source=source) if value.get('filterable') else None
        docular.doc_spec_set(instance, filterclass)
    return constructor


def flag_constructor(flag):
    def constructor(instance, loc):
        value = docular.doc_spec_get(instance, default={})
        value[flag] = True
        docular.doc_spec_set(instance, value)
    return constructor


def collect_constructor(context, instance, loc):
    v = dict(docular.doc_spec_iter_values(instance['fields']))
    value = {'filters': v}
    docular.doc_spec_set(instance, value)


FILTERING_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.field.collection.django': collect_constructor,
    '.field.string': filter_obj(StringFilter),
    '.field.integer': filter_obj(IntegerFilter),
    '.flag.filterable': flag_constructor('filterable'),
}, default=no_constructor)



class FilteringProcessor(BaseProcessor):
    """
    A django processor responsible for the filtering of a response, based
    on a query string.
    """
    name = 'apimas_django.processors.Filtering'

    READ_KEYS = {
        'params': 'request/meta/params',
        'queryset': 'response/content',
    }

    WRITE_KEYS = (
        'response/content',
    )

    # CONSTRUCTORS = {
    #     'ref':        Object(Filter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'serial':     Object(Filter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'integer':    Object(IntegerFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'float':      Object(FloatFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'string':     Object(StringFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'text':       Object(StringFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'choices':    Object(StringFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'email':      Object(StringFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'boolean':    Object(BooleanFilter, pre_hook=_construct_meta,
    #                          conditionals=['.filterable']),
    #     'datetime':   Object(
    #                      DateTimeFilter,
    #                      kwargs_spec_mapping={'format': 'date_format'},
    #                      kwargs_spec=True, pre_hook=_construct_meta,
    #                      conditionals=['.filterable']),
    #     'date':       Object(
    #                      DateFilter,
    #                      kwargs_spec_mapping={'format': 'date_format'},
    #                      kwargs_spec=True, pre_hook=_construct_meta,
    #                      conditionals=['.filterable']),
    #     'struct':     Object(
    #                      StructFilter, args_spec=True,
    #                      args_spec_name='filters',
    #                      pre_hook=_construct_meta,
    #                      conditionals=['.filterable']),
    #     'default':    Dummy()
    # }

    def __init__(self, collection_loc, action_name, filters):
        self.filters = filters

    def process(self, collection, url, action, context):
        """
        The expected response is a `django.db.models.queryset.QuerySet` object
        returned by a django handler.

        After filtering, this processor substitutes the previous `QuerySet`
        object with the new one.
        """
        processor_data = self.read(context)
        params = processor_data['params']
        queryset = processor_data['queryset']
        if not queryset or not params:
            return
        if not isinstance(queryset, QuerySet):
            msg = 'A queryset is expected, {!r} found'
            raise InvalidInput(msg.format(type(queryset)))
        filter_spec = _get_filter_spec(params)
        for field_name, (operator, value) in filter_spec.iteritems():
            filter_obj = self.filters.get(field_name)
            if filter_obj:
                queryset = filter_obj(operator, queryset, value)

        self.write((queryset,), context)


Filtering = ProcessorConstruction(FILTERING_CONSTRUCTORS, FilteringProcessor)


class UserRetrieval(BaseProcessor):
    READ_KEYS = {
        'identity': 'store/auth/identity',
    }

    WRITE_KEYS = (
        'store/auth/user',
    )

    def __init__(self, collection, collection_spec, userid_extractor=None,
                 **meta):
        super(UserRetrieval, self).__init__(
            collection, collection_spec, **meta)
        if userid_extractor:
            userid_extractor = utils.import_object(userid_extractor)
            assert callable(userid_extractor), (
                '"userid_extractor" must be a callable')
        self.userid_extractor = userid_extractor

    def process(self, collection, url, action, context):
        context_data = self.read(context)
        identity = context_data.get('identity')
        if not identity or not self.userid_extractor:
            user_id = None
        else:
            user_id = self.userid_extractor(identity)
        model_backend = ModelBackend()
        user = model_backend.get_user(user_id)
        self.write((user,), context)


class ObjectRetrieval(BaseProcessor):
    READ_KEYS = {
        'model': 'store/orm_model',
        'pk': 'request/meta/pk',
    }

    WRITE_KEYS = (
        'store/instance',
    )

    def process(self, collection, url, action, context):
        context_data = self.read(context)
        model, resource_id = context_data['model'], context_data['pk']
        if model is None:
            loc = self.READ_KEYS['model']
            raise InvalidInput(
                'Processor requires a django model on location {!r},'
                ' nothing found'.format(loc))

        if resource_id is None:
            loc = self.READ_KEYS['pk']
            msg = 'Processor requires a pk on location {!r}, nothing found'
            raise InvalidInput(msg.format(loc))

        instance = django_utils.get_instance(model, resource_id)
        self.write((instance,), context)
