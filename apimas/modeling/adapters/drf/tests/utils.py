import copy
import random
from django.db import models
from apimas.modeling.adapters.drf.utils import import_object
from apimas.modeling.adapters.drf.testing import utils


COLLECTION_TEMPLATE = {
    '.collection': {},
    '.drf_collection': {
        'model': None
    },
    '*': {
    }
}


ACTIONS = {
    '.list': {},
    '.retrieve': {},
    '.create': {},
    '.update': {},
    '.delete': {},
}


PROPERTIES = {'.required': {}}


def generate_ref_field(model_field):
    ref = model_field.related_model.__name__ + '_collection'
    many = model_field.many_to_many or model_field.one_to_many
    return {'.ref': {'to': ref, 'many': many}}


def generate_structure(model_field):
    if model_field.one_to_one or model_field.many_to_one:
        predicate_type = '.struct'
    else:
        predicate_type = '.structarray'
    ref_model = model_field.related_model
    model_fields = filter((lambda x: isinstance(x, models.Field)),
                          ref_model._meta.get_fields())
    field_schema = generate_field_schema(model_fields, iscollection=False)
    return {predicate_type: field_schema, '.readonly': {}}


REL_FIELDS_CONSTRUCTORS = [
    generate_ref_field,
    generate_structure,
]


def generate_field_schema(model_fields, iscollection=True):
    field_schema = {}
    for model_field in model_fields:
        if model_field.related_model is None:
            predicate_type = '.' + utils.FIELD_TYPE_MAPPING[type(model_field)]
            field_node = {'.drf_field': {}, predicate_type: {}}
        else:
            spec_field = random.choice(REL_FIELDS_CONSTRUCTORS)(model_field)
            field_node = dict({'.drf_field': {}}, **spec_field)
        if '.struct' not in field_node and '.structarray' not in field_node:
            field_schema[model_field.name] = dict(field_node, **PROPERTIES)
    identity_field = utils.StringGenerator(n=5)()
    if iscollection:
        field_schema[identity_field] = {'.drf_field': {}, '.identity': {}}
    return field_schema


def generate_random_spec(test_models):
    DEFAULT_PERMISSIONS = [('*',) * 6]
    spec = {'.endpoint': {'permissions': DEFAULT_PERMISSIONS}, 'api': {}}
    for model in test_models:
        model_cls = import_object(model)
        collection_name = model_cls.__name__ + '_collection'
        model_fields = filter((lambda x: isinstance(x, models.Field)),
                              model_cls._meta.get_fields())
        field_schema = generate_field_schema(model_fields)
        collection_spec = copy.deepcopy(COLLECTION_TEMPLATE)
        collection_spec['.drf_collection']['model'] = model
        collection_spec['*'] = field_schema
        collection_spec['actions'] = ACTIONS
        spec['api'][collection_name] = collection_spec
    return spec
