import random
from rest_framework import status
from apimas.modeling.adapters.drf.testing import (
    set_apimas_context, ApimasTestCase)
from apimas.modeling.adapters.drf.testing import utils
from apimas.modeling.adapters.drf.tests.utils import ACTIONS
from apimas.modeling.adapters.drf.mixins import HookMixin
from apimas.modeling.adapters.drf.tests.models import MyModel


PERMISSION_ACTIONS = {
    'list': 'list',
    'retrieve': 'retrieve',
    'create': 'create',
    'update': 'update',
    'partial_update': 'partial_update',
    'delete': 'destroy'
}


def get_fields_sample(field_schema):
    fields = []
    for field, field_spec in field_schema.iteritems():
        if '.struct' in field_spec:
            nested_fields = get_fields_sample(field_spec.get('.struct'))
        elif '.structarray' in field_spec:
            nested_fields = get_fields_sample(field_spec.get('.structarray'))
        else:
            nested_fields = []
        fields.extend([field + '/' + n_field for n_field in nested_fields])
        fields.append(field)
    size = random.randint(0, len(field_schema))
    return random.sample(fields, size)


def generate_random_permissions(spec):
    structural_element = utils.get_structural_element(spec)
    permissions = []
    for collection, collection_spec in spec.get(
            structural_element).iteritems():
        field_schema = collection_spec.get('*')
        fields = get_fields_sample(field_schema)
        rules = [(collection, action, 'anonymous', field, '*', '*')
                 for action in PERMISSION_ACTIONS.values() for field in fields]
        permissions.extend(rules)
    return permissions


MY_NUMBER_CREATE = 999
MY_STRING_CREATE = 'value set on preprocess_create'
MY_NUMBER_UPDATE = -111
MY_STRING_UPDATE = 'value set on preprocess_update'


SPEC = {
    '.endpoint': {
        'permissions': [],
    },
    'api': {
        'mymodel': {
            '.collection': {},
            '.drf_collection': {
                'model': 'apimas.modeling.adapters.drf.tests.models.MyModel',
                'hook_class': 'apimas.modeling.adapters.drf.tests.functional.test_hooks.WriteOperations',
            },
            '*': {
                'id': {
                    '.serial': {},
                    '.drf_field': {},
                    '.readonly': {},
                },
                'string': {
                    '.drf_field': {},
                    '.string': {},
                    '.readonly': {},
                },
                'text': {
                    '.drf_field': {},
                    '.string': {},
                    '.required': {},
                },
                'number': {
                    '.drf_field': {},
                    '.integer': {},
                    '.readonly': {},
                },
                'big_number': {
                    '.drf_field': {},
                    '.biginteger': {},
                    '.required': {},
                },
                'float_number': {
                    '.drf_field': {},
                    '.float': {},
                    '.required': {},
                },
                'boolean': {
                    '.drf_field': {},
                    '.boolean': {},
                    '.required': {},
                },
                'date_field': {
                    '.drf_field': {},
                    '.date': {},
                    '.required': {},
                },
                'datetime_field': {
                    '.drf_field': {},
                    '.datetime': {},
                    '.required': {},
                },
                'url': {
                    '.identity': {},
                    '.drf_field': {},
                }
            },
            'actions': ACTIONS
        },
    }
}


PERMISSION_RULES = generate_random_permissions(SPEC)
SPEC['.endpoint']['permissions'] = PERMISSION_RULES


def get_permitted_fields(rules, collection, action):
    return [rule[-3] for rule in PERMISSION_RULES
            if rule[1] == action and rule[0] == collection]


class WriteOperations(HookMixin):
    def preprocess_create(self):
        permitted_fields = get_permitted_fields(
            PERMISSION_RULES, 'mymodel', 'create')
        field_schema = utils.get_required_fields(SPEC, 'mymodel')
        field_schema = {k: v for k, v in field_schema.iteritems()
                        if k not in permitted_fields}
        extra_data = utils.populate_model(MyModel, instances={}, create=False)
        extra_data.update(
            {'number': MY_NUMBER_CREATE, 'string': MY_STRING_CREATE})
        self.stash(extra=extra_data)

    def preprocess_update(self):
        extra_data = {'number': MY_NUMBER_UPDATE, 'string': MY_STRING_UPDATE}
        self.stash(extra=extra_data)


@set_apimas_context(__name__, SPEC)
class TestSpec(ApimasTestCase):
    def validate_response_create_mymodel(self, collection, action,
                                         response, data, response_spec,
                                         instance):
        if not get_permitted_fields(PERMISSION_RULES, collection,
                                    'update'):
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            return
        self.validate_response(collection, action, response, data,
                               response_spec, instance)
        response_data = response.json()
        self.assertEqual(response_data['string'], MY_STRING_CREATE)
        self.assertEqual(response_data['number'], MY_NUMBER_CREATE)

    def validate_response_update_mymodel(self, collection, action,
                                         response, data, response_spec,
                                         instance):
        if not get_permitted_fields(PERMISSION_RULES, collection,
                                    'create'):
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            return
        self.validate_response(collection, action, response, data,
                               response_spec, instance)
        response_data = response.json()
        self.assertEqual(response_data['string'], MY_STRING_UPDATE)
        self.assertEqual(response_data['number'], MY_NUMBER_UPDATE)

    def validate_response(self, collection, action, response, data,
                          response_spec, instance):
        permission_action = PERMISSION_ACTIONS.get(action)
        permitted_fields = get_permitted_fields(PERMISSION_RULES, collection,
                                                permission_action)
        response_spec = {k: v for k, v in response_spec.iteritems()
                         if k in permitted_fields}
        if not permitted_fields:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            return
        super(TestSpec, self).validate_response(
            collection, action, response, data, response_spec, instance)
