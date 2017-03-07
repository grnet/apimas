from requests.compat import urljoin
from apimas import documents as doc, exceptions as ex
from apimas.adapters.cookbooks import NaiveAdapter
from apimas.clients import ApimasClient, TRAILING_SLASH
from apimas.clients.extensions import (
    RefNormalizer, DateNormalizer, DateTimeNormalizer)


class ApimasClientAdapter(NaiveAdapter):
    ADAPTER_CONF = 'client_conf'

    # Map predicates to cerberus related validation rules.
    PROPERTY_MAPPING = {
        'blankable': 'empty',
        'nullable': 'nullable',
        'readonly': 'readonly',
        'required': 'required',
    }

    EXTRA_PARAMS = {
        '.string': {
            'max_length': {
                'default': 255,
                'map': 'maxlength',
            }
        },
        '.choices': {
            'allowed': {
                'default': [],
                'map': 'allowed',
            },
        },
    }

    TYPE_MAPPING = {
        'integer': 'integer',
        'serial': 'integer',
        'biginteger': 'integer',
        'float': 'float',
        'string': 'string',
        'text': 'string',
        'choices': 'choices',
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

    def get_client(self, endpoint, collection):
        """
        Retrieve client according to a collection and the endpoint to which
        it belongs.

        :raises: ApimasException if client is not found for the selected
        resource.
        """
        collection_name = endpoint + '/' + collection
        if collection_name not in self.clients:
            raise ex.ApimasException(
                'Client not found for collection {!r}'.format(collection_name))
        return self.clients[collection_name]

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
        collection = context.get('parent_name')
        endpoint = urljoin(
            self.root_url, TRAILING_SLASH.join([loc[0], collection]))
        endpoint += TRAILING_SLASH
        instance[self.ADAPTER_CONF] = schema
        client = ApimasClient(endpoint, schema)
        self.clients[loc[0] + '/' + collection] = client
        return instance

    def construct_field(self, instance, spec, loc, context):
        """
        Constructor of `.field` predicate.

        It constructs a dictionary corresponding to a cerberus validation
        schema along with all rules based on spec.
        """
        special_constructors = {
            '.date': self._construct_date_field,
            '.datetime': self._construct_date_field,
        }

        parent_name = context.get('parent_name')
        nested_structures = {'.struct', '.structarray'}
        field_type = self.extract_type(instance)
        if not field_type:
            raise ex.ApimasException(
                'You have to specify field type for field {!r}'.format(
                    parent_name))
        self.init_adapter_conf(instance)
        if field_type in nested_structures:
            return self.construct_nested_field(
                instance, spec, loc, context, field_type)
        method_name = special_constructors.get(field_type)
        if method_name is not None:
            return method_name(instance, spec, loc, context, field_type)
        extra_params = self.get_extra_params(instance, field_type)
        instance[self.ADAPTER_CONF].update(extra_params)
        return instance

    def _construct_date_field(self, instance, spec, loc, context,
                              predicate_type):
        """
        Adds extra configuration based on the parameters of constructor.

        Actually, it normalizes a date object to a string which follows the
        given date format.
        """
        normalizers = {
            '.date': (DateNormalizer, ['%Y-%m-%d']),
            '.datetime': (DateTimeNormalizer, ['%Y-%m-%dT%H:%M:%S']),
        }
        normalizer, default = normalizers.get(predicate_type)
        params = instance.get(predicate_type)
        date_formats = params.get('format', default)
        instance[self.ADAPTER_CONF].update(
            {'coerce': normalizer(string_formats=date_formats)})
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
