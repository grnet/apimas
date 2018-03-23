from django.db.models import Model, ProtectedError
from django.db.models.query import QuerySet
from apimas import utils
from apimas_django import utils as django_utils
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas.errors import ValidationError, AccessDeniedError
import docular


REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='

Nothing = type('Nothing', (), {'__repr__': lambda self: 'Nothing'})()


def no_constructor(instance):
    pass


def copy_constructor(instance):
    docular.doc_spec_set(instance,
                         dict(docular.doc_spec_iter(instance)))


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

    argdoc = instance.get('default')
    if argdoc:
        v = docular.doc_spec_get(argdoc, default=Nothing)
        if v is not Nothing:
            spec['default'] = v

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
        'data': 'imported/content',
    }

    WRITE_KEYS = (
        'backend/content',
    )

    REQUIRED_KEYS = {
    }

    def __init__(self, collection_loc, action_name, spec):
        self.collection_loc = collection_loc
        self.collection_name = collection_loc[-1]
        self.spec = spec
        # self.model = value['model']
        # self.bounds = value['bounds']


def check_write_flags(name, spec, value):
    flags = spec.get('flags', [])
    default = spec.get('default', Nothing)

    if 'readonly' in flags:
        if value is not Nothing:
            raise ValidationError("'%s': Field is readonly" % name)
        return Nothing

    if value is Nothing:
        value = default

    if value is Nothing:
        raise ValidationError("'%s': Field is required" % name)

    if value is None and 'nullable' not in flags:
        raise ValidationError("'%s': Field is not nullable" % name)

    return value


def check_update_flags(name, spec, value, full, instance):
    flags = spec.get('flags', [])
    default = spec.get('default', Nothing)

    if 'readonly' in flags:
        if value is not Nothing:
            raise ValidationError("'%s': Field is readonly" % name)
        return Nothing

    if full and value is Nothing:
        value = default

    if full and value is Nothing:
        raise ValidationError("'%s': Field is required" % name)

    if value is None and 'nullable' not in flags:
        raise ValidationError("'%s': Field is not nullable" % name)

    if value is not Nothing and 'writeonce' in flags and instance is not None:
        source = spec['source']
        stored_value = getattr(instance, source)
        if value != stored_value:
            raise ValidationError("'%s': Field is writeonce" % name)

    return value


def get_write_fields(subspecs, data):
    create_args = {}
    for field_name, field_spec in subspecs.iteritems():
        value = data.get(field_name, Nothing)
        value = check_write_flags(field_name, field_spec, value)
        source = field_spec['source']
        if value is not Nothing:
            create_args[source] = value

    return create_args


def get_update_fields(subspecs, data, full, instance):
    update_args = {}
    for field_name, field_spec in subspecs.iteritems():
        value = data.get(field_name, Nothing)
        value = check_update_flags(
            field_name, field_spec, value, full, instance)
        source = field_spec['source']
        if value is not Nothing:
            update_args[source] = value

    return update_args


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

    create_args.update(get_write_fields(spec['subfields'], data))

    print "CREATE_ARGS", create_args
    return model.objects.create(**create_args)


def defer_create_subcollections(spec, data):
    deferred = []
    for subname, subspec in spec['subcollections'].iteritems():
        subdata = data.get(subname, Nothing)
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
        subdata = data.get(subname, Nothing)
        struct_instance = create_resource(subname, subspec, subdata)
        if struct_instance is not Nothing:
            created[subsource] = struct_instance
    return created


def create_resource(name, spec, data, key=None):
    data = check_write_flags(name, spec, data)
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


def update_subcollections(spec, data, full, instance):
    for subname, subspec in spec['subcollections'].iteritems():
        subdata = data.get(subname, Nothing)
        subdata = check_update_flags(subname, spec, subdata, full, instance)
        if subdata is Nothing:
            continue
        delete_subcollection(instance.id, subspec)
        for elem in subdata:
            create_resource(subname, subspec, elem, key=instance.id)


def update_substructs(spec, data, full, instance):
    created = {}
    model = spec['model']
    for subname, subspec in spec['substructs'].iteritems():
        subsource = subspec['source']
        field = model._meta.get_field(subsource)
        struct_model = field.related_model
        subspec['model'] = struct_model
        subdata = data.get(subname, Nothing)
        subinstance = getattr(instance, subsource)
        if subinstance is None:
            struct_instance = create_resource(subname, subspec, subdata)
            if struct_instance is not Nothing:
                created[subsource] = struct_instance
        else:
            struct_instance = update_resource(
                subname, subspec, subdata, full, subinstance)
            if struct_instance is None:
                created[subsource] = None
    return created


def do_update(spec, data, instance, full, precreated=None):
    update_args = {}
    if precreated:
        update_args.update(precreated)

    model = spec['model']
    update_args.update(
        get_update_fields(spec['subfields'], data, full, instance))

    print "UPDATE ARGS", update_args
    for key, value in update_args.iteritems():
        setattr(instance, key, value)
    instance.save()
    return instance


def update_resource(name, spec, data, full, instance):
    data = check_update_flags(name, spec, data, full, instance)
    if data is Nothing:
        if full:
            raise ValidationError("'%s': Nothing to create" % name)
        else:
            return Nothing

    if data is None:
        print "DELETING instance", instance
        delete_instance(instance)
        return None

    update_subcollections(spec, data, full, instance)
    precreated = update_substructs(spec, data, full, instance)
    return do_update(spec, data, instance, full, precreated)


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


def get_model_instance(spec, pk, kwargs):
    model = spec['model']
    flts = get_bound_filters(spec['bounds'], kwargs)
    objects = model.objects.filter(**flts)
    objects = prefetch_related(objects, spec['subcollections'])
    objects = select_related(objects, spec['substructs'])
    return django_utils.get_instance(objects, pk)


class RetrieveHandlerProcessor(DjangoBaseHandler):
    READ_KEYS = {
        'instance': 'backend/content',
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


class PartialUpdateHandlerProcessor(DjangoBaseHandler):
    full = False
    READ_KEYS = {
        'instance': 'backend/content',
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
            self.collection_name, self.spec, data, self.full, instance)
        instance = get_model_instance(self.spec, pk, kwargs)
        return (instance,)


PartialUpdateHandler = _django_base_construction(PartialUpdateHandlerProcessor)


class FullUpdateHandlerProcessor(PartialUpdateHandlerProcessor):
    full = True


FullUpdateHandler = _django_base_construction(FullUpdateHandlerProcessor)


class DeleteHandlerProcessor(RetrieveHandlerProcessor):
    def execute(self, context_data):
        """ Deletes an existing model instance. """
        (instance,) = RetrieveHandlerProcessor.execute(self, context_data)
        delete_instance(instance)
        return None


DeleteHandler = _django_base_construction(DeleteHandlerProcessor)


class TokenAuthHandler(BaseProcessor):
    """
    Add handler for generating JWT tokens to authenticated parties.
    """
    READ_KEYS = {
        'headers': 'request/meta/headers',
    }

    def __init__(self, collection, spec, auth_method,
                 **meta):
        super(TokenAuthHandler, self).__init__(collection, spec, **meta)

        secret_key_extractor = meta.get('secret_key')
        if secret_key_extractor is None:
            raise InvalidInput('Secret key is missing')
        secret_key_extractor = utils.import_object(secret_key_extractor)
        assert callable(secret_key_extractor), 'Secret key must be a callable'

        self.auth_method = auth_method

        user_processor = meta.get('user_processor')
        if user_processor:
            self.user_processor = utils.import_object(user_processor)
            assert callable(self.user_processor), (
                '"user_processor" must be a callable')

        token_gen = meta.get('token_generator')
        if token_gen is None:
            raise InvalidInput('Token generator is required')
        self.token_gen = utils.import_object(token_gen)
        assert callable(self.token_gen), ('"token_gen" must be a callable')

    def process(self, collection, url, action, context):
        """
        Client is authenticated based on a specific authentication method,
        specified by `auth_method` and then generates a new JWT token.
        """
        context_data = self.read(context)
        user = self.auth_method.authenticate(context_data['headers'])
        if self.user_processor:
            user = self.user_processor(user)
        content = self.token_gen(user)
        return {
            'content': content,
            'meta': {
                'content_type': 'application/json',
                'status_code': 200,
            }
        }

    def handle_error(self, component, cmp_args, ex):
        # This handler maps only `UnauthorizedError` exceptions to status
        # codes.
        status_code = 401 if isinstance(ex, UnauthorizedError) else 500
        return {
            'content': {
                'details': ex.message,
            },
            'meta': {
                'content_type': 'application/json',
                'status_code': status_code,
                'headers': {
                    'WWW-Authenticate': getattr(
                        self.auth_method, 'AUTH_HEADERS', None)
                },
            }
        }
