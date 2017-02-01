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


class SpecGenerator(object):
    EXTRA = {
        '.date': {'format': '%Y-%m-%d'},
        '.datetime': {'format': '%Y-%m-%dT%H:%M'},
        '.string': {'max_length': utils.NumberGenerator(upper=255)()}
    }

    def __init__(self, endpoint=None, permissions=None):
        self.endpoint = endpoint or utils.generate_random_string(
            max_length=10)
        self.permissions = permissions or [('*',) * 6]

    def generate(self, test_models):
        spec = {self.endpoint: {}}
        for model in test_models:
            model_cls = import_object(model)
            collection_name = model_cls.__name__ + '_collection'
            model_fields = filter((lambda x: isinstance(x, models.Field)),
                                  model_cls._meta.get_fields())
            field_schema = self.generate_field_schema(model_fields)
            collection_spec = copy.deepcopy(COLLECTION_TEMPLATE)
            collection_spec['.drf_collection']['model'] = model
            collection_spec['*'] = field_schema
            collection_spec['actions'] = ACTIONS
            spec[self.endpoint][collection_name] = collection_spec
            spec[self.endpoint].update(
                {'.endpoint': {'permissions': self.permissions}})
        return spec

    def generate_ref_field(self, model_field):
        ref = model_field.related_model.__name__ + '_collection'
        many = model_field.many_to_many or model_field.one_to_many
        return {'.ref': {'to': self.endpoint + '/' + ref, 'many': many}}

    def generate_structure(self, model_field):
        if model_field.one_to_one or model_field.many_to_one:
            predicate_type = '.struct'
        else:
            predicate_type = '.structarray'
        ref_model = model_field.related_model
        model_fields = filter((lambda x: isinstance(x, models.Field)),
                              ref_model._meta.get_fields())
        field_schema = self.generate_field_schema(model_fields,
                                                  iscollection=False)
        return {predicate_type: field_schema, '.readonly': {}}

    def generate_field_schema(self, model_fields, iscollection=True):
        rel_field_constructors = [
            self.generate_ref_field,
            self.generate_structure,
        ]
        field_schema = {}
        for model_field in model_fields:
            if model_field.related_model is None:
                predicate_type = '.' + utils.FIELD_TYPE_MAPPING[type(
                    model_field)]
                field_node = {'.drf_field': {}, predicate_type: {}}
                field_node[predicate_type].update(
                    self.EXTRA.get(predicate_type, {}))
            else:
                spec_field = random.choice(rel_field_constructors)(
                    model_field)
                field_node = dict({'.drf_field': {}}, **spec_field)
            if '.struct' not in field_node and '.structarray' not in field_node:
                field_schema[model_field.name] = dict(field_node, **PROPERTIES)
        identity_field = utils.generate_random_string(max_length=4)
        if iscollection:
            field_schema[identity_field] = {'.drf_field': {}, '.identity': {}}
        return field_schema
