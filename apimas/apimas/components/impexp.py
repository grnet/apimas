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

        kwargs = {}
        for key in dependencies or []:
            kwargs[key] = get_meta(top_spec, loc, key)

        pred_instance = instance[predicate]
        pred_kwargs = dict(docular.doc_spec_iter_values(pred_instance)) \
                      if pred_instance else {}

        kwargs.update(pred_kwargs)
        serializer = cls(**kwargs)
        value = {'serializer': serializer, 'map_to': loc[-1]}
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


def resource_constructor(context, instance, loc):
    docular.construct_last(context)
    predicate = context['predicate']

    kwargs = dict(docular.doc_spec_iter(instance))

    pred_instance = instance[predicate]
    pred_kwargs = dict(docular.doc_spec_iter_values(pred_instance)) \
                  if pred_instance else {}
    kwargs.update(pred_kwargs)
    v = dict(docular.doc_spec_iter_values(instance))
    serializer = srs.Struct(v, **kwargs)
    value = {'serializer': serializer}
    docular.doc_spec_set(instance, value)


def list_constructor(context, instance, loc):
    v = docular.doc_spec_get(instance['fields'])
    resource_serializer = v['serializer']
    serializer = srs.List(resource_serializer)
    value = {'serializer': serializer,
             'resource_serializer': resource_serializer,
             'map_to': loc[-1]}
    docular.doc_spec_set(instance, value)


def field_struct_constructor(context, instance, loc):
    v = docular.doc_spec_get(instance['fields'])
    serializer = v['serializer']
    value = {'serializer': serializer, 'map_to': loc[-1]}
    return docular.doc_spec_set(instance, value)


def construct_action(instance):
    on_collection = docular.doc_spec_get(instance['on_collection'])
    value = {'on_collection': on_collection}
    docular.doc_spec_set(instance, value)


IMPORTEXPORT_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.action': construct_action,
    '.resource': resource_constructor,
    '.field.collection.django': list_constructor,
    '.field.*': no_constructor,
    '.field.struct': field_struct_constructor,
    '.field.string': serializer_obj(srs.String),
    '.field.serial': serializer_obj(srs.Serial),
    '.field.identity': serializer_obj(srs.Identity, dependencies=['root_url']),
    '.field.integer': serializer_obj(srs.Integer),
    '.flag.*': no_constructor,
    '.flag.readonly': cerberus_flag('readonly'),
    '.flag.nullable': cerberus_flag('nullable'),
    '.meta': no_constructor,
    '.string': construct_string,
}, default=no_constructor)

    # _CONSTRUCTORS = {
    #     'ref':        Object(srs.Ref, kwargs_spec=True, kwargs_instance=True,
    #                          last=True, post_hook=_post_hook),
    #     'serial':     Object(srs.Serial, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'integer':    Object(srs.Integer, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'float':      Object(srs.Float, kwargs_spec=True, kwargs_instance=True,
    #                          last=True, post_hook=_post_hook),
    #     'string':     Object(srs.String, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'uuid':       Object(srs.UUID, kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'text':       Object(srs.String, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'choices':    Object(srs.Choices, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'email':      Object(srs.Email, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'boolean':    Object(srs.Boolean, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'datetime':   Object(srs.DateTime, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          kwargs_spec_mapping={'format': 'date_format'},
    #                          post_hook=_post_hook),
    #     'date':       Object(srs.Date, kwargs_spec=True, kwargs_instance=True,
    #                          kwargs_spec_mapping={'format': 'date_format'},
    #                          last=True, post_hook=_post_hook),
    #     'file':       Object(srs.File, kwargs_spec=True, kwargs_instance=True,
    #                          last=True, post_hook=_post_hook),
    #     'identity':   Object(srs.Identity, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'struct':     Object(srs.Struct, args_spec=True,
    #                          args_spec_name='schema', kwargs_instance=True,
    #                          last=True, post_hook=_post_hook),
    #     'array of':   Object(srs.List, args_spec=True,
    #                          args_spec_name='serializer', kwargs_instance=True,
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
    def __init__(self, collection_loc, action_name,
                 serializer, resource_serializer, map_to, on_collection):
        self.serializer = serializer if on_collection else resource_serializer


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
