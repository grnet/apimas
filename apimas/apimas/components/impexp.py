import docular
from apimas import converters as cnvs
from apimas import documents as doc
from apimas.errors import AccessDeniedError
from apimas.components import BaseProcessor, ProcessorConstruction


Null = object()

def get_meta(top_spec, loc, key):
    return docular.doc_spec_get(
        docular.doc_inherit2(top_spec, loc, ('.meta', key)))

FIELD_ARGS = ['default']


def converter_obj(cls, dependencies=None, extra_args=None):
    def constructor(context, instance, loc, top_spec, config):
        docular.construct_last(context)
        predicate = context['predicate']

        kwargs = docular.doc_spec_get(instance, default={}).get('args', {})

        for key in dependencies or []:
            kwargs[key] = docular.doc_spec_get(config[':'+key])

        extra_check = extra_args or []
        for field_arg in FIELD_ARGS + extra_check:
            argdoc = instance.get(field_arg)
            if argdoc:
                v = docular.doc_spec_get(argdoc, default=Null)
                if v is not Null:
                    kwargs[field_arg] = v

        converter = cls(**kwargs)
        value = {'converter': converter}
        docular.doc_spec_set(instance, value)
    return constructor


def cerberus_flag(flag):
    def constructor(instance, loc):
        value = docular.doc_spec_get(instance, default={})
        args = value.get('args', {})
        args[flag] = True
        value['args'] = args
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


def list_constructor(context, instance, loc, top_spec, config):
    predicate = context['predicate']

    value = docular.doc_spec_get(instance, default={})
    args = value.get('args', {})

    field_converters = dict(docular.doc_spec_iter_values(instance['fields']))
    resource_converter = cnvs.Struct(schema=field_converters)
    args['converter'] = resource_converter
    value['args'] = args

    docular.doc_spec_set(instance, value)
    converter_obj(cnvs.List, dependencies=None)(
        context, instance, loc, top_spec, config)


def field_struct_constructor(context, instance, loc, top_spec, config):
    value = docular.doc_spec_get(instance, default={})
    args = value.get('args', {})

    field_converters = dict(docular.doc_spec_iter_values(instance['fields']))
    args['schema'] = field_converters
    value['args'] = args

    docular.doc_spec_set(instance, value)
    converter_obj(cnvs.Struct, dependencies=None)(
        context, instance, loc, top_spec, config)


def construct_action(instance):
    on_collection = docular.doc_spec_get(instance['on_collection'])
    value = {'on_collection': on_collection}
    docular.doc_spec_set(instance, value)


IMPORTEXPORT_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.action': construct_action,
    '.field.collection.django': list_constructor,
    '.field.*': no_constructor,
    '.field.struct': field_struct_constructor,
    '.field.string': converter_obj(cnvs.String),
    '.field.serial': converter_obj(cnvs.Serial),
    '.field.identity': converter_obj(
        cnvs.Identity, dependencies=['root_url'], extra_args=['to']),
    '.field.ref': converter_obj(
        cnvs.Ref, dependencies=['root_url'], extra_args=['to']),
    '.field.integer': converter_obj(cnvs.Integer),
    '.field.float': converter_obj(cnvs.Float),
    '.field.uuid': converter_obj(cnvs.UUID),
    '.field.text': converter_obj(cnvs.String),
    '.field.email': converter_obj(cnvs.Email),
    '.field.boolean': converter_obj(cnvs.Boolean),
    '.field.datetime': converter_obj(cnvs.DateTime),
    '.field.date': converter_obj(cnvs.Date),
    '.field.file': converter_obj(cnvs.File),

    '.flag.*': no_constructor,
    '.flag.readonly': cerberus_flag('readonly'),
    '.flag.writeonly': cerberus_flag('writeonly'),
    '.flag.nullable': cerberus_flag('nullable'),
    '.meta': no_constructor,
    '.string': construct_string,
}, default=no_constructor)

    # _CONSTRUCTORS = {
    #     'ref':        Object(cnvs.Ref, kwargs_spec=True, kwargs_instance=True,
    #                          last=True, post_hook=_post_hook),
    #     'choices':    Object(cnvs.Choices, kwargs_spec=True,
    #                          kwargs_instance=True, last=True,
    #                          post_hook=_post_hook),
    #     'file':       Object(cnvs.File, kwargs_spec=True, kwargs_instance=True,
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
    def __init__(self, collection_loc, action_name, converter, on_collection):
        self.on_collection = on_collection
        self.converter = converter if on_collection else converter.converter


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
        'imported_filters': 'imported/filters',
        'imported_ordering': 'imported/ordering',
    }

    def process_filters(self, filters, can_read_fields):
        if not filters:
            return {}
        filter_data = {}
        operators = {}
        for param, value in filters.iteritems():
            parts = param.rsplit('__', 1)
            operator = parts[1] if len(parts) == 2 else None
            path = parts[0].split('.')
            docular.doc_set(operators, path, operator)
            docular.doc_set(filter_data, path, value)

        converter = self.converter
        if self.on_collection:
            converter = converter.converter

        imported_filters = converter.import_data(
            filter_data, can_read_fields, flat=True)
        return docular.doc_merge(operators, imported_filters)

    def process_ordering(self, ordering_param, can_read_fields):
        results = []
        if not ordering_param:
            return results
        orderings = ordering_param.split(',')
        for ordering in orderings:
            if ordering.startswith('-'):
                reverse = True
                ordering = ordering[1:]
            else:
                reverse = False

            path = ordering.split('.')
            if not docular.doc_get(can_read_fields, path):
                raise AccessDeniedError(
                    "You do not have permission to order by this field")
            results.append((path, reverse))
        return results

    def process_parameters(self, context_data):
        parameters = context_data['parameters']
        filters = {}
        ordering = None
        for param, value in parameters.iteritems():
            if param == 'ordering':
                ordering = value
                continue

            parts = param.split('__', 1)
            if len(parts) != 2:
                continue
            if parts[0] == 'flt':
                filters[parts[1]] = value

        read_fields = context_data['read_fields']
        imported_filters = self.process_filters(filters, read_fields)
        imported_ordering = self.process_ordering(ordering, read_fields)
        result = {}
        if imported_filters:
            result['imported_filters'] = imported_filters
        if imported_ordering:
            result['imported_ordering'] = imported_ordering

        return result

    def process_write_data(self, context_data):
        write_data = context_data['write_data']
        if not write_data:
            return write_data
        can_write = context_data['can_write']
        if not can_write:
            raise AccessDeniedError(
                'You do not have permission to write to this resource')

        can_write_fields = context_data['write_fields']
        return self.converter.import_data(write_data, can_write_fields)

    def execute(self, context_data):
        imported_content = self.process_write_data(context_data)
        imported_data = self.process_parameters(context_data)
        imported_data['imported_content'] = imported_content
        return imported_data


ImportData = ProcessorConstruction(
    IMPORTEXPORT_CONSTRUCTORS, ImportDataProcessor)


class ExportDataProcessor(ImportExportData):
    """
    Processor responsible for the serialization of data.
    """
    READ_KEYS = {
        'export_data': 'exportable/content',
        'can_read': 'permissions/can_read',
        'read_fields': 'permissions/read_fields',
    }

    WRITE_KEYS = (
        'response/content',
    )

    def execute(self, context_data):
        export_data = context_data['export_data']
        if export_data is None:
            return None
        can_read = context_data['can_read']
        if not can_read:
            raise AccessDeniedError(
                'You do not have permission to read this resource')

        can_read_fields = context_data['read_fields']
        exported_data = self.converter.export_data(
            export_data, can_read_fields)
        return (exported_data,)


ExportData = ProcessorConstruction(
    IMPORTEXPORT_CONSTRUCTORS, ExportDataProcessor)
