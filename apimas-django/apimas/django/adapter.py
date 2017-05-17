import copy
from collections import defaultdict
from urlparse import urljoin
from django.conf.urls import url
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from apimas import documents as doc, utils
from apimas.errors import ConflictError, AdapterError, InvalidSpec
from apimas.adapters.actions import ApimasAction
from apimas.django.wrapper import DjangoWrapper
from apimas.django.testing import TestCase


class DjangoAdapter(object):
    """
    Adapter responsible for constructing a REST API using Django framework
    as backend.

    Attributes:
        spec (dict): Specification used to construct the implementation.
        views (dict): Dictionary of function-based django view per collection.
        urls (dict): Dictionary of lists which contains a list of url patterns
            per collection.
        test_methods (dict): Dictionary of test methods per collection.
        models (dict): Dictionary of django models per collection.
        AUTOMATED_ACTIONS (dict): Specification of automated action provided
            by the adapter, i.e. `.create`, `.list`, `.retrieve.`, `.update`,
            `.partial_update` and `.delete`.

    Example:
        The following snippet can be used in your `urls.py` file.

        >>> from apimas.django.adapter import DjangoAdapter
        >>> adapter = DjangoAdapter()
        >>> adapter.construct(SPEC) # Construct urlpatterns given a spec.
        >>> urlpatterns = adapter.get_urlpatterns()
    """
    AUTOMATED_ACTIONS = {
        'create': {
            'method': 'POST',
            'url': '/',
            'handler': 'apimas.django.handlers.CreateHandler',
            'pre': [
                'apimas.components.processors.DeSerialization'
            ],
            'post': [
                'apimas.components.processors.Serialization'
            ]
        },
        'list': {
            'method': 'GET',
            'url': '/',
            'handler': 'apimas.django.handlers.ListHandler',
            'post': [
                'apimas.components.processors.Serialization'
            ]
        },
        'retrieve': {
            'method': 'GET',
            'url': '/',
            'handler': 'apimas.django.handlers.RetrieveHandler',
            'post': [
                'apimas.components.processors.Serialization'
            ]
        },
        'update': {
            'method': 'PUT',
            'url': '/',
            'pre': [
                'apimas.components.processors.DeSerialization',
            ],
            'handler': 'apimas.django.handlers.UpdateHandler',
            'post': [
                'apimas.components.processors.Serialization',
            ]

        },
        'partial_update': {
            'method': 'PATCH',
            'url': '/',
            'pre': [
                'apimas.components.processors.Serialization',
            ],
            'handler': 'apimas.django.handlers.UpdateHandler',
            'post': [
                'apimas.components.processors.Serialization',
            ]

        },
        'delete': {
            'method': 'DELETE',
            'url': '/',
            'handler': 'apimas.django.handlers.DeleteHandler',
        },
    }

    def __init__(self, test_mode=False):
        self.spec = None
        self.views = {}
        self.models = {}
        self.urls = defaultdict(list)
        self.test_methods = {}
        self._constructors = {
            'endpoint': self._endpoint,
            'create': self._automated_action('create'),
            'list': self._automated_action('list'),
            'retrieve': self._automated_action('retrieve'),
            'update': self._automated_action('update'),
            'delete': self._automated_action('delete'),
            'actions': self._actions,
        }
        self._action_urls = defaultdict(dict)

    def construct(self, spec):
        """
        Constructs a REST API based on specification given as parameter.
        Implementation is built using django framework.

        At the end of the construction:
            * Django views have been constructed for every action and
              collection.
            * URL patterns have been mapped to the corresponding views.

        Args:
            spec (dict): Specification from which urls and views are
                constructed.
        """
        self.spec = copy.deepcopy(spec)
        doc.doc_construct(
            {}, spec, constructors=self._constructors,
            allow_constructor_input=False, autoconstruct=True,
            construct_spec=True)

    def get_urlpatterns(self):
        """
        Get a list of constructed URL patterns which are mapped to django
        views.

        Returns:
            List of constructed django URL patterns.

        Raises:
            AdapterError: If URLs have not been constructed yet.
        """
        if not self.urls:
            msg = ('Adapter has not constructed the urls yet.'
                   ' Run construct() first.')
            raise AdapterError(msg)
        return [url for endpoint_urls in self.urls.values()
                for url in endpoint_urls]

    def get_testcase(self):
        """
        Gets the test case class for testing the API made by the adapter.

        Returns:
            A Test Case class inheriting from `apimas.django.testing.TestCase`
            and can be used to test your REST API.
        """
        if not self.test_methods:
            msg = ('Adapter has not constructed any implementation yet.'
                   ' Run construct() first.')
            raise AdapterError(msg)
        standard_content = {
            'adapter': self,
            'spec': self.spec,
        }
        content = dict(standard_content, **self.test_methods)
        return type('DjangoTestCase', (TestCase,), content)

    def _construct_view(self, action_name, collection_path, collection_spec,
                        **kwargs):
        method, action_url, handler, pre_proc, post_proc = (
                self._get_action_params(**kwargs))
        if method is None:
            msg = 'URL not found for action {!r}'.format(action_name)
            raise InvalidSpec(msg, loc=collection_path.split('/'))
        if action_url is None:
            msg = 'HTTP method not found for action {!r}'.format(action_name)
            raise InvalidSpec(msg, loc=collection_path.split('/'))
        if handler is None:
            msg = 'Handler not found for action {!r}'.format(action_name)
            raise InvalidSpec(msg, loc=collection_path.split('/'))
        pre_proc = map(lambda x: x(collection_spec), pre_proc)
        post_proc = map(lambda x: x(collection_spec), post_proc)
        context = self._get_orm_context(
            collection_spec.get('.collection'), collection_path)
        apimas_action = ApimasAction(
            collection_path, action_url, action_name,
            handler(collection_spec), request_proc=pre_proc,
            response_proc=post_proc, **context)
        return apimas_action

    def _construct_url(self, path, view, action_url, is_collection):
        # Add a trailing slash to the path.
        pattern = '(?P<pk>[^/.]+)/' if not is_collection else ''
        path += '/'
        path = urljoin(path, pattern)
        if action_url != '/':
            url_pattern = r'^' + urljoin(path, action_url)
        else:
            url_pattern = r'^' + path
        url_pattern = url_pattern.strip('/') + '/$'
        return url_pattern

    def _get_orm_context(self, context, collection_path):
        model = context.get('model')
        if model:
            if collection_path not in self.models:
                orm_model = utils.import_object(model)
                self.models[collection_path] = orm_model
            else:
                # Model already exists, so we do not need to import again.
                orm_model = self.models[collection_path]
            return {
                'orm_type': 'django',
                'orm_model': orm_model
            }
        return {}

    def _is_collection(self, loc):
        # Heuristic: If the parent node is '*', then we presume that
        # we refer to a resource.
        return loc[-3] != '*'

    def _get_action_params(self, **kwargs):
        method = kwargs.get('method')
        action_url = kwargs.get('url')
        handler = kwargs.get('handler')
        if handler is not None:
            handler = utils.import_object(handler)

        # Initialize pre processors and post processors with spec.
        pre_proc = map(lambda x: utils.import_object(x), kwargs.get('pre', []))
        post_proc = map(lambda x: utils.import_object(x),
                        kwargs.get('post', []))
        return (method, action_url, handler, pre_proc, post_proc)

    def _construct_test_method(self, action_name, action_spec, collection_path,
                               is_collection):
        # Dictionary describing the action.
        action_params = {
            'url': action_spec['url'],
            'method': action_spec['method'],
            'iscollection': is_collection
        }
        endpoint, collection = collection_path.split('/')

        def wrapper(func):
            def method(self):
                return func(self, endpoint, collection, action_name,
                            action_params)
            return method

        # Gets the template test case and parameterize it to generate a new
        # one.
        template = getattr(TestCase, '_template_test_case')
        method_name = 'test_%s_%s_%s' % (endpoint, collection, action_name)
        self.test_methods[method_name] = wrapper(template)

    def _construct_action(self, action_name, action_params, collection_spec,
                          collection_path, is_collection):
        view = self._construct_view(action_name, collection_path,
                                    collection_spec, **action_params)
        self.views[collection_path] = view
        urlpattern = self._construct_url(
            collection_path, view, action_params['url'], is_collection)
        method = action_params['method']
        value = doc.doc_get(self._action_urls, (urlpattern, method))
        if value is not None:
            msg = 'Multiple actions found for {url!r} and {method!r} method'
            raise ConflictError(msg.format(url=urlpattern, method=method))
        self._action_urls[urlpattern][method] = view
        self._construct_test_method(action_name, action_params,
                                    collection_path, is_collection)

    def _construct_automated_action(self, instance, spec, loc, context,
                                    action_name):
        is_collection = self._is_collection(loc)
        if self._is_collection(loc) == action_name in ['list', 'create']:
            subject = 'collection' if is_collection else 'resource'
            msg = '.{action!r} cannot be applied on a {subject!s}'
            raise InvalidSpec(msg.format(action=action_name, subject=subject),
                              loc=loc)
        top_spec = context.get('top_spec')
        collection_spec = doc.doc_get(top_spec, loc[:2])
        collection_path = '/'.join(loc[:2])
        default_params = self.AUTOMATED_ACTIONS[action_name]
        # Override default params if users specified their params.
        action_params = dict(default_params, **spec)
        self._construct_action(action_name,
                               action_params,
                               collection_spec, collection_path,
                               is_collection)
        return instance

    def _endpoint(self, instance, spec, loc, context):
        endpoint = context.get('parent_name')
        for k, v in self._action_urls.iteritems():
            url_actions = dict(v)
            django_view = DjangoWrapper(url_actions)
            http_methods = require_http_methods(v.keys())
            django_view = csrf_exempt(http_methods(django_view))
            self.urls[endpoint].append(url(k, django_view))
        return instance

    def _automated_action(self, action):
        def _action(instance, spec, loc, context):
            return self._construct_automated_action(
                instance, spec, loc, context, action)
        return _action

    def _actions(self, instance, spec, loc, context):
        actions = utils.get_structural_elements(spec)
        top_spec = context.get('top_spec')
        for action_name in actions:
            action_params = spec[action_name]
            collection_spec = doc.doc_get(top_spec, loc[:2])
            collection_path = '/'.join(loc[:2])
            is_collection = self._is_collection(loc)
            self._construct_action(action_name, action_params, collection_spec,
                                   collection_path, is_collection)
        return instance
