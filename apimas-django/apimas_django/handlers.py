from django.db.models import ProtectedError
from apimas import utils
from apimas_django import utils as django_utils
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas.errors import AccessDeniedError, InvalidInput
import docular


REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='

Nothing = type('Nothing', (), {'__repr__': lambda self: 'Nothing'})()


def no_constructor(instance):
    pass


def get_bounds(loc, top_spec):
    bounds = []
    working_loc = loc
    while len(working_loc) >= 2:
        bound = docular.doc_spec_get(
            docular.doc_get(top_spec, working_loc + ('bound',)))
        if bound is None:
            break
        bounds.append(bound)
        working_loc = working_loc[:-2]
    return bounds


def get_sub_elements(instance):
    subcollections = {}
    substructs = {}
    subfields = {}
    for field, field_value in docular.doc_spec_iter_values(instance['fields']):
        if field_value:
            field_spec = field_value['spec']
            field_type = field_spec['type']
            if field_type == 'collection':
                subcollections[field] = field_spec
            elif field_type == 'struct':
                substructs[field] = field_spec
            elif field_type == 'regular':
                subfields[field] = field_spec
    return subcollections, substructs, subfields


def struct_constructor(context, instance, loc):
    docular.construct_last(context)
    value = docular.doc_spec_get(instance)
    spec = value['spec']

    source = docular.doc_spec_get(instance.get('source', {})) or loc[-1]
    subcollections, substructs, subfields = get_sub_elements(instance)
    spec['type'] = 'struct'
    spec['source'] = source
    spec['subcollections'] = subcollections
    spec['substructs'] = substructs
    spec['subfields'] = subfields
    docular.doc_spec_set(instance, value)


def collection_constructor(context, instance, loc, top_spec):
    docular.construct_last(context)
    value = docular.doc_spec_get(instance, default={})
    spec = value.get('spec', {})

    model = docular.doc_spec_get(instance['model'])
    source = docular.doc_spec_get(instance.get('source', {}))
    bounds = get_bounds(loc, top_spec)
    subcollections, substructs, subfields = get_sub_elements(instance)

    spec['type'] = 'collection'
    spec['model'] = utils.import_object(model)
    spec['source'] = source
    spec['bounds'] = bounds
    spec['subcollections'] = subcollections
    spec['substructs'] = substructs
    spec['subfields'] = subfields
    value['spec'] = spec
    docular.doc_spec_set(instance, value)


def field_constructor(instance, loc):
    value = docular.doc_spec_get(instance, default={})
    spec = value.get('spec', {})
    spec['type'] = 'regular'
    source = docular.doc_spec_get(instance.get('source', {}))
    spec['source'] = source if source else loc[-1]

    def_doc = docular.doc_spec_get(instance, 'default', default=Nothing)
    deffn_doc = docular.doc_spec_get(
        instance, 'default_fn', default=Nothing)

    if def_doc is not Nothing and deffn_doc is not Nothing:
        raise InvalidInput("Multiple default values given")

    if def_doc is not Nothing:
        spec['default'] = lambda: def_doc
    elif deffn_doc is not Nothing:
        fn = utils.import_object(deffn_doc)
        spec['default'] = fn

    value['spec'] = spec
    docular.doc_spec_set(instance, value)


def construct_flag(flag):
    def constructor(instance, loc):
        value = docular.doc_spec_get(instance, default={})
        spec = value.get('spec', {})
        flags = spec.get('flags', [])
        flags.append(flag)
        spec['flags'] = flags
        value['spec'] = spec
        docular.doc_spec_set(instance, value)
    return constructor


DJANGEBASEHANDLER_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    {
        '.field.*': field_constructor,
        '.field.struct': struct_constructor,
        '.field.collection.django': collection_constructor,
        '.flag.readonly': construct_flag('readonly'),
        '.flag.writeonly': construct_flag('writeonly'),
        '.flag.nullable': construct_flag('nullable'),
    },
    default=no_constructor)


def _django_base_construction(action):
    return ProcessorConstruction(
        DJANGEBASEHANDLER_CONSTRUCTORS, action)


class DjangoBaseHandler(BaseProcessor):
    """
    Base handler for django specific actions.

    This handler requires a django model to either read or write data. This
    handler assumes that there is an interaction with django models, e.g.
    a query, an insertion, etc.

    This handler extracts the following data from context:
        * `model`: Django model with which handler interacts.
        * `data`: A dictionary representing data of request (if any).
        * `pk`: Primary key of the resource if handler operates on a specific
                model instance, e.g. update.

    The final response of the handler is a dictionary of kwargs needed by
    APIMAS in order response can be constructed later. This includes:
        * `content`: A `django.db.models.Model` or
            `django.db.models.query.QuerySet` instance.
        * `content_type`: Content type of response, e.g. `application/json`.
        * `status_code`: Status code of response, e.g. 201.


    Django base handler also offers a hook (i.e. method `execute()`) where
    other handlers can execute arbitrary code. It is the actual
    interaction with the django models, where a model instance or a QuerySet
    is expected as the output of this hook.

    Attributes:
        name (str): The identifier of this handler.
        READ_KEYS (dict): Human readable keys which are mapped to the actual
            keys of context from which processor reads.
        REQUIRED_KEYS (set): Required keys for the adapter.

    Examples:
        A very simple handler that uses Django BaseHandler is the following
        which operates on resources. It takes the django model and pk as
        specified by the request and the corresponding model instance.

        >>> from apimas.errors import InvalidInput
        >>> from apimas_django.handlers import BaseHandler
        >>> class MyHandler(BaseHandler):
        ...     name = 'myapp.mymodule.MyHandler'
        ...     def execute(self, collection, url, action, context_data):
        ...        model = context_data['model']
        ...        pk = context_data.get('pk')
        ...        if pk is None:
        ...            raise InvalidInput('Handler operates on resources.')
        ...        return model.objects.get(pk=pk)
    """
    READ_KEYS = {
        'kwargs': 'request/meta/kwargs',
        'pk': 'request/meta/kwargs/pk',
        'data': 'backend/input',
    }

    WRITE_KEYS = (
        'backend/raw_response',
    )

    REQUIRED_KEYS = {
    }

    def __init__(self, collection_loc, action_name, spec, post_handler):
        self.collection_loc = collection_loc
        self.collection_name = collection_loc[-1]
        self.spec = spec
        self.post_handler = utils.import_object(post_handler) \
                            if post_handler else None

    def process(self, context):
        context_data = self.read(context)
        output = self.execute(context_data)
        if output is not None:
            self.write(output, context)

        if self.post_handler:
            raw_response = context.extract('backend/raw_response')
            self.post_handler(raw_response, context)


def get_fields(subspecs, data):
    create_args = {}
    for field_name, field_spec in subspecs.iteritems():
        source = field_spec['source']
        value = data.get(source, Nothing)
        if value is not Nothing:
            create_args[source] = value

    return create_args


def get_bound_name(spec):
    bounds = spec.get('bounds')
    if bounds:
        bound = bounds[0]
        return bound + '_id'
    return None


def do_create(key, spec, data, precreated=None):
    create_args = {}
    if precreated:
        create_args.update(precreated)

    model = spec['model']
    bound_name = get_bound_name(spec)
    if bound_name is not None:
        assert key
        create_args[bound_name] = key

    create_args.update(get_fields(spec['subfields'], data))

    print "CREATE_ARGS", create_args
    return model.objects.create(**create_args)


def defer_create_subcollections(spec, data):
    deferred = []
    for subname, subspec in spec['subcollections'].iteritems():
        subsource = subspec['source']
        subdata = data.get(subsource, Nothing)
        if subdata is Nothing:
            continue
        deferred.extend((subname, subspec, elem) for elem in subdata)
    return deferred


def create_substructs(spec, data):
    created = {}
    model = spec['model']
    for subname, subspec in spec['substructs'].iteritems():
        subsource = subspec['source']
        field = model._meta.get_field(subsource)
        struct_model = field.related_model
        subspec['model'] = struct_model
        subdata = data.get(subsource, Nothing)
        struct_instance = create_resource(subname, subspec, subdata)
        if struct_instance is not Nothing:
            created[subsource] = struct_instance
    return created


def create_resource(name, spec, data, key=None):
    if data is Nothing:
        return Nothing

    if data is None:
        return None

    deferred = defer_create_subcollections(spec, data)
    precreated = create_substructs(spec, data)
    instance = do_create(key, spec, data, precreated)
    for args in deferred:
        create_resource(*args, key=instance.id)
    return instance


def delete_subcollection(key, spec):
    model = spec['model']
    bound_name = get_bound_name(spec)
    assert bound_name is not None
    flt = {bound_name: key}
    print "DELETING for", flt
    delete_queryset(model.objects.filter(**flt))


def update_subcollections(spec, data, instance):
    for subname, subspec in spec['subcollections'].iteritems():
        subsource = subspec['source']
        subdata = data.get(subsource, Nothing)
        if subdata is Nothing:
            continue
        delete_subcollection(instance.id, subspec)
        for elem in subdata:
            create_resource(subname, subspec, elem, key=instance.id)


def update_substructs(spec, data, instance):
    created = {}
    model = spec['model']
    for subname, subspec in spec['substructs'].iteritems():
        subsource = subspec['source']
        field = model._meta.get_field(subsource)
        struct_model = field.related_model
        subspec['model'] = struct_model
        subdata = data.get(subsource, Nothing)
        subinstance = getattr(instance, subsource)
        if subinstance is None:
            struct_instance = create_resource(subname, subspec, subdata)
            if struct_instance is not Nothing:
                created[subsource] = struct_instance
        else:
            struct_instance = update_resource(
                subname, subspec, subdata, subinstance)
            if struct_instance is None:
                created[subsource] = None
    return created


def do_update(spec, data, instance, precreated=None):
    update_args = {}
    if precreated:
        update_args.update(precreated)

    update_args.update(get_fields(spec['subfields'], data))

    print "UPDATE ARGS", update_args
    for key, value in update_args.iteritems():
        setattr(instance, key, value)
    instance.save()
    return instance


def update_resource(name, spec, data, instance):
    if data is Nothing:
        return Nothing

    if data is None:
        print "DELETING instance", instance
        delete_instance(instance)
        return None

    update_subcollections(spec, data, instance)
    precreated = update_substructs(spec, data, instance)
    return do_update(spec, data, instance, precreated)


def delete_instance(instance):
    try:
        instance.delete()
    except ProtectedError:
        raise AccessDeniedError('Deleting this resource is forbidden')


def delete_queryset(queryset):
    try:
        queryset.delete()
    except ProtectedError:
        raise AccessDeniedError('Deleting these resources is forbidden')


class CreateHandlerProcessor(DjangoBaseHandler):
    REQUIRED_KEYS = {
        'data',
    }

    def execute(self, context_data):
        """ Creates a new django model instance. """

        data = context_data['data']
        kwargs = context_data['kwargs']
        key = kwargs.get('id0')
        instance = create_resource(
            self.collection_name, self.spec, data, key=key)
        return (instance,)


CreateHandler = _django_base_construction(CreateHandlerProcessor)


def select_related(objects, substructs):
    for key, value in substructs.iteritems():
        source = value['source']
        if source:
            objects = objects.select_related(source)
    return objects


def prefetch_related(objects, subcollections):
    for key, value in subcollections.iteritems():
        source = value['source']
        if source:
            objects = objects.prefetch_related(source)
    return objects


def get_bound_filters(bounds, kwargs):
    flts = {}
    prev = ''
    for i, bound in enumerate(bounds):
        prefix = (prev + '__') if prev else ''
        ref = prefix + bound
        flts[ref + '_id'] = kwargs['id' + str(i)]
        prev = ref
    return flts


class ListHandlerProcessor(DjangoBaseHandler):
    REQUIRED_KEYS = {
    }

    def execute(self, context_data):
        """
        Gets all django model instances based on the orm model extracted
        from request context.
        """
        model = self.spec['model']
        bounds = self.spec['bounds']
        kwargs = context_data['kwargs']
        flts = get_bound_filters(bounds, kwargs)

        objects = model.objects
        objects = prefetch_related(objects, self.spec['subcollections'])
        objects = select_related(objects, self.spec['substructs'])
        return (objects.filter(**flts),)


ListHandler = _django_base_construction(ListHandlerProcessor)


def get_model_instance(spec, pk, kwargs, filters=None):
    model = spec['model']
    bound_filters = get_bound_filters(spec['bounds'], kwargs)
    objects = model.objects.filter(**bound_filters)
    if filters:
        objects = objects.filter(*filters)
    objects = prefetch_related(objects, spec['subcollections'])
    objects = select_related(objects, spec['substructs'])
    return django_utils.get_instance(objects, pk)


class RetrieveHandlerProcessor(DjangoBaseHandler):
    READ_KEYS = {
        'instance': 'backend/instance',
    }
    READ_KEYS.update(DjangoBaseHandler.READ_KEYS)
    REQUIRED_KEYS = {
        'pk',
    }

    def execute(self, context_data):
        """
        Gets a single model instance which based on the orm model and
        resource ID extracted from request context.
        """
        pk = context_data['pk']
        kwargs = context_data['kwargs']
        instance = context_data['instance']
        if not instance:
            instance = get_model_instance(self.spec, pk, kwargs)
        return (instance,)


RetrieveHandler = _django_base_construction(RetrieveHandlerProcessor)


class UpdateHandlerProcessor(DjangoBaseHandler):
    READ_KEYS = {
        'instance': 'backend/instance',
    }
    READ_KEYS.update(DjangoBaseHandler.READ_KEYS)
    REQUIRED_KEYS = {
        'pk',
        'data',
    }

    def execute(self, context_data):
        """
        Updates an existing model instance based on the data of request.
        """
        pk = context_data['pk']
        kwargs = context_data['kwargs']
        data = context_data['data']
        instance = context_data['instance']
        if not instance:
            instance = get_model_instance(self.spec, pk, kwargs)

        update_resource(
            self.collection_name, self.spec, data, instance)
        instance = get_model_instance(self.spec, pk, kwargs)
        return (instance,)


UpdateHandler = _django_base_construction(UpdateHandlerProcessor)


class DeleteHandlerProcessor(RetrieveHandlerProcessor):
    def execute(self, context_data):
        """ Deletes an existing model instance. """
        (instance,) = RetrieveHandlerProcessor.execute(self, context_data)
        delete_instance(instance)
        return None


DeleteHandler = _django_base_construction(DeleteHandlerProcessor)
