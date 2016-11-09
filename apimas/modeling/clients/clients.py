from cerberus import Validator
import requests
from requests.exceptions import HTTPError
from requests.compat import urljoin, quote
from apimas.modeling.core import documents as doc, exceptions as ex
from apimas.modeling.adapters.cookbooks import NaiveAdapter
from apimas.modeling.clients.auth import ApimasClientAuth
from apimas.modeling.clients.normalizers import RefNormalizer


TRAILING_SLASH = '/'


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
            raise ex.ApimasClientException(e)
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
        self.api_validator = Validator(self.validation_schema)
        self.auth = None

    @handle_exception
    def create(self, raise_exception=True, headers=None, data=None):
        """
        Method for the creation of resource according to the given data.

        Example: POST endpoint/
        """
        data = self.validate(data or {}, raise_exception)
        r = requests.post(self.endpoint, headers=headers, data=data,
                          auth=self.auth)
        return r

    @handle_exception
    def update(self, resource_id, raise_exception=True, headers=None,
               data=None):
        """
        Method for the update of resource according to the specified data.

        Example: PUT endpoint/<pk>/
        """
        data = self.validate(data or {}, raise_exception)
        r = requests.put(self.format_endpoint(resource_id), headers=headers,
                         data=data, auth=self.auth)
        return r

    @handle_exception
    def partial_update(self, resource_id, raise_exception=True, headers=None,
                       data=None):
        """
        Method for the partial update of resource, i.e. only a part of the
        resource's fields are updated.

        Example: PATCH endpoint/<pk>/
        """
        data = self.partial_validate(data or {}, raise_exception)
        r = requests.patch(self.format_endpoint(resource_id), headers=headers,
                           data=data, auth=self.auth)
        return r

    @handle_exception
    def list(self, raise_exception=True, headers=None, params=None):
        """
        Method for getting a list of identical resources. Query parameters
        are supported.

        Example: GET endpoint/
        """
        r = requests.get(self.endpoint, headers=headers, params=params,
                         auth=self.auth)
        return r

    @handle_exception
    def retrieve(self, resource_id, raise_exception=True, headers=None,
                 params=None):
        """
        Method for a single resource matched with the specified resource
        id given as parameter. Query parameters are supported.

        Example: GET endpoint/<pk>/
        """
        r = requests.get(self.format_endpoint(resource_id), headers=headers,
                         params=params, auth=self.auth)
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

    def partial_validate(self, data, raise_exception=True):
        """
        Validates data that are going to be sent for a partial update of a
        resource.

        Construct a cerberus schema validator by taking into consideration
        only the fields that are included in the request.

        :param raise_exception: True if an exception should be raised when
        validation fails.
        """
        partial_schema = {k: v for k, v in self.validation_schema.iteritems()
                          if k in data}
        validator = Validator(partial_schema)
        is_valid = validator.validate(data)
        if raise_exception and not is_valid:
            raise ex.ApimasClientException(validator.errors)
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
        'boolean': 'boolean',
        'date': 'date',
        'datetime': 'datetime',
        'struct': 'dict',
        'structarray': 'list',
        'ref': 'string',
    }

    PREDICATES = list(NaiveAdapter.PREDICATES) + ['.field']

    def __init__(self, root_url):
        self.root_url = root_url
        self.adapter_spec = None
        self.clients = {}

    def get_clients(self):
        return self.clients

    def get_client(self, resource):
        """
        Retrieve client according to resource name.

        :raises: ApimasException if client is not found for the selected
        resource.
        """
        if resource not in self.clients:
            raise ex.ApimasException(
                'Client not found for resource `%s`' % (resource))
        return self.clients[resource]

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
        nested_structures = {'.struct', '.structarray'}
        self.init_adapter_conf(instance)
        if '.ref' in instance:
            return self.construct_ref_field(instance, spec, loc, context)
        for k in nested_structures:
            if k in instance:
                return self.construct_nested_field(
                    instance, spec, loc, context, k)
        return instance

    def construct_ref_field(self, instance, spec, loc, context):
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
        ref = doc.doc_get(instance, ('.ref', 'to')).keys()[0]
        instance[self.ADAPTER_CONF].update(
            {'coerce': RefNormalizer(TRAILING_SLASH.join(
                (self.root_url, loc[0], ref, '')))})
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
        field_schema = {field_name: schema.get(self.ADAPTER_CONF, {})
                        for field_name, schema in doc.doc_get(
                            instance, ('*',)).iteritems()}
        instance[self.ADAPTER_CONF].update(
            bound_field[field_type](field_schema))
        return instance
