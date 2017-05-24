from copy import deepcopy
import json
import random
from urlparse import urljoin
from django.test import TestCase as DjangoTestCase
from django.test.client import MULTIPART_CONTENT
from django.core.files.uploadedfile import InMemoryUploadedFile
from apimas import documents as doc
from apimas.django import model_utils as mutils
from apimas.utils import utils
from apimas.django.generators import DjangoRequestGenerator

REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='


def _ref(spec, field_spec):
    refs = []
    ref = field_spec[REF]['to']
    endpoint, collection = tuple(ref.split('/'))
    refs.append(ref)
    refs.extend(get_ref_collections(spec, endpoint, collection))
    return refs


def _array_of(spec, field_spec):
    array_type = field_spec.get(ARRAY_OF)
    if REF in array_type:
        return _ref(spec, field_spec[ARRAY_OF])
    if STRUCT in array_type:
        return _get_refs(array_type.get(STRUCT), spec)
    return []


def _get_refs(field_schema, spec):
    refs = []
    for field, field_spec in field_schema.iteritems():
        if REF in field_spec:
            refs.extend(_ref(spec, field_spec))
        elif STRUCT in field_spec:
            refs.extend(_get_refs(field_spec.get(STRUCT), spec))
        elif ARRAY_OF in field_spec:
            refs.extend(_array_of(spec, field_spec))
    return refs


def get_ref_collections(spec, endpoint, collection):
    loc = (endpoint, collection, '*')
    field_schema = {k: v for k, v in doc.doc_get(spec, loc).iteritems()
                    if not k.startswith('.')}
    return _get_refs(field_schema, spec)


class TestCase(DjangoTestCase):

    EXPECTED_STATUS_CODES = [
        200,
        201,
        204
    ]

    def setUp(self):
        self.test_url = None
        self.request_kwargs = {}
        self.models = self.adapter.models
        self.spec = deepcopy(self.spec)

    def create_instances(self, endpoint, collection, excluded_models=None):
        """
        Create instance of the model associated with the collection model
        along with its dependencies.

        Models along with their dependencies are specifies, and then a
        topological sort algorithm is applied on the derived graph in order
        model to be created with the right sequence.
        """
        collections = [endpoint + '/' + collection] + get_ref_collections(
            self.spec, endpoint, collection)
        models = {k: v for k, v in self.models.iteritems()
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
            instance = mutils.populate_model(model, instances=instances)
            instances[model] = instance
            for collection, collection_model in models.iteritems():
                if model is collection_model:
                    collection_instances[collection].append(instance)
        return collection_instances

    def setUp_default(self, endpoint, collection, action, action_spec):
        """
        Setup a test scenario for a particular endpoint, collection and action.

        A model instance corresponding to the model associated with the
        provided collection (which belongs to a particular endpoint), is
        created along with its dependencies.

        In case of the `create` action, the instances of the dependencies
        are created only.

        Args:
            endpoint (str): Endpoint to which collection belongs.
            collection (str): Name of inspected collection.
            action (str): Name of action that is currenly tested.
            action_spec (dict): Dictionary acting as a descriptor of the
                action (e.g. http method, action url, subject).
        """
        if action == 'create':
            # We do not need to create an instance corresponding to the
            # specified collection, but only instances of the dependencies.
            full_collection_name = endpoint + '/' + collection
            self.collection_instances = self.create_instances(
                endpoint, collection,
                excluded_models=[self.models.get(full_collection_name)])
        else:
            self.collection_instances = self.create_instances(
                endpoint, collection)

    def _get_url(self, endpoint, collection, action_spec):
        slash = '/'
        iscollection = action_spec['iscollection']
        action_url = action_spec['url']
        instances = self.collection_instances.get(
            endpoint + slash + collection)
        url = slash.join(['', endpoint, collection, ''])
        pattern = '' if iscollection\
            else str(random.choice(instances).pk) + slash
        url = urljoin(url, pattern)
        if action_url and action_url != slash:
            url = urljoin(url, action_url.strip(slash) + slash)
        return url

    def _get_content_and_type(self, endpoint, collection, action_spec):
        # Create random data based on the spec.
        gen = DjangoRequestGenerator(
            doc.doc_get(self.spec, (endpoint, collection)),
            instances=self.collection_instances)
        data = gen.construct()
        if any(isinstance(v, (file, InMemoryUploadedFile))
               for v in data.itervalues()):
            return data, MULTIPART_CONTENT
        # It is not supported to create body for a GET request
        # by django client.
        if action_spec['method'] not in ['get', 'GET']:
            data = json.dumps(data)
        return data, 'application/json'

    def prepare_request_default(self, endpoint, collection, action,
                                action_spec):
        """
        Prepares a django request constructing all required arguments
        for the invocation of the client.

        Client needs:
            * A URL to make its call (`self.test_url` field).
            * Any valid arguments for the invocation, such as data or
             content type (`self.request_kwargs`).

        This method constructs randomly both the url and the arguments.

        Args:
            endpoint (str): Endpoint to which collection belongs.
            collection (str): Name of inspected collection.
            action (str): Name of action that is currenly tested.
            action_spec (dict): Dictionary acting as a descriptor of the
                action (e.g. http method, action url, subject).
        """
        self.test_url = self._get_url(
            endpoint, collection, action_spec)
        data, content_type = self._get_content_and_type(
            endpoint, collection, action_spec)
        self.request_kwargs.update({
            'data': data,
            'content_type': content_type,
        })

    def validate_response_default(self, endpoint, collection, action,
                                  action_spec, response):
        """
        Validates the response of the server.

        This method tests that the status code of the response is not an
        erroneus one.

        Args:
            endpoint (str): Endpoint to which collection belongs.
            collection (str): Name of inspected collection.
            action (str): Name of action that is currenly tested.
            action_spec (dict): Dictionary acting as a descriptor of the
                action (e.g. http method, action url, subject).
            response: Response object made by django client.
        """
        self.assertTrue(response.status_code in self.EXPECTED_STATUS_CODES)

    def _get_stage_method(self, property_name, dict_key):
        default_methods = {
            'SETUP': self.setUp_default,
            'REQUEST': self.prepare_request_default,
            'VALIDATE': self.validate_response_default,
        }
        methods_dict = getattr(self, property_name, None)
        default = default_methods[property_name]
        if methods_dict is None:
            return default
        return methods_dict.get(dict_key, default)

    def _template_test_case(self, endpoint, collection, action, action_spec):
        """
        It triggers a test scenario for a particular endpoint, collection and
        action.

        This scenario includes the `setup`, `request preparation` and
        `response validation` stages.
        """
        key = (endpoint, collection, action)
        setup_method = self._get_stage_method('SETUP', key)
        setup_method(endpoint, collection, action, action_spec)

        prepare_method = self._get_stage_method('REQUEST', key)
        prepare_method(endpoint, collection, action, action_spec)

        client_method = getattr(self.client, action_spec['method'].lower())
        response = client_method(self.test_url, **self.request_kwargs)

        validate_method = self._get_stage_method('VALIDATE', key)
        validate_method(endpoint, collection, action, action_spec, response)
