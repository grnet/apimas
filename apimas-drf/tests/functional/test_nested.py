from django.db import models
from rest_framework import serializers
from apimas.drf.testing import (
    apimas_context, ApimasTestCase)
from tests.models import MyModel
from tests.utils import SpecGenerator, ACTIONS


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
generator = SpecGenerator()
mymodel_field_schema = generator.generate_field_schema(
    model_fields, iscollection=False)

SPEC = {
    'api': {
        '.endpoint': {
            'permissions': [
                ('*',) * 6
            ]
        },
        'my_collection': {
            '.collection': {},
            '.drf_collection': {
                'model': 'tests.models.RefModel',
                'model_serializers': ['tests.functional.test_nested.MySerializer']
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
            '.actions': ACTIONS
        },
    }
}


@apimas_context(__name__, SPEC)
class TestNestedObjectCreation(ApimasTestCase):
    pass
