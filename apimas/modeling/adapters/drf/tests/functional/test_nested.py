from django.db import models
from rest_framework import serializers
from apimas.modeling.adapters.drf.testing import (
    set_apimas_context, ApimasTestCase)
from apimas.modeling.adapters.drf.tests.models import MyModel
from apimas.modeling.adapters.drf.tests.utils import (
    generate_field_schema, ACTIONS)


class MySerializer(serializers.BaseSerializer):

    def get_nested_serializers(self):
        return {k: field for k, field in self.fields.iteritems()
                if isinstance(field, serializers.BaseSerializer)}

    def create_nested_instances(self, validated_data):
        nested_serializers = self.get_nested_serializers()
        nested_instances = {}
        for k, v in nested_serializers.iteritems():
            if k not in validated_data:
                continue
            nested_data = validated_data.pop(k)
            model = v.Meta.model
            nested_instances[k] = model.objects.create(**nested_data)
        return nested_instances

    def create(self, validated_data):
        validated_data.update(self.create_nested_instances(validated_data))
        return super(MySerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        validated_data.update(self.create_nested_instances(validated_data))
        instance = super(MySerializer, self).update(instance, validated_data)
        return instance


model_fields = filter((lambda x: isinstance(x, models.Field)),
                      MyModel._meta.get_fields())
mymodel_field_schema = generate_field_schema(model_fields, iscollection=False)

SPEC = {
    '.endpoint': {
        'permissions': [
            ('*',) * 6
        ]
    },
    'api': {
        'my_collection': {
            '.collection': {},
            '.drf_collection': {
                'model': 'apimas.modeling.adapters.drf.tests.models.RefModel',
                'model_serializers': ['apimas.modeling.adapters.drf.tests.functional.test_nested.MySerializer']
            },
            '*': {
                'id': {
                    '.serial': {},
                    '.drf_field': {},
                    '.readonly': {},
                },
                'mymodel': {
                    '.required': {},
                    '.drf_field': {},
                    '.struct': mymodel_field_schema,
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


@set_apimas_context(__name__, SPEC)
class TestNestedObjectCreation(ApimasTestCase):
    pass
