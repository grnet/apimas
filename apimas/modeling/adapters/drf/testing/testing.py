import random
from urlparse import urlparse
from django.test import override_settings
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from apimas.modeling.adapters.drf.utils import get_package_module
from apimas.modeling.adapters.drf.django_rest import DjangoRestAdapter
from apimas.modeling.adapters.drf.testing import utils


TEST_CASE_FUNCTIONS = [
    'list',
    'retrieve',
    'delete',
    'create',
    'update',
    'partial_update'
]


def _add_test_functions(cls, adapter):
    """
    This method creates test functions for every collection and action
    according to the spec.

    Each test function is added to the `ApimasTestCase` class given as
    parameter.

    :param cls: `ApimasTestCase` class to which test functions will be added.
    :param adapter: Adapter which descripes APIMAS spec.
    """
    structural_elements = adapter.get_structural_elements(
        adapter.adapter_spec)
    for collection, _ in adapter.adapter_spec.get(
            structural_elements[0]).iteritems():
        func = getattr(cls, 'validate_crud_action')
        for func_name in TEST_CASE_FUNCTIONS:
            function = get_collection_test_method(collection, func_name)(func)
            test_case_func_name = 'test_%s_%s' % (func_name, collection)
            if not hasattr(cls, test_case_func_name):
                setattr(cls, test_case_func_name, function)


def get_collection_test_method(collection, action):
    """ Get a test function, customized based on a collection and action. """
    def wrapper(func):
        def method(self):
            return func(self, collection, action)
        return method
    return wrapper


def _add_urlpatterns(module, urls):
    """ Add generated urls to the module given as parameter. """
    module = get_package_module(module)
    setattr(module, 'urlpatterns', [urls])


def set_apimas_context(urlconf_module, spec):
    """
    This function (decorator) is used to customize `TestCase` classes based
    on the `APIMAS` spec of an application.

    More specifically, the given spec is used in order `Django` urls to be
    created and then test functions (triggering test case scenarios for
    every collection and action) are created and bound to the provided
    `TestCase` class.

    :param urlconf_module: Path to the module where generated django urls
    will be added.
    :param spec: `APIMAS` specification.
    """

    def wrapper(cls):
        setattr(cls, 'spec', spec)
        adapter = DjangoRestAdapter()
        adapter.construct(spec)
        adapter.apply()
        setattr(cls, 'adapter', adapter)
        urls = adapter.urls
        _add_urlpatterns(urlconf_module, urls)
        _add_test_functions(cls, adapter)
        return override_settings(ROOT_URLCONF=urlconf_module)(cls)
    return wrapper


class ApimasTestCase(APITestCase):
    """
    Class triggering all test scenarios corresponding to the collections and
    their actions based on a `APIMAS` specification.
    """
    STATUS_CODES = {
        'list': status.HTTP_200_OK,
        'retrieve': status.HTTP_200_OK,
        'create': status.HTTP_201_CREATED,
        'delete': status.HTTP_204_NO_CONTENT,
        'update': status.HTTP_200_OK,
        'partial_update': status.HTTP_200_OK,
    }

    WRITABLE_ACTIONS = {
        'create',
        'update',
        'partial_update',
    }

    RESOURCE_ACTIONS = {
        'retrieve',
        'delete',
        'update',
        'partial_update',
    }

    ACTIONS_TO_METHODS = {
        'list': 'get',
        'retrieve': 'get',
        'create': 'post',
        'delete': 'delete',
        'update': 'put',
        'partial_update': 'patch',
    }

    ACTIONS_TO_SPEC = {
        'list': '.list',
        'retrieve': '.retrieve',
        'create': '.create',
        'delete': '.delete',
        'update': '.update',
        'partial_update': '.update',
    }

    SETUP_METHOD_NAME_PATTERN = 'setUp_%s_%s'

    VALIDATE_RE_METHOD_NAME_PATTERN = 'validate_response_%s_%s'

    REQUEST_CONTEXT_METHOD_PATTERN = 'request_context_%s_%s'

    AUTHENTICATE_METHOD_PATTERN = 'authenticate_%s'

    def setUp(self):
        self.models = self.adapter.models

        # A dictionary keyed by each collection which contains the created
        # instance which refer to that collection.
        self.collection_instances = {}

    def setUp_collection(self, collection, action):
        """
        Setup a test scenario for a particular collection and action.

        A model instance corresponding to the model associated with the
        provided collection is created along with its dependencies.

        In case of the `create` action, the instances of the dependencies
        are created only.
        """
        method_name = self.AUTHENTICATE_METHOD_PATTERN % (collection)
        authentication_method = getattr(self, method_name, None)
        if authentication_method is not None:
            authentication_method(collection)
        if action == 'create':
            # We do not need to create an instance corresponding to the
            # specified collection, but only instances of the dependencies.
            self.collection_instances = self.create_instances(
                collection, excluded_models=[self.models.get(collection)])
        else:
            self.collection_instances = self.create_instances(collection)
        return self.collection_instances.get(collection)

    def _get_response_type(self, action):
        """ Get expected response type based on the action. """
        if action == 'list':
            return list
        elif action == 'delete':
            return type(None)
        else:
            return dict

    def _validate_response_content(self, response_data, response_spec,
                                   msg_prefix=''):
        """
        It validates that the response_data follow the given response spec,
        e.g. a field is incuded on the response data.
        """
        if isinstance(response_data, dict):
            self._validate_response(
                response_data, response_spec, msg_prefix=msg_prefix)
        else:
            # Assert that every element of the list has the expected structure
            # according to the spec.
            for obj in response_data:
                self._validate_response(obj, response_spec,
                                        msg_prefix=msg_prefix)

    def assert_response_content(self, status_code, expected_status_code,
                                data, expected_structure, msg_prefix=''):
        """
        Assert that a response returns the expected status code and the
        structure of response data are according to the specification, e.g.
        it has the expected type and it includes the desired properties.

        It fails if at least one of the above is not validated.
        """
        if not isinstance(expected_structure, tuple) and len(
                expected_structure) != 2:
            raise ValueError('expected_structure must be in the form of '
                             '(response_type, response_structure)')

        msg = ('Response status codes are not equal, %s != %s.'
               ' Response content: %s' % (
                   status_code, expected_status_code, data))
        self.assertEqual(status_code, expected_status_code,
                         msg=msg_prefix + msg)
        response_type, response_structure = expected_structure
        self.assertTrue(isinstance(data, response_type))
        if data is None:
            assert not response_structure, (
                'Response structure cannot be validated against empty data')
        else:
            self._validate_response_content(data, response_structure)

    def validate_response(self, collection, action, response,
                          data, response_spec, instances):
        """
        It validates that the server response is as expected. The status
        code and response structure are validated.

        If an action is not inlcuded on the spec, then
        `HTTP_405_METHOD_NOT_ALLOWED` is expected.

        If action is `delete`, then no response data are expected.
        """
        response_type = self._get_response_type(action)
        spec_action = self.ACTIONS_TO_SPEC[action]
        if not utils.action_exists(self.spec, collection, spec_action):
            self.assert_action_not_allowed(response)
            # If action is not specified on the spec, then it isn't allowed.
            return

        if action == 'delete':
            expected_structure = (response_type, None)
        else:
            expected_structure = (response_type, response_spec)
        self.assert_response_content(
            response.status_code, self.STATUS_CODES[action], response.data,
            expected_structure)

    def request_context(self, collection, action, instances):
        """
        Create request context in order test scenario to be triggered.

        URL, data, and content_type are needed to be provided.
        URL is constructed based on the collection and action. Data are
        populated randomly according to the spec, and content_type is specified
        according to the data content. For instance, if a file is going to
        be uploaded, then the content type denotes `multipart`, `json`
        otherwise.
        """
        content_type = 'json'
        if action not in self.RESOURCE_ACTIONS:
            url = self.get_collection_url(collection)
        else:
            instance = random.choice(instances)
            url = self.get_collection_url(collection, pk=instance.pk)
        if action not in self.WRITABLE_ACTIONS:
            return url, {}, content_type
        all_fields = action != 'partial_update'
        writable_fields = utils.get_required_fields(self.spec, collection)
        data = utils.populate_request(
            writable_fields, self.collection_instances, all_fields=all_fields)
        if any(isinstance(v, (InMemoryUploadedFile, file))
               for v in data.itervalues()):
            content_type = 'multipart'
        return url, data, content_type

    def create_instances(self, collection, excluded_models=None):
        """
        Create instance of the model associated with the collection model
        along with its dependencies.

        Models along with their dependencies are specifies, and then a
        topological sort algorithm is applied on the derived graph in order
        model to be created with the right sequence.
        """
        collections = [collection] + utils.get_ref_collections(
            self.spec, collection)
        models = {k: v for k, v in self.models.iteritems()
                  if k in collections}
        schema = utils.get_models_to_create(models.values())
        top_ordered_models = utils.topological_sort(schema)
        instances = {}
        collection_instances = {collection: []
                                for collection in models.iterkeys()}
        excluded = excluded_models or []
        for model in top_ordered_models:
            if model in excluded:
                continue
            instance = utils.populate_model(model, instances=instances)
            instances[model] = instance
            for collection, collection_model in models.iteritems():
                if model is collection_model:
                    collection_instances[collection].append(instance)
        return collection_instances

    def _validate_response(self, response_data, exposed_fields,
                           msg_prefix=''):
        """
        It validates that the response structure follows the response spec
        """
        self.assertTrue(isinstance(response_data, dict))
        for field, field_spec in exposed_fields.iteritems():
            msg = ('Field %s unexpectedly is not included in the'
                   ' response data %s' % (repr(field), response_data))
            self.assertIn(field, response_data, msg=msg)
            value = response_data.get(field)
            if '.struct' in field_spec:
                structure = field_spec.get('.struct')
                self.assert_structure_field(value, structure, '.struct',
                                            msg_prefix)
            elif '.structarray' in field_spec:
                structure = field_spec.get('.structarray')
                self.assert_structure_field(value, structure,
                                            '.structarray', msg_prefix)

    def assert_structure_field(self, value, structure,
                               structure_type, msg_prefix=''):
        """
        Asserts that the given value is structural and it matches with the
        given structure spec.
        """
        if structure_type not in ['.struct', '.structarray']:
            raise ValueError('`structure_type` must be `.struct|.structarray`')

        if structure == '.structarray':
            self.assertTrue(isinstance(value, list))
            for element in value:
                self._validate_response(element, structure,
                                        msg_prefix=msg_prefix)
        else:
            self.assertTrue(isinstance(value, dict))
            self._validate_response(value, structure, msg_prefix=msg_prefix)

    def assert_identity_field(self, value, collection, expected_pk,
                              msg_prefix=''):
        """
        It asserts that an identify has the right form, e.g. it corresponds
        to the endpoint of collection and it refers to the expected resource
        (defined by id).
        """
        msg = ('Identity field is not valid for collection %s or it does'
               ' not refer to the expected resource' % (collection))
        path = urlparse(value).path
        url = reverse(collection + '-detail', args=[expected_pk])
        self.assertEqual(url, path, msg=msg_prefix + msg)

    def assert_action_not_allowed(self, response):
        self.assertIn(response.status_code,
                      [status.HTTP_405_METHOD_NOT_ALLOWED,
                       status.HTTP_404_NOT_FOUND])

    def get_collection_url(self, collection, pk=None):
        """ It forms url based on the collection and given id. """
        structural_element = utils.get_structural_element(self.spec)
        loc = ('', structural_element, collection)
        if pk is not None:
            loc += (str(pk),)
        url = '/'.join(loc) + '/'
        return url

    def validate_crud_action(self, collection, action):
        """
        It triggers a test scenario for a particular collection and action.

        This scenario includes the `setup`, `request creation` and
        `response validation` stages.
        """
        method_name = self.SETUP_METHOD_NAME_PATTERN % (action, collection)
        setup_method = getattr(self, method_name, self.setUp_collection)
        instances = setup_method(collection, action)

        method_name = self.REQUEST_CONTEXT_METHOD_PATTERN % (
            action, collection)
        request_context = getattr(self, method_name, self.request_context)
        url, data, content_type = request_context(
            collection, action, instances=instances)
        client_method = getattr(self.client, self.ACTIONS_TO_METHODS[action])
        response = client_method(url, data=data, format=content_type)
        if action not in self.WRITABLE_ACTIONS:
            response_spec = utils.get_fields(self.spec, collection,
                                             excluded=['.writeonly'])
        else:
            response_spec = utils.get_required_fields(self.spec, collection)
        method_name = self.VALIDATE_RE_METHOD_NAME_PATTERN % (
            action, collection)
        validate_response = getattr(self, method_name,
                                    self.validate_response)
        validate_response(collection, action, response, data, response_spec,
                          instances)
