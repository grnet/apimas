import copy
import docular
from apimas_django.predicates import PREDICATES


def no_constructor(instance):
    pass


def action_constructor(instance):
    v = set()
    preprocessors = dict(docular.doc_spec_iter_values(instance.get('pre', {}))).values()
    postprocessors = dict(docular.doc_spec_iter_values(instance.get('post', {}))).values()
    v.update(preprocessors)
    v.update(postprocessors)
    handler = docular.doc_spec_get(instance.get('handler'))
    if handler:
        v.update({handler})
    docular.doc_spec_set(instance, v)


def collection_constructor(instance):
    v = set()
    for name, action_processors in docular.doc_spec_iter_values(instance['actions']):
        if action_processors:
            v.update(action_processors)

    for name, field_processors in docular.doc_spec_iter_values(instance['fields']):
        if field_processors:
            v.update(field_processors)

    docular.doc_spec_set(instance, v)


def endpoint_constructor(instance):
    v = set()
    for name, collection_processors in docular.doc_spec_iter_values(instance):
        if collection_processors:
            v.update(collection_processors)
    docular.doc_spec_set(instance, v)


def app_constructor(instance):
    v = set()
    for name, endpoint_processors in docular.doc_spec_iter_values(instance):
        if endpoint_processors:
            v.update(endpoint_processors)
    docular.doc_spec_set(instance, v)


COLLECT_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    {'.action': action_constructor,
     '.field.collection.*': collection_constructor,
     '.endpoint': endpoint_constructor,
     '.apimas_app': app_constructor,
    },
    default=no_constructor)


def collect_processors(spec):
    spec = copy.deepcopy(spec)
    docular.doc_spec_construct(spec, PREDICATES, COLLECT_CONSTRUCTORS)
    return docular.doc_spec_get(spec)