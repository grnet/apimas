import copy
import docular
from apimas_django.predicates import PREDICATES


def no_constructor(instance):
    pass


def processor_constructor(instance):
    module_path = docular.doc_spec_get(instance['module_path'])
    docular.doc_spec_set(instance, module_path)


def action_constructor(instance):
    processors = dict(docular.doc_spec_iter_values(instance.get('processors', {}))).values()
    processors = set(processors)
    docular.doc_spec_set(instance, processors)


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
    for name, collection_processors in docular.doc_spec_iter_values(
            instance['collections']):
        if collection_processors:
            v.update(collection_processors)
    docular.doc_spec_set(instance, v)


def app_constructor(instance):
    v = set()
    for name, endpoint_processors in docular.doc_spec_iter_values(
            instance['endpoints']):
        if endpoint_processors:
            v.update(endpoint_processors)
    docular.doc_spec_set(instance, v)


COLLECT_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    {'.action': action_constructor,
     '.processor': processor_constructor,
     '.field.collection.*': collection_constructor,
     '.endpoint': endpoint_constructor,
     '.apimas_app': app_constructor,
    },
    default=no_constructor)


def collect_processors(spec):
    spec = copy.deepcopy(spec)
    docular.doc_spec_construct(spec, PREDICATES, COLLECT_CONSTRUCTORS)
    return docular.doc_spec_get(spec)
