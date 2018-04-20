from django.db.models  import Model
from django.db.models.query import QuerySet
from apimas.errors import InvalidInput
from apimas.components import BaseProcessor, ProcessorConstruction
import docular


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


def access_relation(value, key):
    if hasattr(value, 'through'):
        flt = {value.source_field_name: key}
        return value.through.objects.filter(**flt)
    return value.all()


class InstanceToDictProcessor(BaseProcessor):
    READ_KEYS = {
        'instance': 'backend/checked_response',
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

    def to_dict(self, instance, spec):
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
                    subvalues = access_relation(value, key=instance)
                    value = [self.to_dict(subvalue, fields)
                             for subvalue in subvalues]
                elif fields_type == 'struct':
                    value = self.to_dict(value, fields)

            data[k] = value
        return data

    def execute(self, processor_data):
        instance = processor_data['instance']
        if instance is None:
            return (None,)

        if instance and (not isinstance(instance, Model) and not
                         isinstance(instance, QuerySet) and not
                         isinstance(instance, list)):
            msg = 'Unexpected type {!r} found.'
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
