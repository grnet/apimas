import docular
from apimas import serializers as srs
from apimas import documents as doc
from apimas.errors import AccessDeniedError
from apimas.components import BaseProcessor, ProcessorConstruction


def get_meta(top_spec, loc, key):
    return docular.doc_spec_get(
        docular.doc_inherit2(top_spec, loc, ('.meta', key)))


def serializer_obj(cls, dependencies=None):
    def constructor(context, instance, loc, top_spec):
        docular.construct_last(context)
        predicate = context['predicate']

        kwargs = docular.doc_spec_get(instance, default={})
        for key in dependencies or []:
            kwargs[key] = get_meta(top_spec, loc, key)


        instance_args = dict(docular.doc_spec_iter_values(instance))
        kwargs.update(instance_args)

        serializer = cls(**kwargs)
        value = {'serializer': serializer}
        docular.doc_spec_set(instance, value)
    return constructor


def cerberus_flag(flag):
    def constructor(instance, loc):
        value = docular.doc_spec_get(instance, default={})
        value[flag] = True
        docular.doc_spec_set(instance, value)
    return constructor


def no_constructor(instance):
    pass


def construct_string(instance, loc):
    if '=' not in instance:
        #print "No string value at", loc
        pass
    else:
        instance['='] = str(instance['='])


def list_constructor(context, instance, loc, top_spec):
    predicate = context['predicate']
    value = docular.doc_spec_get(instance, default={})
    field_serializers = dict(docular.doc_spec_iter_values(instance['fields']))
    resource_serializer = srs.Struct(schema=field_serializers)
    value['serializer'] = resource_serializer
    docular.doc_spec_set(instance, value)
    serializer_obj(srs.List, dependencies=None)(
        context, instance, loc, top_spec)


def field_struct_constructor(context, instance, loc, top_spec):
    value = docular.doc_spec_get(instance, default={})
    field_serializers = dict(docular.doc_spec_iter_values(instance['fields']))
    value['schema'] = field_serializers
    docular.doc_spec_set(instance, value)
    serializer_obj(srs.Struct, dependencies=None)(
        context, instance, loc, top_spec)


def construct_action(instance):
    on_collection = docular.doc_spec_get(instance['on_collection'])
    value = {'on_collection': on_collection}
    docular.doc_spec_set(instance, value)


IMPORTEXPORT_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.action': construct_action,
    '.field.collection.django': list_constructor,
    '.field.*': no_constructor,
    '.field.struct': field_struct_constructor,
    '.field.string': serializer_obj(srs.String),
    '.field.serial': serializer_obj(srs.Serial),
    '.field.identity': serializer_obj(srs.Identity, dependencies=['root_url']),
    '.field.integer': serializer_obj(srs.Integer),
    '.field.float': serializer_obj(srs.Float),
    '.field.uuid': serializer_obj(srs.UUID),
    '.field.text': serializer_obj(srs.String),
    '.field.email': serializer_obj(srs.Email),
    '.field.boolean': serializer_obj(srs.Boolean),
    '.field.datetime': serializer_obj(srs.DateTime),
    '.field.date': serializer_obj(srs.Date),

    '.flag.*': no_constructor,
    '.flag.readonly': cerberus_flag('readonly'),
    '.flag.nullable': cerberus_flag('nullable'),
    '.meta': no_constructor,
    '.string': construct_string,
}, default=no_constructor)

    # _CONSTRUCTORS = {
    #     'ref':        Object(srs.Ref, kwargs_spec=True, kwargs_instance=True,
    #                          last=True, post_hook=_post_hook),
    #     'choices':    Object(srs.Choices, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'file':       Object(srs.File, kwargs_spec=True, kwargs_instance=True,
    #                          last=True, post_hook=_post_hook),
    #     'readonly':   Flag('readonly'),
    #     'writeonly':  Flag('writeonly'),
    #     'nullable':   Flag('nullable'),
    #     'default':    Dummy(),
    # }


class ImportExportData(BaseProcessor):
    """
    Base processor used for serialization purposes.

    It uses the Serializer classes provided by apimas and reads from
    specification to construct them accordingly.
    """
    def __init__(self, collection_loc, action_name, serializer, on_collection):
        self.serializer = serializer if on_collection else serializer.serializer


    def get_serializer(self, data, allowed_fields):
        # if allowed_fields is not None:
        #     serializers = self._get_serializers(allowed_fields)
        # else:

        return self.serializer

    def perform_serialization(self, context_data):
        raise NotImplementedError(
            'perform_serialization() must be implemented')

    def process(self, collection, url, action, context):
        """i
        Reads data which we want to serialize from context, it performs
        serialization on them and finally it saves output to context.
        """
        context_data = self.read(context)
        output = self.perform_serialization(context_data)
        if output is not None:
            self.write(output, context)


def check_field(allowed, field):
    while True:
        if field in allowed:
            return field
        splits = field.rsplit('/', 1)
        prefix = splits[0]
        if field == prefix:
            return False
        field = prefix
        continue


def check_field_permissions(allowed, write_data):
    if allowed is doc.ANY:
        return


def path_exists(doc, path):
    feed, trail, nodes = docular.doc_locate(doc, path)
    return not feed


class ImportDataProcessor(ImportExportData):
    """
    Processor responsible for the deserialization of data.
    """
    name = 'apimas.components.processors.DeSerialization'

    READ_KEYS = {
        'write_data': 'request/content',
        'parameters': 'request/meta/params',
        'can_read': 'permissions/can_read',
        'read_fields': 'permissions/read_fields',
        'can_write': 'permissions/write_fields',
        'write_fields': 'permissions/write_fields',
    }

    WRITE_KEYS = {
        'imported_content': 'imported/content',
    }

    def process_write_data(self, context_data):
        write_data = context_data['write_data']
        if not write_data:
            return None
        can_write = context_data['can_write']
        if not can_write:
            raise AccessDeniedError(
                'You do not have permission to do this action')

        can_write_fields = context_data['write_fields']
        return self.serializer.deserialize(write_data, can_write_fields)

    def perform_serialization(self, context_data):
        imported_content = self.process_write_data(context_data)
        return {'imported_content': imported_content}


ImportData = ProcessorConstruction(
    IMPORTEXPORT_CONSTRUCTORS, ImportDataProcessor)


class ExportDataProcessor(ImportExportData):
    """
    Processor responsible for the serialization of data.
    """
    name = 'apimas.components.processors.Serialization'

    READ_KEYS = {
        'export_data': 'exportable/content',
        'can_read': 'permissions/can_read',
        'read_fields': 'permissions/read_fields',
    }

    WRITE_KEYS = {
        'data': 'response/content',
    }

    def perform_serialization(self, context_data):
        export_data = context_data['export_data']
        if export_data is None:
            return None
        can_read = context_data['can_read']
        if not can_read:
            raise AccessDeniedError(
                'You do not have permission to do this action')

        can_read_fields = context_data['read_fields']
        return {'data': self.serializer.serialize(export_data, can_read_fields)}


ExportData = ProcessorConstruction(
    IMPORTEXPORT_CONSTRUCTORS, ExportDataProcessor)
