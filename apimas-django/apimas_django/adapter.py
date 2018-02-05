import copy
from collections import defaultdict
from urlparse import urljoin
from django.conf.urls import url
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
# from apimas import documents as doc, utils
from apimas import utils
from apimas.tabmatch import Tabmatch
from apimas.errors import (InvalidInput, ConflictError, AdapterError,
                           InvalidSpec)
from apimas.adapters.actions import ApimasAction
from apimas_django.wrapper import DjangoWrapper
from apimas_django.testing import TestCase
from apimas.components.processors import Authentication
from apimas import documents as doc
from apimas_django.predicates import PREDICATES
from apimas_django.collect_construction import collect_processors
import docular
import docular.constructors
import pprint


def _path_to_pattern_set(pattern):
    """
    Converts a pattern from string format to a pattern set.

    Args:
        pattern (str): A pattern in a string format, e.g. `api/foo/bar`.

    Returns:
        A pattern set, e.g. [set(['api']), set(['foo']), set(['bar'])
    """
    pattern = pattern.split('/')
    pattern_len = len(pattern)
    if pattern_len != 3:
        msg = 'A pattern with 3 columns is expected. {!s} found'
        raise InvalidInput(msg.format('/'.join(pattern)))
    pattern_set = []
    for segment in pattern:
        parsed_segment = doc.parse_pattern(segment)
        pattern_doc = {parsed_segment: {}}
        pattern_set.extend(
            doc.doc_to_level_patterns(pattern_doc)[:-1])
    return pattern_set


def _get_action_params(action_params):
    method = docular.doc_spec_get(action_params.get('method'))
    on_collection = docular.doc_spec_get(action_params.get('on_collection'))
    action_url = docular.doc_spec_get(action_params.get('url'))
    handler = docular.doc_spec_get(action_params.get('handler'))

    pre = action_params.get('pre', {})
    post = action_params.get('post', {})
    # Initialize pre processors and post processors with spec.
    pre_keys = sorted(key for key in pre.keys()
                      if key[:1] not in ("*", ".", "="))
    pre_proc = [docular.doc_spec_get(pre.get(key)) for key in pre_keys]
    post_keys = sorted(key for key in post.keys()
                      if key[:1] not in ("*", ".", "="))
    post_proc = [docular.doc_spec_get(post.get(key)) for key in post_keys]
    return (method, on_collection, action_url, handler, pre_proc, post_proc)


def get_orm_context(context):
    model = docular.doc_spec_get(context.get('model'))
    if model:
        return {
            'orm_type': 'django',
            'orm_model': utils.import_object(model)
        }
    return {}


# def action_constructor(instance, loc, context):
#     action_name = loc[-1]
#     collection_path = "/".join(loc)
#     collection_spec = docular.doc_get(top_spec, loc[:-3])
#     action_params = instance

#     docular.doc_spec_set(instance, mk_action(...))


def collection_django_constructor(instance, context, loc):
    print "On collection_django_constructor loc:", loc
    docular.doc_spec_set(instance,
                         mk_collection_views(instance, context))


def get_subcollection_views(collection_spec):
    views = {}
    for key, value in docular.doc_spec_iter_values(
            collection_spec['fields']):
        if value is not None:
            views.update(value)
    return views


def mk_collection_views(collection_spec, context):
    actions = docular.doc_get(collection_spec, ("actions",))
    if not actions:
        print "NO ACTIONS", pprint_spec(collection_spec)

    views = get_subcollection_views(collection_spec)

    for key, action_spec in docular.doc_spec_iter(actions):
        urlpattern, method, view = mk_action_view(
            key, action_spec, collection_spec, context)
        docular.doc_set(views, (urlpattern, method), view)
    return views


def named_pattern(name):
    return '(?P<%s>[^/.]+)' % name


def join_urls(*args):
    """
    Join arguments into a url.

    >>> join_urls("http://www.test.org", "path")
    'http://www.test.org/path'
    >>> join_urls("http://www.test.org/", "path")
    'http://www.test.org/path'
    >>> join_urls("http://www.test.org", "/path")
    'http://www.test.org/path'
    >>> join_urls("http://www.test.org/", "/path")
    'http://www.test.org/path'
    >>> join_urls("http://www.test.org/", "/path/")
    'http://www.test.org/path/'
    >>> join_urls("http://www.test.org/a/b", "c/d")
    'http://www.test.org/a/b/c/d'
    >>> join_urls("http://www.test.org/a/b/", "c/d")
    'http://www.test.org/a/b/c/d'
    >>> join_urls("http://www.test.org/a/b", "/c/d")
    'http://www.test.org/a/b/c/d'
    >>> join_urls("http://www.test.org/a/b/", "/c/d")
    'http://www.test.org/a/b/c/d'
    >>> join_urls("http://www.test.org/a/b/", "/c/d/", "/e/f/")
    'http://www.test.org/a/b/c/d/e/f/'
    >>> join_urls("/path1", "/path")
    '/path1/path'
    >>> join_urls("path1", "/path")
    'path1/path'
    >>> join_urls("path1/")
    'path1/'
    >>> join_urls("path1/", "path2", "path3")
    'path1/path2/path3'
    >>> join_urls("", "path2", "path3")
    'path2/path3'
    >>> join_urls("", "", "")
    ''
    """
    args = filter(bool, args)

    if len(args) == 0:
        return ''

    if len(args) == 1:
        return args[0]

    return "/".join([args[0].rstrip("/")] +
                    [a.strip("/") for a in args[1:-1]] +
                    [args[-1].lstrip("/")])


def _construct_url(path, action_url):
    unpacked_action_url = action_url.replace('*', named_pattern('pk'))
    url = join_urls(path, unpacked_action_url).rstrip('/') + '/'
    url_pattern = r'^' + url + '$'
    return url_pattern


    pattern = named_pattern('pk') if not on_collection else ''
    path = join_urls(path, pattern)
    if action_url != '/':
        url_pattern = r'^' + join_urls(path, action_url)
    else:
        url_pattern = r'^' + path
    url_pattern = url_pattern.rstrip('/') + '/$'
    return url_pattern


def construct_processors(processors, spec):
    artifacts = {}
    for processor in processors:
        print 'Constructing:', processor
        proc = utils.import_object(processor)
        newspec = copy.deepcopy(spec)
        docular.doc_spec_construct(newspec, PREDICATES, proc.constructors)
        artifacts[processor] = (newspec, proc.processor)
    return artifacts


def make_processor(processor, collection_loc, on_collection, artifacts):
    proc_spec, cls = artifacts[processor]
    subspec = docular.doc_get(proc_spec, collection_loc)
    return cls(subspec, on_collection)


def mk_url_prefix(loc):
    endpoint_prefix = loc[0]
    segments = []
    collections = loc[1:]
    for i, name in enumerate(reversed(collections)):
        position, is_fields = divmod(i, 2)
        if not is_fields:
            segments.append(name)
        else:
            assert name == 'fields'
            name = 'id' + str(position)
            segments.append(named_pattern(name))
    segments.append(endpoint_prefix)
    return '/'.join(reversed(segments))


def mk_action_view(
        action_name, action_params, collection_spec, context):
    method, on_collection, action_url, handler, pre_proc, post_proc = (
        _get_action_params(action_params))

    loc = context['loc']
    if method is None:
        msg = 'URL not found for action {!r}'.format(action_name)
        raise InvalidSpec(msg, loc=loc)
    if action_url is None:
        msg = 'HTTP method not found for action {!r}'.format(action_name)
        raise InvalidSpec(msg, loc=loc)
    if handler is None:
        msg = 'Handler not found for action {!r}'.format(action_name)
        raise InvalidSpec(msg, loc=loc)

    print "ACTION", action_name
    collection_path = mk_url_prefix(loc)
    urlpattern = _construct_url(collection_path, action_url)
    method = method.upper()

    top_spec = context['top_spec']
    artifacts = docular.doc_spec_get(docular.doc_get(top_spec, ('.meta', 'artifacts')))
    pre_proc = [make_processor(proc, loc, on_collection, artifacts) for proc in pre_proc]
    post_proc = [make_processor(proc, loc, on_collection, artifacts) for proc in post_proc]
    handler = make_processor(handler, loc, on_collection, artifacts)

    orm_context = get_orm_context(collection_spec)
    apimas_action = ApimasAction(
        collection_path, action_url, action_name, handler,
        request_proc=pre_proc, response_proc=post_proc, **orm_context)
    return urlpattern, method, apimas_action


def endpoint_constructor(instance):
    print "On endpoint_constructor"
    views = {name:
             mk_django_urls(docular.doc_spec_get(collection_spec))
             for name, collection_spec in docular.doc_spec_iter(instance)}
    docular.doc_spec_set(instance, views)


def mk_django_urls(action_urls):
    urls = []
    for urlpattern, method_actions in action_urls.iteritems():
        django_view = DjangoWrapper(method_actions,
                                    meta={'root_url': 'http://127.0.0.1:8000/'})
        methods = method_actions.keys()
        http_methods = require_http_methods(methods)
        django_view = csrf_exempt(http_methods(django_view))
        urls.append(url(urlpattern, django_view))
    return urls


def apimas_app_constructor(instance):
    print "On apimas_constructor"
    urlpatterns = []
    for endpoint, endpoint_patterns in docular.doc_spec_iter(instance):
        endpoint_patterns = docular.doc_spec_get(endpoint_patterns)
        for collection, collection_patterns in endpoint_patterns.iteritems():
            urlpatterns.extend(collection_patterns)
    print "URLPATTERNS:"
    for urlpattern in urlpatterns:
        print urlpattern
    docular.doc_spec_set(instance, urlpatterns)


def no_constructor(instance):
    pass


def construct_string(instance, loc):
    if '=' not in instance:
        #print "No string value at", loc
        pass
    else:
        instance['='] = str(instance['='])


def construct_boolean(instance, loc):
    v = instance.get('=')
    if v is None:
        #print "no boolean in %s" % str(loc)
        pass
    else:
        instance['='] = bool(v)


_CONSTRUCTORS = {
    '.apimas_app': apimas_app_constructor,
    '.boolean': construct_boolean,
    '.field.collection.django': collection_django_constructor,
    '.endpoint': endpoint_constructor,
    '.string': construct_string,
}

REGISTERED_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    _CONSTRUCTORS, default=no_constructor)


def load_apimas_config(config):
    apimas_app_spec = PREDICATES['.apimas_app']
    return docular.doc_spec_config(apimas_app_spec, config, PREDICATES)


def construct_views(spec):
    processors = collect_processors(spec)
    print "FOUND PROCESSORS:", processors
    artifacts = construct_processors(processors, spec)
    spec['.meta']['artifacts'] = {'=': artifacts}
    docular.doc_spec_construct(spec, PREDICATES, REGISTERED_CONSTRUCTORS)
    return docular.doc_spec_get(spec)


def pprint_spec(spec):
    pprint.pprint(docular.doc_strip_spec(spec))


# class DjangoAdapter(object):
#     """
#     Adapter responsible for constructing a REST API using Django framework
#     as backend.

#     Attributes:
#         spec (dict): Specification used to construct the implementation.
#         views (dict): Dictionary of function-based django view per collection.
#         urls (dict): Dictionary of lists which contains a list of url patterns
#             per collection.
#         test_methods (dict): Dictionary of test methods per collection.
#         models (dict): Dictionary of django models per collection.
#         AUTOMATED_ACTIONS (dict): Specification of automated action provided
#             by the adapter, i.e. `.create`, `.list`, `.retrieve.`, `.update`,
#             `.partial_update` and `.delete`.

#     Example:
#         The following snippet can be used in your `urls.py` file.

#         >>> from apimas_django.adapter import DjangoAdapter
#         >>> adapter = DjangoAdapter()
#         >>> adapter.construct(SPEC) # Construct urlpatterns given a spec.
#         >>> urlpatterns = adapter.get_urlpatterns()
#     """

#     def __init__(self, config, test_mode=False):
#         self.spec = docular.doc_spec_config(apimas_spec, config, PREDICATES)
#         self.views = {}
#         self.models = {}
#         self.urls = defaultdict(list)
#         self._test_methods = {}
#         # self._constructors = {
#         #     'endpoint': self._endpoint,
#         #     'create': self._automated_action('create'),
#         #     'list': self._automated_action('list'),
#         #     'retrieve': self._automated_action('retrieve'),
#         #     'update': self._automated_action('update'),
#         #     'delete': self._automated_action('delete'),
#         #     'actions': self._actions,
#         #     'auth':   self._auth,
#         #     'basic': Authentication.CONSTRUCTORS['basic'],
#         #     'token':   Authentication.CONSTRUCTORS['token'],
#         # }
#         self._action_urls = defaultdict(dict)
#         self._auth_urls = []

#     def construct(self):
#         """
#         Constructs a REST API based on specification given as parameter.
#         Implementation is built using django framework.

#         At the end of the construction:
#             * Django views have been constructed for every action and
#               collection.
#             * URL patterns have been mapped to the corresponding views.

#         Args:
#             spec (dict): Specification from which urls and views are
#                 constructed.
#         """
#         docular.doc_spec_construct(self.spec, PREDICATES, CONSTRUCTORS)

#     def get_urlpatterns(self):
#         """
#         Get a list of constructed URL patterns which are mapped to django
#         views.

#         Returns:
#             List of constructed django URL patterns.

#         Raises:
#             AdapterError: If URLs have not been constructed yet.
#         """
#         if not self.urls:
#             msg = ('Adapter has not constructed the urls yet.'
#                    ' Run construct() first.')
#             raise AdapterError(msg)
#         urlpatterns = [url for endpoint_urls in self.urls.values()
#                        for url in endpoint_urls]
#         urlpatterns.extend(self._auth_urls)
#         return urlpatterns

#     def _update_testcase_content(self, matches, pattern_spec, content):
#         for row in matches:
#             key = (row.endpoint, row.collection, row.action)
#             for stage, func in pattern_spec.iteritems():
#                 if stage not in content:
#                     content[stage] = {}
#                 if key in content[stage]:
#                     msg = ('A function has already been set for stage'
#                            ' {stage!r}. ({loc!s})')
#                     raise ConflictError(msg.format(
#                         stage=row.stage, loc=','.join(key)))
#                 content[stage][key] = func
#             test_method = self._test_methods[key]
#             method_name = 'test_%s_%s_%s' % key
#             content[method_name] = test_method

#     def get_testcase(self, patterns=None, name='DjangoTestCase', **kwargs):
#         """
#         Gets the test case class for testing the API made by the adapter.

#         This method generates an `apimas_django.testing.TestCase` subclass.
#         It expects a dictionary of patterns which specifies which tests should
#         be run. Each pattern is a string with the following format:

#             ```
#             <endpoint pattern>/<collection pattern>/<action pattern>
#             ```
#         For example, the pattern `api/foo/create` matches only with the action
#         "create" of collection "foo" which belongs to the endpoint named
#         "api".

#         Typically, A test case for every triplet of endpoint-collection-action
#         is generated, thus developer can filter which tests should be run
#         via these patterns. Note that exclusion patterns are not supported.

#         Also, this dictionary defines an execution spec per pattern.
#         This spec denotes code that must be executed if there is match. There
#         are three hooks. Each hook is identified by a key which maps to a
#         function object. Specifically:
#             * `SETUP`: Called during the setup of the test case. Typically,
#               used for the setup of the databse with mock data, etc.
#               Signature: `(endpoint, collection, action, action_spec)`

#             * `PREPARE`: Called during the preparation of the request. It
#               must define `self.request_url` and self.request_kwargs` fields.
#               Signature: `(endpoint, collection, action, action_spec)`

#             * 'VALIDATE': Called after the client request. It's the hook for
#               your assertions based on the client response.
#               Signature: `(endpoint, collection, action, action_spec,
#                            response)`

#         Note that if there is hook not specified in the execution spec, then
#         the default code as specified by the `apimas_django.testing.TestCase`
#         is executed.

#         Args:
#             patterns (dict): Dictionary of execution spec per pattern.
#             name (str): (optional) Name of generated class.
#             **kwargs: Additional content for generated class.

#         Returns:
#             A Test Case class inheriting from `apimas_django.testing.TestCase`
#             and used to test implementation constructed by adapter.

#         Examples:
#             The following snippet can be included in your `tests.py` file.
#             >>> from apimas_django.adapter import DjangoAdapter
#             >>> adapter = DjangoAdapter()
#             >>> adapter.construct(SPEC)
#             >>> # This tests all actions for all collections under endpoint
#             >>> # named `api`.
#             >>> patterns = {
#             ...     'api/*/*': {}
#             ... }
#             >>> TestCase = adapter.get_testcase(patterns=patterns)

#             Also, you can add your own code like the following:
#             >>> def my_validation(endpoint, collection, action, action_spec,
#             ...                   response):
#             ...     # My assertions.
#             >>> # This applies method `my_validation` for validating all
#             >>> # actions of collection `api/mycollection`.
#             >>> patterns = {
#             ...        'api/mycollection/*': {
#             ...            'VALIDATE': my_validation,
#             ...       }
#             ... }
#             >>> TestCase = adapter.get_testcase(patterns=patterns)
#         """
#         rules = self._test_methods.keys()
#         patterns = patterns or rules
#         if not self._test_methods:
#             msg = ('Adapter has not constructed any implementation yet.'
#                    ' Run construct() first.')
#             raise AdapterError(msg)

#         if not isinstance(patterns, dict):
#             msg = 'patterns should be a dict, not {!r}'
#             raise InvalidInput(msg.format(type(patterns)))

#         columns = ('endpoint', 'collection', 'action')
#         tab = Tabmatch(columns, rules)
#         content = {}
#         for pattern, pattern_spec in patterns.iteritems():
#             pattern_set = _path_to_pattern_set(pattern)
#             matches = tab.multimatch(pattern_set, expand=columns)
#             self._update_testcase_content(matches, pattern_spec, content)

#         standard_content = {
#             'adapter': self,
#             'spec': self.spec,
#         }
#         content = dict(standard_content, **content)
#         content.update(kwargs)
#         return type(name, (TestCase,), content)

#     def _construct_view(self, action_name, collection_path, collection_spec,
#                         action_params, meta):
#         method, action_url, handler, pre_proc, post_proc = (
#                 self._get_action_params(action_params))
#         if method is None:
#             msg = 'URL not found for action {!r}'.format(action_name)
#             raise InvalidSpec(msg, loc=collection_path.rsplit('/', 1))
#         if action_url is None:
#             msg = 'HTTP method not found for action {!r}'.format(action_name)
#             raise InvalidSpec(msg, loc=collection_path.rsplit('/', 1))
#         if handler is None:
#             msg = 'Handler not found for action {!r}'.format(action_name)
#             raise InvalidSpec(msg, loc=collection_path.rsplit('/', 1))
#         method = method.upper()
#         pre_proc = [proc(collection_path, collection_spec, **meta)
#                     for proc in pre_proc]
#         post_proc = [proc(collection_path, collection_spec, **meta)
#                      for proc in post_proc]
#         context = self._get_orm_context(
#             collection_spec.get('.collection'), collection_path)
#         apimas_action = ApimasAction(
#             collection_path, action_url, action_name,
#             handler(collection_path, collection_spec, **meta),
#             request_proc=pre_proc, response_proc=post_proc, **context)
#         return apimas_action

#     def _construct_url(self, path, view, action_url, is_collection):
#         # Add a trailing slash to the path.
#         pattern = '(?P<pk>[^/.]+)/' if not is_collection else ''
#         path += '/'
#         path = urljoin(path, pattern)
#         if action_url != '/':
#             url_pattern = r'^' + urljoin(path, action_url)
#         else:
#             url_pattern = r'^' + path
#         url_pattern = url_pattern.strip('/') + '/$'
#         return url_pattern

#     def _get_orm_context(self, context, collection_path):
#         model = context.get('model')
#         if model:
#             if collection_path not in self.models:
#                 orm_model = utils.import_object(model)
#                 self.models[collection_path] = orm_model
#             else:
#                 # Model already exists, so we do not need to import again.
#                 orm_model = self.models[collection_path]
#             return {
#                 'orm_type': 'django',
#                 'orm_model': orm_model
#             }
#         return {}

#     def _is_collection(self, loc):
#         # Heuristic: If the parent node is '*', then we presume that
#         # we refer to a resource.
#         return loc[-3] != '*'

#     def _get_action_params(self, action_params):
#         method = action_params.get('method')
#         action_url = action_params.get('url')
#         handler = action_params.get('handler')
#         if handler is not None:
#             handler = utils.import_object(handler)

#         # Initialize pre processors and post processors with spec.
#         pre_proc = [utils.import_object(x)
#                     for x in action_params.get('pre', [])]
#         post_proc = [utils.import_object(x)
#                      for x in action_params.get('post', [])]
#         return (method, action_url, handler, pre_proc, post_proc)

#     def _construct_test_method(self, action_name, action_spec, collection_path,
#                                is_collection):
#         # Dictionary describing the action.
#         action_params = {
#             'url': action_spec['url'],
#             'method': action_spec['method'],
#             'iscollection': is_collection
#         }
#         endpoint, collection = collection_path.rsplit('/', 1)

#         def wrapper(func):
#             def method(self):
#                 return func(self, endpoint, collection, action_name,
#                             action_params)
#             return method

#         # Gets the template test case and parameterize it to generate a new
#         # one.
#         template = getattr(TestCase, '_template_test_case')
#         key = (endpoint, collection, action_name)
#         self._test_methods[key] = wrapper(template)

#     def _construct_action(self, action_name, action_params, collection_spec,
#                           collection_path, is_collection, meta):
#         view = self._construct_view(action_name, collection_path,
#                                     collection_spec, action_params, meta)
#         self.views[collection_path] = view
#         urlpattern = self._construct_url(
#             collection_path, view, action_params['url'], is_collection)
#         method = action_params['method'].upper()
#         value = doc.doc_get(self._action_urls, (urlpattern, method))
#         if value is not None:
#             msg = 'Multiple actions found for {url!r} and {method!r} method'
#             raise ConflictError(msg.format(url=urlpattern, method=method))
#         self._action_urls[urlpattern][method] = view
#         self._construct_test_method(action_name, action_params,
#                                     collection_path, is_collection)

#     def _construct_automated_action(self, context, action_name):
#         is_collection = self._is_collection(context.loc)
#         if self._is_collection(context.loc) ==\
#                 action_name in ['list', 'create']:
#             subject = 'collection' if is_collection else 'resource'
#             msg = '.{action!r} cannot be applied on a {subject!s}'
#             raise InvalidSpec(msg.format(action=action_name, subject=subject),
#                               loc=context.loc)
#         top_spec = context.top_spec
#         collection_spec = doc.doc_get(top_spec, context.loc[:2])
#         collection_path = '/'.join(context.loc[:2])
#         default_params = self.AUTOMATED_ACTIONS[action_name]
#         # Override default params if users specified their params.
#         action_params = dict(default_params, **context.spec)
#         meta = context.top_spec.get('.meta', {})
#         self._construct_action(action_name,
#                                action_params,
#                                collection_spec, collection_path,
#                                is_collection, meta)
#         return context.instance

#     def _endpoint(self, context):
#         endpoint = context.parent_name
#         for k, v in self._action_urls.iteritems():
#             url_actions = dict(v)
#             django_view = DjangoWrapper(url_actions)
#             http_methods = require_http_methods(v.keys())
#             django_view = csrf_exempt(http_methods(django_view))
#             self.urls[endpoint].append(url(k, django_view))
#         return context.instance

#     def _automated_action(self, action):
#         def _action(context):
#             return self._construct_automated_action(context, action)
#         return _action

#     def _actions(self, context):
#         actions = utils.get_structural_elements(context.spec)
#         top_spec = context.top_spec
#         for action_name in actions:
#             action_params = context.spec[action_name]
#             collection_spec = doc.doc_get(top_spec, context.loc[:2])
#             collection_path = '/'.join(context.loc[:2])
#             is_collection = self._is_collection(context.loc)
#             meta = context.top_spec.get('.meta', {})
#             self._construct_action(action_name, action_params, collection_spec,
#                                    collection_path, is_collection, meta)
#         return context.instance

#     def _get_auth_params(self, context):
#         handler = context.spec.get('handler')
#         if handler is None:
#             raise InvalidSpec("'auth_handler' must not be None",
#                               loc=context.loc)
#         handler = utils.import_object(handler)

#         auth_method = context.spec.get('auth_method')
#         if auth_method is None:
#             raise InvalidSpec("'auth method' must not be None",
#                               loc=context.loc)

#         auth_url = context.spec.get('url')
#         if auth_url is None:
#             raise InvalidSpec("'auth url must not be None'", loc=context.loc)
#         return handler, auth_method, auth_url

#     def _auth(self, context):
#         handler, auth, auth_url = self._get_auth_params(context)
#         meta = context.top_spec.get('.meta', {})
#         path = context.parent_name or None

#         # We use apimas built-in processor for authentication.
#         apimas_action = ApimasAction(
#             path, url=auth_url, action='auth',
#             handler=handler(path, context.top_spec, auth_method=auth, **meta))
#         django_view = DjangoWrapper({'POST': apimas_action})
#         http_methods = require_http_methods(['POST'])
#         django_view = csrf_exempt(http_methods(django_view))
#         url_pattern = r'^%s/$' % (auth_url.strip('/'))
#         self._auth_urls.append(url(url_pattern, django_view))
