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
from apimas_django.wrapper import django_views
from apimas_django.testing import TestCase
from apimas_django.predicates import PREDICATES
from apimas_django.collect_construction import collect_processors

import docular
import docular.constructors
import pprint


def read_action_spec(action_spec):
    param_keys = ('method', 'status_code', 'content_type',
                  'on_collection', 'url')
    params = {k:v for k, v in (docular.doc_spec_iter_values(action_spec))
              if k in param_keys}

    handler = docular.doc_spec_get(action_spec, 'handler')
    pre = action_spec.pop('pre', {})
    post = action_spec.pop('post', {})

    # Initialize pre processors and post processors with spec.
    pre_keys = sorted(key for key in pre.keys()
                      if key[:1] not in ("*", ".", "="))
    pre_proc = [docular.doc_spec_get(pre.get(key)) for key in pre_keys]
    post_keys = sorted(key for key in post.keys()
                      if key[:1] not in ("*", ".", "="))
    post_proc = [docular.doc_spec_get(post.get(key)) for key in post_keys]

    return params, handler, pre_proc, post_proc


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


def make_processor(processor_data, collection_loc, action_name, artifacts):
    processor = processor_data['module_path']
    config = processor_data['config']
    proc_spec, cls = artifacts[processor]

    collection_subspec = docular.doc_get(proc_spec, collection_loc)
    collection_values = docular.doc_spec_get(collection_subspec) or {}

    action_loc = collection_loc + ('actions', action_name)
    action_subspec = docular.doc_get(proc_spec, action_loc)
    action_values = docular.doc_spec_get(action_subspec) or {}

    arguments = dict(collection_values)
    arguments.update(action_values)
    arguments.update(config)
    return cls(collection_loc, action_name, **arguments)


def mk_url_prefix(loc):
    endpoint_prefix = loc[1]
    segments = []
    collections = loc[3:]
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
        action_name, action_spec, collection_spec, context):
    params, handler, pre_proc, post_proc = read_action_spec(action_spec)
    method = params['method']
    status_code = params['status_code']
    content_type = params['content_type']
    on_collection = params['on_collection']
    action_url = params['url']

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
    artifacts = docular.doc_spec_get(top_spec, ':artifacts')
    pre_proc = [make_processor(proc, loc, action_name, artifacts) for proc in pre_proc]
    post_proc = [make_processor(proc, loc, action_name, artifacts) for proc in post_proc]
    handler = make_processor(handler, loc, action_name, artifacts)

    apimas_action = ApimasAction(
        collection_path, action_url, action_name, status_code, content_type,
        handler, request_proc=pre_proc, response_proc=post_proc)
    return urlpattern, method, apimas_action


def processor_constructor(instance, config):
    value = {}
    value['module_path'] = docular.doc_spec_get(instance['module_path'])
    config_values = {}
    for conf_key, conf_value in docular.doc_spec_iter_values(config):
        config_values[conf_key[1:]] = conf_value
    value['config'] = config_values
    docular.doc_spec_set(instance, value)


def endpoint_constructor(instance):
    print "On endpoint_constructor"
    views = {name:
             mk_django_urls(docular.doc_spec_get(collection_spec))
             for name, collection_spec in docular.doc_spec_iter(
                     instance['collections'])}
    docular.doc_spec_set(instance, views)


def mk_django_urls(action_urls):
    urls = []
    for urlpattern, method_actions in action_urls.iteritems():
        django_view = django_views(method_actions)
        methods = method_actions.keys()
        http_methods = require_http_methods(methods)
        django_view = csrf_exempt(http_methods(django_view))
        urls.append(url(urlpattern, django_view))
    return urls


def apimas_app_constructor(instance):
    print "On apimas_constructor"
    urlpatterns = []
    for endpoint, endpoint_patterns in docular.doc_spec_iter(
            instance['endpoints']):
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
    '.processor': processor_constructor,
    '.string': construct_string,
}

REGISTERED_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    _CONSTRUCTORS, default=no_constructor)


def configure_apimas_app(app_config):
    apimas_app_spec = PREDICATES['.apimas_app']
    return configure_spec(apimas_app_spec, app_config)


def configure_spec(spec, config):
    return docular.doc_spec_config(spec, config, PREDICATES)


def construct_views(spec):
    processors = collect_processors(spec)
    print "FOUND PROCESSORS:", processors
    artifacts = construct_processors(processors, spec)
    spec[':artifacts'] = {'=': artifacts}
    docular.doc_spec_construct(spec, PREDICATES, REGISTERED_CONSTRUCTORS)
    return docular.doc_spec_get(spec)


def pprint_spec(spec):
    pprint.pprint(docular.doc_strip_spec(spec))
