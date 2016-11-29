import requests
from requests.exceptions import HTTPError
from requests.compat import urljoin, quote
from apimas.modeling.core import documents as doc, exceptions as ex
from apimas.modeling.adapters.cookbooks import NaiveAdapter
from apimas.modeling.clients.auth import ApimasClientAuth
from apimas.modeling.clients.extensions import (
    RefNormalizer, DateNormalizer, DateTimeNormalizer, ApimasValidator)


TRAILING_SLASH = '/'


def get_subdocuments(document):
    """ Get documents that are elements of lists of a parent document. """
    subdocs = {}
    for k, v in document.iteritems():
        if isinstance(v, list):
            subs = filter((lambda x: isinstance(x, dict)), v)
            if subs:
                subdocs[k] = subs
        elif isinstance(v, dict):
            for key, value in get_subdocuments(v).iteritems():
                subdocs[k + '/' + key] = value
    return subdocs


def to_cerberus_paths(data):
    """
    This utility function creates the corresponding paths of a cerberus
    validation schema which are respondible for validating the given data.

    Example:
    data = {
        'foo': {
            'bar': 'value'
        },
        'bar': 'value'
    }

    paths = ['foo/schema/bar', 'bar']

    :param data: Dictionary of data.

    :returns: A list of paths.
    """
    if not data:
        return []
    cerberus_paths = []
    for k, v in data.iteritems():
        cerberus_nodes = [k]
        if isinstance(v, list):
            continue
        if isinstance(v, dict):
            nodes = to_cerberus_paths(v)
            for node in nodes:
                cerberus_paths.append(
                    '/'.join((cerberus_nodes + ['schema', node])))
        else:
            cerberus_paths.append('/'.join(cerberus_nodes))
    return cerberus_paths


def handle_exception(func):
    """
    Handler of exceptions raised due to the response status codes.
    It catches them it raised an appropriate `ApimasClientException`.
    """
    def wrapper(*args, **kwargs):
        try:
            r = func(*args, **kwargs)
            if kwargs.pop('raise_exception', True):
                r.raise_for_status()
            return r
        except HTTPError as e:
            raise ex.ApimasClientException(
                e.message, response=e.response, request=e.request)
    return wrapper


class ApimasClient(object):
    """
    A class which defines a client for specific resource.
    All CRUD operations are supported.

    Typically, the initialization of the resource client requires the
    location of this resource to the web, resource specification and
    credentials if the resource is protected.

    TODO: Support additional actions.
    """

    def __init__(self, endpoint, schema, **credentials):
        self.endpoint = endpoint
        self.validation_schema = schema
        self.api_validator = ApimasValidator(self.validation_schema)
        self.auth = None

    @handle_exception
    def create(self, raise_exception=True, headers=None, data=None):
        """
        Method for the creation of resource according to the given data.

        Example: POST endpoint/
        """
        request_kwargs = {
            'headers': headers,
            'auth': self.auth,
        }
        request_kwargs.update(self.extract_write_data(data, raise_exception))
        r = requests.post(self.endpoint, **request_kwargs)
        return r

    @handle_exception
    def update(self, resource_id, raise_exception=True, headers=None,
               data=None):
        """
        Method for the update of resource according to the specified data.

        Example: PUT endpoint/<pk>/
        """
        request_kwargs = {
            'headers': headers,
            'auth': self.auth,
        }
        data = self.validate(data or {}, raise_exception)
        request_kwargs.update(self.extract_write_data(data, raise_exception))
        r = requests.put(self.format_endpoint(resource_id), **request_kwargs)
        return r

    @handle_exception
    def partial_update(self, resource_id, raise_exception=True, headers=None,
                       data=None):
        """
        Method for the partial update of resource, i.e. only a part of the
        resource's fields are updated.

        Example: PATCH endpoint/<pk>/
        """
        request_kwargs = {
            'headers': headers,
            'auth': self.auth,
        }
        request_kwargs.update(self.extract_write_data(
            data, raise_exception, partial=True))
        r = requests.patch(self.format_endpoint(resource_id), **request_kwargs)
        return r

    @handle_exception
    def list(self, raise_exception=True, headers=None, params=None, data=None):
        """
        Method for getting a list of identical resources. Query parameters
        are supported.

        Example: GET endpoint/
        """
        r = requests.get(self.endpoint, headers=headers, params=params,
                         auth=self.auth, json=data)
        return r

    @handle_exception
    def retrieve(self, resource_id, raise_exception=True, headers=None,
                 params=None, data=None):
        """
        Method for a single resource matched with the specified resource
        id given as parameter. Query parameters are supported.

        Example: GET endpoint/<pk>/
        """
        r = requests.get(self.format_endpoint(resource_id), headers=headers,
                         params=params, auth=self.auth, json=data)
        return r

    @handle_exception
    def delete(self, resource_id, raise_exception=True, headers=None):
        """
        Method for the deletion of a specific resource.

        Example: DELETE endpoint/<pk>/
        """
        r = requests.delete(
            self.format_endpoint(resource_id), auth=self.auth,
            headers=headers)
        return r

    @handle_exception
    def head(self, resource_id=None, headers=None):
        """
        Method for making a HTTP HEAD request on a specific endpoint.
        """
        endpoint = self.endpoint if resource_id is None else\
            self.format_endpoint(resource_id)
        r = requests.head(endpoint, headers=headers, auth=self.auth)
        return r

    @handle_exception
    def options(self, headers=None):
        """
        Method for making a HTTP OPTIONS request on resource's endpoint.
        """
        r = requests.options(self.endpoint, headers=headers, auth=self.auth)
        return r

    def format_endpoint(self, resource_id):
        """
        This method concatenates the resource's endpoint with a specified
        identifier.

        Example: endpoint/<pk>/
        """
        return urljoin(self.endpoint, quote(
            str(resource_id))) + TRAILING_SLASH

    def _validate_subdata(self, data, schema, raise_exception):
        """
        This function partially validates subdata of request.

        Subdata are considered nested data which are elements of lists.

        Example:

        data = {
            'foo': [
                {'foo': 'value'},
                {'bar': 'value'},
            ]
        }

        This function partial validates them according to their specified
        fields.

        :returns: A dictionary of validated subdata, with the path of their
        location to the parent document as keys.
        """
        subdocs = get_subdocuments(data)
        validated = {}
        for k, v in subdocs.iteritems():
            path = k.split('/')
            cerberus_path = []
            for u in path:
                cerberus_path.extend([u, 'schema'])
            subdata = doc.doc_pop(data, path)
            subschema = doc.doc_pop(schema, cerberus_path[:-1]) or {}
            subschema = subschema.get('schema', {}).get('schema', {})
            if not subschema:
                raise ex.ApimasClientException(
                    'Field `%s` cannot be validated' % (str(tuple(path))))
            validated_docs = []
            for subdoc in subdata:
                validated_docs.append(self.partial_validate(
                    subdoc, raise_exception, subschema))
            validated[tuple(path)] = validated_docs
        return validated

    def partial_validate(self, data, raise_exception=True, schema=None):
        """
        Validates data that are going to be sent for a partial update of a
        resource.

        Construct a cerberus schema validator by taking into consideration
        only the fields that are included in the request.

        :param raise_exception: True if an exception should be raised when
        validation fails.
        """
        schema = schema or self.validation_schema
        cerberus_paths = to_cerberus_paths(data)
        validated_subdocs = self._validate_subdata(
            data, schema, raise_exception)
        partial_schema_paths = {
            path: doc.doc_get(schema, path.split('/'))
            for path in cerberus_paths}
        partial_schema = doc.doc_from_ns(partial_schema_paths)
        validator = ApimasValidator(partial_schema)
        is_valid = validator.validate(data)
        if raise_exception and not is_valid:
            raise ex.ApimasClientException(validator.errors)
        for k, v in validated_subdocs.iteritems():
            doc.doc_set(validator.document, k, v)
        return validator.document

    def validate(self, data, raise_exception=True):
        """
        Validates data that are going to be sent using a cerberus validation
        schema.

        :param raise_exception: True if an exception should be raised when
        validation fails.
        """
        is_valid = self.api_validator.validate(data)
        if raise_exception and not is_valid:
            raise ex.ApimasClientException(self.api_validator.errors)
        return self.api_validator.document

    def extract_files(self, data):
        """
        This functions checks if data which are going to be sent to request
        include files and it extract them.

        Then it performs two checks:
        a) It checks that the location of files is not nested.
        b) If files were detected, then it checks that request data does
        not include nested data.

        When uploading files, the `Content-Type` header of request is set
        to `multipart/form-data`.

        :param data: Dictionary of data which are going to be sent to request.

        :returns: A dictionary keyed by the name of the field and it includes
        all files to be uploaded.
        """
        paths = [path for path, val in doc.doc_iter(data)
                 if isinstance(val, file)]
        error_msg = ('Content-Type `application/json is not supported when'
                     ' uploading files`')
        if any(len(path) > 1 for path in paths):
            raise ex.ApimasClientException(error_msg)
        if paths and any(isinstance(v, (list, dict))
                         for _, v in data.iteritems()):
            raise ex.ApimasClientException(error_msg)
        return {path[-1]: doc.doc_pop(data, path) for path in paths}

    def extract_write_data(self, data, raise_exception, partial=False):
        """
        This function extracts data, sent for CREATE and UPDATE requests of
        a resource.

        This functions validates data, and then it seperates files to be
        uploaded from the rest.

        If files are present, then the `Content-Type` of request is set to
        `multipart/form-data`, otherwise `application/json`.

        :param data: Dictionary of data which are going to be sent to request.
        :param raise_exception: True if an exception should be raised when
        validation fails.
        :param partial: True if request includes a subset of resource's fields,
        False otherwise.
        """
        if partial:
            data = self.partial_validate(data or {}, raise_exception)
        else:
            data = self.validate(data or {}, raise_exception)
        files = self.extract_files(data)
        return {'data': data, 'files': files} if files else {'json': data}

    def set_credentials(self, auth_type, **credentials):
        """
        Set credentials to interact with the endpoint (
            If resource is protected) based on the selected auth type.
        """
        self.auth = ApimasClientAuth(auth_type, **credentials)


class ApimasClientAdapter(NaiveAdapter):
    ADAPTER_CONF = 'client_conf'

    # Map predicates to cerberus related validation rules.
    PROPERTY_MAPPING = {
        'blankable': 'empty',
        'nullable': 'nullable',
        'readonly': 'readonly',
        'required': 'required',
    }

    TYPE_MAPPING = {
        'integer': 'integer',
        'serial': 'integer',
        'biginteger': 'integer',
        'float': 'float',
        'string': 'string',
        'email': 'email',
        'boolean': 'boolean',
        'date': 'string',
        'datetime': 'string',
        'struct': 'dict',
        'structarray': 'list',
        'ref': 'string',
        'file': 'file',
    }

    SKIP_FIELDS = {'.identity'}

    PREDICATES = list(NaiveAdapter.PREDICATES) + ['.field']

    def __init__(self, root_url):
        self.root_url = root_url
        self.adapter_spec = None
        self.clients = {}

    def get_clients(self):
        return self.clients

    def get_client(self, collection):
        """
        Retrieve client according to resource name.

        :raises: ApimasException if client is not found for the selected
        resource.
        """
        if collection not in self.clients:
            raise ex.ApimasException(
                'Client not found for resource `%s`' % (collection))
        return self.clients[collection]

    def apply(self):
        """
        Apply generated cerberus specification and create `ApimasClient`
        objects for every resource defined in the specification.
        """
        if not self.adapter_spec:
            raise ex.ApimasException(
                'Cannot create clients from an empty spec')

        structural_elements = self.get_structural_elements(self.adapter_spec)
        assert len(structural_elements) == 1
        for collection, spec in doc.doc_get(
                self.adapter_spec, (structural_elements[0],)).iteritems():
            schema = spec.get(self.ADAPTER_CONF, {})
            endpoint = urljoin(
                self.root_url, TRAILING_SLASH.join(
                    [structural_elements[0], collection]))
            endpoint += TRAILING_SLASH
            self.clients[collection] = ApimasClient(endpoint, schema)

    def construct_collection(self, instance, spec, loc, context):
        """
        Constructor for `.collection` predicate.

        This constructor aims to aggregate the cerberus validation schemas
        for every single field defined by the collection.
        """
        instance = super(self.__class__, self).construct_collection(
            instance, spec, loc, context)
        self.init_adapter_conf(instance)
        schema = {field_name: schema.get(self.ADAPTER_CONF, {})
                  for field_name, schema in doc.doc_get(
                      instance, ('*',)).iteritems()}
        instance[self.ADAPTER_CONF] = schema
        return instance

    def construct_field(self, instance, spec, loc, context):
        """
        Constructor of `.field` predicate.

        It constructs a dictionary corresponding to a cerberus validation
        schema along with all rules based on spec.
        """
        def default(instance, spec, loc, context, **kwargs):
            return instance

        parent_name = context.get('parent_name')
        nested_structures = {'.struct', '.structarray'}
        field_type = self.extract_type(instance)
        if not field_type:
            raise ex.ApimasException(
                'You have to specify field type for field `%s`' % (
                    parent_name))
        self.init_adapter_conf(instance)
        if field_type in nested_structures:
            return self.construct_nested_field(
                instance, spec, loc, context, field_type)
        method_name = '_add_' + field_type[1:] + '_params'
        params = doc.doc_get(instance, (field_type,))
        return getattr(self, method_name, default)(
            instance, spec, loc, context, **params)

    def _add_date_params(self, instance, spec, loc, context, **kwargs):
        """
        Adds extra configuration based on the parameters of constructor.

        Actually, it normalizes a date object to a string which follows the
        given date format.
        """
        date_format = kwargs.pop('format', None)
        instance[self.ADAPTER_CONF].update(
            {'coerce': DateNormalizer(date_format)})
        return instance

    def _add_datetime_params(self, instance, spec, loc, context, **kwargs):
        """
        Adds extra configuration based on the parameters of constructor.

        Actually, it normalizes a date object to a string which follows the
        given datetime format.
        """
        date_format = kwargs.pop('format', None)
        instance[self.ADAPTER_CONF].update(
            {'coerce': DateTimeNormalizer(date_format)})
        return instance

    def construct_ref(self, instance, spec, loc, context):
        """
        Construct a field that refes to another collection.

        It sets a normalization rule so that it converts an value to the
        corresponding url location of the referenced collection. Actually,
        this value indicates the id of the referenced collection.

        Example:
        value: my_value --> normalized: http://<root_url>/<loc>/my_value/

        where loc is the location where referenced collection is placed at,
        joined by trailing slash `/`.

        This normalization is triggered before every cerberus validation.
        """
        instance = super(self.__class__, self).construct_ref(
            instance, spec, loc, context)
        many = spec.get('many')
        ref = spec.get('to')
        normalizer = {'coerce': RefNormalizer(TRAILING_SLASH.join(
            (self.root_url, loc[0], ref, '')))}
        instance[self.ADAPTER_CONF].update(normalizer)
        if many is True:
            conf = {'type': 'list', 'schema': instance[self.ADAPTER_CONF]}
            instance[self.ADAPTER_CONF] = conf
        return instance

    def construct_nested_field(self, instance, spec, loc, context,
                               field_type=None):
        """
        Constructor for predicates that include nested schemas. Typically,
        `.struct` and `.structarray` predicates are included in this category
        of fields.

        This constructor generates the corresponding cerberus syntax for having
        a `list` of dicts or a `dict` in accordance to the aforementioned
        structures.
        """
        bound_field = {
            '.struct': lambda x: {'type': 'dict', 'schema': x},
            '.structarray': lambda x: {'type': 'list', 'schema': {
                'type': 'dict', 'schema': x}}
        }
        params = doc.doc_get(instance, (field_type,))
        field_schema = {field_name: schema.get(self.ADAPTER_CONF, {})
                        for field_name, schema in params.iteritems()}
        instance[self.ADAPTER_CONF].update(
            bound_field[field_type](field_schema))
        return instance

    def construct_writeonly(self, instance, spec, loc, context):
        return instance
