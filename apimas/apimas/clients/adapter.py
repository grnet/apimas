import copy
import json
from requests.compat import urljoin
from apimas import documents as doc, utils
from apimas.decorators import last
from apimas.errors import (
    AdapterError, ConflictError, InvalidInput, InvalidSpec, NotFound)
from apimas.adapters.cookbooks import NaiveAdapter
from apimas.adapters.actions import extract_from_action, ApimasAction
from apimas.clients import ApimasClient, TRAILING_SLASH, Client
from apimas.clients.extensions import (
    RefNormalizer, DateNormalizer, DateTimeNormalizer)
from apimas.components import BaseHandler


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

        :raises: NotFound if client is not found for the selected
        collection.
        """
        collection_name = endpoint + '/' + collection
        if collection_name not in self.clients:
            raise NotFound(
                'Client not found for collection {!r}'.format(collection_name))
        return self.clients[collection_name]

    def construct_collection(self, context):
        """
        Constructor for `.collection` predicate.

        This constructor aims to aggregate the cerberus validation schemas
        for every single field defined by the collection.
        """
        instance = super(self.__class__, self).construct_collection(
            context)
        self.init_adapter_conf(instance)
        schema = {field_name: schema.get(self.ADAPTER_CONF, {})
                  for field_name, schema in doc.doc_get(
                      instance, ('*',)).iteritems()}
        collection = context.parent_name
        endpoint = urljoin(
            self.root_url, TRAILING_SLASH.join([context.loc[0], collection]))
        endpoint += TRAILING_SLASH
        instance[self.ADAPTER_CONF] = schema
        client = ApimasClient(endpoint, schema)
        self.clients[context.loc[0] + '/' + collection] = client
        return instance

    def construct_field(self, context):
        """
        Constructor of `.field` predicate.

        It constructs a dictionary corresponding to a cerberus validation
        schema along with all rules based on spec.
        """
        special_constructors = {
            '.date': self._construct_date_field,
            '.datetime': self._construct_date_field,
        }

        parent_name = context.parent_name
        nested_structures = {'.struct', '.structarray'}
        field_type = self.extract_type(context.instance)
        if not field_type:
            raise InvalidSpec(
                'You have to specify field type for field {!r}'.format(
                    parent_name))
        self.init_adapter_conf(context.instance)
        if field_type in nested_structures:
            return self.construct_nested_field(
                context, field_type)
        method_name = special_constructors.get(field_type)
        if method_name is not None:
            return method_name(context, field_type)
        extra_params = self.get_extra_params(context.instance, field_type)
        context.instance[self.ADAPTER_CONF].update(extra_params)
        return context.instance

    def _construct_date_field(self, context, predicate_type):
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
        params = context.instance.get(predicate_type)
        date_formats = params.get('format', default)
        context.instance[self.ADAPTER_CONF].update(
            {'coerce': normalizer(string_formats=date_formats)})
        return context.instance

    def construct_ref(self, context):
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
            context)
        many = context.spec.get('many')
        ref = context.spec.get('to')
        normalizer = {'coerce': RefNormalizer(TRAILING_SLASH.join(
            (self.root_url, context.loc[0], ref, '')))}
        instance[self.ADAPTER_CONF].update(normalizer)
        if many is True:
            conf = {'type': 'list', 'schema': instance[self.ADAPTER_CONF]}
            instance[self.ADAPTER_CONF] = conf
        return instance

    def construct_nested_field(self, context, field_type=None):
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
        # Concatenate '=' because we have compound predicates.
        params = doc.doc_get(context.instance, (field_type + '=',))
        field_schema = {field_name: schema.get(self.ADAPTER_CONF, {})
                        for field_name, schema in params.iteritems()}
        context.instance[self.ADAPTER_CONF].update(
            bound_field[field_type](field_schema))
        return context.instance

    def construct_writeonly(self, context):
        return context.instance


class ClientHandler(BaseHandler):
    READ_KEYS = {
        'session': 'request/meta/session',
        'native': 'request/native',
        'data': 'request/meta/data',
        'headers': 'request/meta/headers',
        'files': 'request/meta/files',
        'params': 'request/meta/params',
    }

    def prepare_request(self, request, request_context):
        headers = request_context['headers']
        files = request_context['files']
        data = request_context['data']
        content_type = headers.get('Content-Type')
        if content_type is None:
            if not files:
                headers['Content-Type'] = 'application/json'
            else:
                headers['Content-Type'] = 'multipart/form-data'

        if headers['Content-Type'] == 'application/json':
            data = json.dumps(data)

        # Update native request object.
        request.data = data
        request.headers = headers
        request.files = files
        request.params = request_context['params']
        return request.prepare()

    def process(self, collection, url, action, context):
        handler_data = self.read(context)
        session = handler_data.get('session')
        if session is None:
            raise InvalidInput('"session" object is None')
        native_request = handler_data['native']
        if native_request is None:
            raise InvalidInput('"request" object is None')

        prepared_request = self.prepare_request(native_request, handler_data)
        response = session.send(prepared_request)
        return {
            'content': response.content,
            'native': response,
            'meta': {
                'status_code': response.status_code,
                'headers': response.headers,
                'cookies': response.cookies,
            }
        }

    def handle_error(self, processor, processor_args, ex):
        raise ex


def _iscollection(loc):
    return loc[-2] != '*'


def _get_collection_action(action_name, action_content,
                           collection_path, action_url, method):
    url_segments = collection_path + (action_url,)

    def action(self, content=None, params=None, headers=None):
        url = utils.urljoin(self.root_url, *url_segments)
        return self._request(url, method, action_content, content, params,
                             headers)

    setattr(action, '__name__', action_name)
    return action


def _get_resource_action(action_name, action_content, collection_path,
                         action_url, method):

    def action(self, pk, content=None, params=None, headers=None):
        url_segments = collection_path + (str(pk), action_url)
        url = utils.urljoin(self.root_url, *url_segments)
        return self._request(url, method, action_content, content, params,
                             headers)

    setattr(action, '__name__', action_name)
    return action


class ClientAdapter(object):
    AUTOMATED_ACTIONS = {
        'create': {
            'method': 'POST',
            'url': '/',
            'pre': [
            ],
            'post': [
            ],
            'handler': 'apimas.clients.adapter.ClientHandler',
        },
        'list': {
            'method': 'GET',
            'url': '/',
            'pre': [
            ],
            'post': [
            ],
            'handler': 'apimas.clients.adapter.ClientHandler',
        },
        'retrieve': {
            'method': 'GET',
            'url': '/',
            'pre': [
            ],
            'post': [
            ],
            'handler': 'apimas.clients.adapter.ClientHandler',
        },
        'update': {
            'method': 'PUT',
            'url': '/',
            'pre': [
            ],
            'post': [
            ],
            'handler': 'apimas.clients.adapter.ClientHandler',
        },
        'partial_update': {
            'method': 'PATCH',
            'url': '/',
            'pre': [
            ],
            'post': [
            ],
            'handler': 'apimas.clients.adapter.ClientHandler',
        },
        'delete': {
            'method': 'DELETE',
            'url': '/',
            'pre': [
            ],
            'post': [
            ],
            'handler': 'apimas.clients.adapter.ClientHandler',
        },
    }

    def __init__(self):
        self._constructors = {
            'create': self._automated_action('create'),
            'list': self._automated_action('list'),
            'retrieve': self._automated_action('retrieve'),
            'update': self._automated_action('update'),
            'partial_update': self._automated_action('partial_update'),
            'delete': self._automated_action('delete'),
            'actions': self._actions,
            'collection': self._collection,
        }
        self._clients = {}

    @last
    def _collection(self, context):
        collection_name = context.parent_name
        resource_actions = (
            doc.doc_get(context.instance, ('*', 'actions')) or {})
        collection_actions = context.instance.get('actions', {})
        if set(collection_actions).intersection(resource_actions):
            raise ConflictError(
                'Duplicate actions found on collection {!r}'.format(
                    collection_name))

        cls_name = collection_name.capitalize() + 'Client'
        client = type(cls_name, (Client,),
                      dict(collection_actions, **resource_actions))
        return client

    def _construct_action(self, action_name, action_spec, context):
        collection_path = context.loc[:2]
        collection_spec = doc.doc_get(context.top_spec, collection_path)
        action_url, handler, pre, post = extract_from_action(action_spec)
        action = ApimasAction(
            collection=collection_path,
            action=action_name,
            url=action_url,
            handler=handler(collection_path, collection_spec),
            request_proc=[p(collection_path, collection_spec) for p in pre],
            response_proc=[p(collection_path, collection_spec) for p in post],
        )
        method = action_spec.get('method')
        if _iscollection(context.loc):
            func = _get_collection_action(
                action_name, action, collection_path, action_url, method)
        else:
            func = _get_resource_action(
                action_name, action, collection_path, action_url, method)
        return func

    def _actions(self, context):
        actions = {}
        for action_name, action_spec in context.spec.items():
            if action_name.startswith('.'):
                automated_action_spec = self.AUTOMATED_ACTIONS.get(action_name)
                if automated_action_spec is None:
                    continue
                action_spec = dict(automated_action_spec, **action_spec)
            func = self._construct_action(action_name, action_spec, context)

            if action_name in actions:
                raise ConflictError('Action {!r} already exists'.format(
                    action_name))
            actions[action_name] = func
        context.instance.update({'actions': actions})
        return context.instance

    def _automated_action(self, action_name):
        def _action(context):
            action_spec = self.AUTOMATED_ACTIONS[action_name]

            if action_name in context.instance:
                raise ConflictError('Action {!r} already exists'.format(
                    action_name))
            context.instance.update({action_name: action_spec})
            return context.instance
        return _action

    def _check_construction(self):
        if not self._clients:
            msg = ('Clients have not been constructed yet. Run construct()'
                   ' first.')
            raise AdapterError(msg)

    def construct(self, spec):
        self.spec = copy.deepcopy(spec)
        self._clients = doc.doc_construct(
            {}, spec, constructors=self._constructors,
            allow_constructor_input=False, autoconstruct=True,
            construct_spec=True)

    @property
    def clients(self):
        self._check_construction()
        return self._clients

    def get_endpoint_clients(self, endpoint):
        self._check_construction()
        clients = self.clients_.get(endpoint)
        if clients is None:
            raise NotFound('Clients for endpoint {!r} not found'.format(
                endpoint))
        return clients

    def get_client(self, endpoint, collection):
        self._check_construction()
        client = doc.doc_get(self._clients, (endpoint, collection))
        if client is None:
            msg = 'Client for endpoint {!r} and collection {!r} not found'
            raise NotFound(msg.format(endpoint, collection))
        return client
