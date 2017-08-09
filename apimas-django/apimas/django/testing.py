from collections import namedtuple
from copy import deepcopy
import json
import random
from urlparse import urljoin
from django.test import TestCase as DjangoTestCase
from django.test.client import MULTIPART_CONTENT, RequestFactory, Client
from django.core.files.uploadedfile import InMemoryUploadedFile
from apimas import documents as doc
from apimas.errors import InvalidInput
from apimas.django import model_utils as mutils
from apimas.utils import utils
from apimas.django.generators import DjangoRequestGenerator

REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='


def _ref(spec, field_spec, excluded):
    refs = []
    ref = field_spec[REF]['to']
    if ref not in excluded:
        excluded.append(ref)
        refs.append(ref)
        refs.extend(get_ref_collections(spec, ref, excluded))
    return refs


def _array_of(spec, field_spec, excluded):
    array_type = field_spec.get(ARRAY_OF)
    if REF in array_type:
        return _ref(spec, field_spec[ARRAY_OF], excluded)
    if STRUCT in array_type:
        return _get_refs(array_type.get(STRUCT), spec, excluded)
    return []


def _get_refs(field_schema, spec, excluded):
    refs = []
    for field, field_spec in field_schema.iteritems():
        if REF in field_spec:
            refs.extend(_ref(spec, field_spec, excluded))
        elif STRUCT in field_spec:
            refs.extend(_get_refs(field_spec.get(STRUCT), spec, excluded))
        elif ARRAY_OF in field_spec:
            refs.extend(_array_of(spec, field_spec, excluded))
    return refs


def get_ref_collections(spec, collection, excluded=None):
    excluded = excluded or []
    endpoint, _, collection = collection.partition('/')
    loc = (endpoint, collection, '*')
    field_schema = {k: v for k, v in doc.doc_get(spec, loc).iteritems()
                    if not k.startswith('.')}
    return _get_refs(field_schema, spec, excluded)


def get_url(context, instances):
    """
    Construct URL to make a call to a collection or a resource of
    a collection.

    Args:
        context (apimas.django.testing.TestingContext): Context
        instances (dict): A dictionary of lists which contains all created
            model instances per collection.

    Returns:
        str: URL which matches to the specified collection and action.
    """
    slash = '/'
    iscollection = context.iscollection
    action_url = context.action_url
    if not iscollection and not instances:
        raise InvalidInput('There is not any instance for {!r}'.format(
            context.collection))
    url = slash.join(['', context.collection, ''])
    pattern = '' if iscollection\
        else str(random.choice(instances).pk) + slash
    url = urljoin(url, pattern)
    if action_url and action_url != slash:
        url = urljoin(url, action_url.strip(slash) + slash)
    return url


def get_content_and_type(context, instances):
    """
    Creates random data and specifies content type accordingly.

    Args:
        context (apimas.django.testing.TestingContext): Context
        instances (dict): A dictionary of lists which contains all created
            model instances per collection.
    """
    # Create random data based on the spec.
    gen = DjangoRequestGenerator(
        doc.doc_get(context.spec, tuple(context.collection.rsplit('/', 1))),
        instances=instances, **context.spec.get('.meta', {}))
    data = gen.construct()
    if any(isinstance(v, (file, InMemoryUploadedFile))
           for v in data.itervalues()):
        return data, MULTIPART_CONTENT
    # It is not supported to create body for a GET request
    # by django client.
    if context.action_method not in ['get', 'GET']:
        data = json.dumps(data)
    return data, 'application/json'


def create_collection_instances(collection, spec, models,
                                excluded_models=None):
    """
    Create an instance of the model associated with a collection.

    Models along with their dependencies are extracted, and then a
    topological sort algorithm is applied on the derived graph in order
    required dependencies to be created with the right order..
    """
    collections = [collection] + get_ref_collections(spec, collection)
    models = {k: v for k, v in models.iteritems()
              if k in collections}
    schema = mutils.get_models_to_create(models.values())
    top_ordered_models = utils.topological_sort(schema)
    instances = {}
    collection_instances = {collection: []
                            for collection in models.iterkeys()}
    excluded = excluded_models or []
    for model in top_ordered_models:
        if model in excluded:
            continue
        instance = mutils.populate_random_model(model, instances=instances)
        instances[model] = instance
        for collection, collection_model in models.iteritems():
            if model is collection_model:
                collection_instances[collection].append(instance)
    return collection_instances


def setUp_default(context):
    """
    Setup a test scenario for a particular endpoint, collection and action.

    A model instance corresponding to the model associated with the
    provided collection (which belongs to a particular endpoint), is
    created along with its dependencies.

    In case of the `create` action, the instances of the dependencies
    are created only.

    Args:
        context (apimas.django.testing.TestingContext): Context

    Returns:
        dict: A dictonary of lists which contains the created model instances
            per collection.
    """
    if context.action == 'create':
        # We do not need to create an instance corresponding to the
        # specified collection, but only instances of the dependencies.
        return create_collection_instances(
            context.collection, context.spec, context.models,
            excluded_models=[context.models.get(context.collection)])
    else:
        return create_collection_instances(
            context.collection, context.spec, context.models)


def prepare_request_default(context, instances):
    """
    Prepares a django request constructing all required arguments
    for the invocation of the client.

    Client needs:
        * A URL to make its call.
        * Any valid arguments for the invocation, such as data or
         content type.

    This method constructs randomly both the url and the arguments.

    Args:
        context (apimas.django.testing.TestingContext): Context
        instances (dict): A dictionary of lists which contains all created
            model instances per collection.

    Returns:
        str: A URL for the call.
        dict: Keyword arguments for the invocation of the django test client.
    """
    test_url = get_url(context, instances.get(context.collection))
    data, content_type = get_content_and_type(context, instances)
    request_kwargs = {
        'data': data,
        'content_type': content_type,
    }
    return test_url, request_kwargs


def validate_response_default(test_obj, context, instances, response):
    """
    Validates the response of the server.

    This method tests that the status code of the response is not an
    erroneus one.

    Args:
        test_obj: Instance of TestCase class.
        context (apimas.django.testing.TestingContext): Context
        instances (dict): A dictionary of lists which contains all created
            model instances per collection.
        response: Response of django test client.
    """
    expected_status_codes = [
        200,
        201,
        204,
    ]
    test_obj.assertTrue(response.status_code in expected_status_codes)


TESTING_CONTEXT_PARAMS = [
    'collection',
    'action',
    'iscollection',
    'action_method',
    'action_url',
    'adapter',
    'models',
    'spec',
]
TestingContext = namedtuple('TestingContext', TESTING_CONTEXT_PARAMS)


class ApimasRequestFactory(RequestFactory):
    def put(self, path, data='', content_type='application/octet-stream',
            secure=False, **extra):
        data = self._encode_data(data, content_type)
        return super(ApimasRequestFactory, self).put(path, data, content_type,
                                                     secure, **extra)


class TestClient(ApimasRequestFactory, Client):
    pass


class TestCase(DjangoTestCase):
    client_class = TestClient

    def setUp(self):
        self.test_url = None
        self.request_kwargs = {}
        self.models = self.adapter.models
        self.context = {
            'spec': deepcopy(self.spec),
            'models': self.adapter.models,
            'adapter': self.adapter,
        }

    def _get_stage_method(self, property_name, dict_key):
        default_methods = {
            'SETUP': setUp_default,
            'REQUEST': prepare_request_default,
            'VALIDATE': validate_response_default,
        }
        methods_dict = getattr(self, property_name, None)
        default = default_methods[property_name]
        if methods_dict is None:
            return default
        return methods_dict.get(dict_key, default)

    def _create_testing_context(self, endpoint, collection, action,
                                action_spec):
        return TestingContext(
            collection=endpoint + '/' + collection,
            action=action,
            iscollection=action_spec['iscollection'],
            action_url=action_spec['url'],
            action_method=action_spec['method'],
            spec=self.spec,
            adapter=self.adapter,
            models=self.models,
        )

    def _template_test_case(self, endpoint, collection, action, action_spec):
        """
        It triggers a test scenario for a particular endpoint, collection and
        action.

        This scenario includes the `setup`, `request preparation` and
        `response validation` stages.
        """
        context = self._create_testing_context(
            endpoint, collection, action, action_spec)
        key = (endpoint, collection, action)
        setup_method = self._get_stage_method('SETUP', key)
        instances = setup_method(context)

        prepare_method = self._get_stage_method('REQUEST', key)
        test_url, kwargs = prepare_method(context, instances)

        client_method = getattr(self.client, action_spec['method'].lower())
        response = client_method(test_url, **kwargs)

        validate_method = self._get_stage_method('VALIDATE', key)
        validate_method(self, context, instances, response)
