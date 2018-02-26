from django.db.models import Model
from django.db.models.query import QuerySet
from apimas import utils
from apimas_django import utils as django_utils
from apimas.components import BaseProcessor, ProcessorConstruction
import docular


REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='


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


def struct_constructor(instance, loc):
    source = docular.doc_spec_get(instance.get('source', {})) or loc[-1]
    spec = {
        'type': 'struct',
        'source': source,
    }
    value = {'spec': spec}
    docular.doc_spec_set(instance, value)


def collection_constructor(instance, loc, top_spec):
    model = docular.doc_spec_get(instance['model'])
    source = docular.doc_spec_get(instance.get('source', {}))
    bounds = get_bounds(loc, top_spec)
    subcollections = {}
    substructs = {}
    for field, field_value in docular.doc_spec_iter_values(instance['fields']):
        if field_value:
            field_spec = field_value['spec']
            field_type = field_spec['type']
            if field_type == 'collection':
                subcollections[field] = field_spec
            else:
                substructs[field] = field_spec
    spec = {
        'type': 'collection',
        'model': utils.import_object(model),
        'source': source,
        'bounds': bounds,
        'subcollections': subcollections,
        'substructs': substructs,
    }
    value = {'spec': spec}
    docular.doc_spec_set(instance, value)


DJANGEBASEHANDLER_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    {
        '.field.struct': struct_constructor,
        '.field.collection.django': collection_constructor,
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
        self.spec = spec
        # self.model = value['model']
        # self.bounds = value['bounds']


class CreateHandlerProcessor(DjangoBaseHandler):
    REQUIRED_KEYS = {
        'data',
    }

    def do_create(self, key, spec, data):
        model = spec['model']
        bounds = spec['bounds']
        if bounds:
            print "BOUNDS", bounds
            assert key
            bound = bounds[0]
            data[bound + '_id'] = key
        return model.objects.create(**data)

    def create_with(self, key, spec, data):
        recs = []
        subcollections = spec['subcollections']
        for subkey in data.keys():
            if subkey in subcollections:
                values = data.pop(subkey)
                recs.extend((subcollections[subkey], value)
                            for value in values)
        substructs = spec['substructs']
        for subkey in data.keys():
            if subkey in substructs:
                struct_data = data.pop(subkey)
                model = spec['model']
                field = model._meta.get_field(subkey)
                struct_instance = field.related_model.objects.create(
                    **struct_data)
                data[subkey] = struct_instance

        instance = self.do_create(key, spec, data)
        for rec in recs:
            self.create_with(instance.id, *rec)
        return instance

    def execute(self, context_data):
        """ Creates a new django model instance. """

        data = context_data['data']
        kwargs = context_data['kwargs']
        key = kwargs.get('id0')
        instance = self.create_with(key, self.spec, data)
        # if many:
        #     for k, v in many.iteritems():
        #         getattr(instance, k).add(*v)
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
        flts = {}
        prev = ''
        for i, bound in enumerate(bounds):
            prefix = (prev + '__') if prev else ''
            ref = prefix + bound
            flts[ref + '_id'] = kwargs['id' + str(i)]
            prev = ref

        objects = model.objects
        objects = prefetch_related(objects, self.spec['subcollections'])
        objects = select_related(objects, self.spec['substructs'])
        return (objects.filter(**flts),)


ListHandler = _django_base_construction(ListHandlerProcessor)


class RetrieveHandlerProcessor(DjangoBaseHandler):
    READ_KEYS = {
        'instance': 'store/instance',
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
        model = self.spec['model']
        objects = model.objects
        objects = prefetch_related(objects, self.spec['subcollections'])
        objects = select_related(objects, self.spec['substructs'])

        instance = django_utils.get_instance(objects, pk)
        return (instance,)


RetrieveHandler = _django_base_construction(RetrieveHandlerProcessor)


class UpdateHandlerProcessor(CreateHandlerProcessor):
    READ_KEYS = {
        'instance': 'store/instance',
    }
    READ_KEYS.update(DjangoBaseHandler.READ_KEYS)
    REQUIRED_KEYS = {
        'pk',
        'data',
    }

    def _update_obj(self, obj, data):
        for k, v in data.iteritems():
            setattr(obj, k, v)
        obj.save()
        return obj

    def execute(self, context_data):
        """
        Updates an existing model instance based on the data of request.
        """
        model = self.spec['model']
        pk = context_data['pk']
        data = context_data['data']
        instance = model.objects.get(pk=pk)
#        data, many = self._parse_ref(model, data)
        instance = self._update_obj(instance, data)
        # if many:
        #     for k, v in many.iteritems():
        #         getattr(instance, k).add(*v)
        return (instance,)


UpdateHandler = _django_base_construction(UpdateHandlerProcessor)


class DeleteHandlerProcessor(RetrieveHandlerProcessor):
    STATUS_CODE = 204
    READ_KEYS = {
        'instance': 'store/instance',
    }
    READ_KEYS.update(DjangoBaseHandler.READ_KEYS)
    CONTENT_TYPE = None
    REQUIRED_KEYS = {
        'pk',
    }

    def execute(self, context_data):
        """ Deletes an existing model instance. """
        instance = super(DeleteHandler, self).execute(
            collection, url, action, context_data)
        instance.delete()
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
