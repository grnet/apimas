from django.core.exceptions import FieldDoesNotExist
from django.db.models  import Model
from django.db.models.query import QuerySet
from apimas import documents as doc, utils
from apimas.errors import (AccessDeniedError, ConflictError, InvalidInput,
                           InvalidSpec)
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas_django import utils as django_utils
from apimas.converters import Date, DateTime, Integer, Float, Boolean, List
from apimas_django import handlers
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


def construct_file(instance, loc, context):
    docular.construct_last(context)
    source = docular.doc_spec_get(instance.get('source', {}),
                                  default=loc[-1])
    v = {'source': source}
    docular.doc_spec_set(instance, v)


def construct_struct(instance, loc):
    source = docular.doc_spec_get(instance.get('source', {}),
                                  default=loc[-1])
    fields = dict(docular.doc_spec_iter_values(instance['fields']))
    v = {'source': source, 'fields': fields, 'field_type': 'struct'}
    docular.doc_spec_set(instance, v)


def construct_collection(instance, loc, context):
    docular.construct_last(context)
    source = docular.doc_spec_get(instance.get('source', {}),
                                  default=loc[-1])
    fields = dict(docular.doc_spec_iter_values(instance['fields']))
    value = {'source': source, 'fields': fields, 'field_type': 'collection'}
    docular.doc_spec_set(instance, value)


def construct_action(instance, loc):
    on_collection = docular.doc_spec_get(instance['on_collection'])
    value = {'on_collection': on_collection}
    docular.doc_spec_set(instance, value)


INSTANCETODICT_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    {'.field.*': construct_field,
     '.field.struct': construct_struct,
     '.field.file': construct_file,
     '.action': construct_action,
     '.field.collection.django': construct_collection,
    },
    default=no_constructor)


class InstanceToDictProcessor(BaseProcessor):
    READ_KEYS = {
        'instance': 'backend/content',
        'can_read': 'permissions/can_read',
        'read_fields': 'permissions/read_fields',
    }

    WRITE_KEYS = (
        'exportable/content',
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
                    value = [self.to_dict(subvalue, fields)
                             for subvalue in subvalues]
                elif fields_type == 'struct':
                    value = self.to_dict(value, fields)

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

    def execute(self, processor_data):
        """
        A processor which is responsible for converting a
        `django.db.models.Model` or a `django.db.models.query.QuerySet`
        instance into a python dict.

        This dict holds only the information specified by the spec.
        """
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
            instance = [self.to_dict(inst, self.field_spec)
                        for inst in instance]
        return (instance,)


InstanceToDict = ProcessorConstruction(
    INSTANCETODICT_CONSTRUCTORS, InstanceToDictProcessor)


class ObjectRetrievalProcessor(handlers.DjangoBaseHandler):
    READ_KEYS = {
        'kwargs': 'request/meta/kwargs',
        'pk': 'request/meta/kwargs/pk',
    }

    WRITE_KEYS = (
        'backend/content',
    )

    def execute(self, context_data):
        pk = context_data['pk']
        kwargs = context_data['kwargs']
        instance = handlers.get_model_instance(self.spec, pk, kwargs)
        return (instance,)

ObjectRetrieval = handlers._django_base_construction(ObjectRetrievalProcessor)
