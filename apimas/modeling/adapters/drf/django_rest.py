from collections import Iterable
from django.db import models
from django.core.exceptions import FieldDoesNotExist
from apimas.modeling.core import documents as doc
from apimas.modeling.adapters.adapter import Adapter
from apimas.modeling.adapters.drf.container import Container
from apimas.modeling.adapters.drf.utils import (
    ApimasException, import_object)


def handle_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FieldDoesNotExist as e:
            raise ApimasException(e)
    return wrapper


class DjangoRestAdapter(Adapter):
    STRUCTURES = {
        '.ref',
        '.struct',
        '.structarray',
        '.resource',
        '.collection',
    }

    DRF_CONF_KEY = 'drf_conf'
    PROPERTIES_CONF_KEY = 'properties'
    NESTED_CONF_KEY = 'nested_objects'

    NON_INTERSECTIONAL_PAIRS = [
        ('read_only', 'write_only'),
        ('required', 'read_only')
    ]

    PROPERTIES = {
        '.readonly': 'read_only',
        '.writeonly': 'write_only',
        '.blankable': 'allow_blank',
        '.nullable': 'allow_null',
        '.required': 'required',
    }

    FIELD_MAPPING = {
        'serial': models.AutoField,
        'integer': models.IntegerField,
        'big-integer': models.BigIntegerField,
        'float': models.FloatField,
        'string': models.CharField,
        'boolean': models.BooleanField,
        'date': models.DateField,
        'datetime': models.DateTimeField,
        'ref': (models.ForeignKey, models.OneToOneField, models.OneToOneRel,
                models.ManyToManyField, models.ManyToOneRel,
                models.ManyToManyRel),
        'structarray': (models.ManyToManyField, models.ManyToOneRel,
                        models.ManyToManyRel),
        'struct': (models.ForeignKey, models.OneToOneField,
                   models.OneToOneRel),
    }

    FIELD_CONSTRUCTORS = {
        '.serial': 'serial',
        '.integer': 'integer',
        '.big-integer': 'big-integer',
        '.float': 'float',
        '.string': 'string',
        '.boolean': 'boolean',
        '.date': 'date',
        '.datetime': 'datetime',
        '.ref': 'ref',
    }

    def __init__(self):
        self.gen_adapter_spec = {}
        self.urls = None

    def construct(self, spec):
        self.adapter_spec = doc.doc_construct(
            {}, spec, constructors=self.get_constructors(),
            allow_constructor_input=True)

    def apply(self):
        if not self.adapter_spec:
            raise ApimasException(
                'Cannot apply an empty adapter specification')
        structural_elements = self.get_structural_elements(self.adapter_spec)
        container = Container(structural_elements[0])
        self.urls = container.create_api_views(
            self.adapter_spec.get(self.DRF_CONF_KEY, {}))

    def get_structural_elements(self, instance):
        filter_func = lambda x: not x.startswith('.')\
            and not x == self.DRF_CONF_KEY
        return filter(filter_func, instance.keys())

    def construct_action(self, instance, spec, loc, top_spec):
        return instance

    def construct_CRUD_action(self, instance, spec, loc, top_spec, action):
        adapter_key = 'allowable_operations'
        self.init_adapter_conf(instance)
        if adapter_key not in instance[self.DRF_CONF_KEY]:
            instance[self.DRF_CONF_KEY][adapter_key] = []
        instance[self.DRF_CONF_KEY][adapter_key].append(action)
        return instance

    def construct_list(self, instance, spec, loc, top_spec):
        return self.construct_CRUD_action(instance, spec, loc, top_spec,
                                          'list')

    def construct_retrieve(self, instance, spec, loc, top_spec):
        return self.construct_CRUD_action(instance, spec, loc, top_spec,
                                          'retrieve')

    def construct_create(self, instance, spec, loc, top_spec):
        return self.construct_CRUD_action(instance, spec, loc, top_spec,
                                          'create')

    def construct_update(self, instance, spec, loc, top_spec):
        return self.construct_CRUD_action(instance, spec, loc, top_spec,
                                          'update')

    def construct_delete(self, instance, spec, loc, top_spec):
        return self.construct_CRUD_action(instance, spec, loc, top_spec,
                                          'delete')

    def construct_endpoint(self, instance, spec, loc, top_spec):
        adapter_key = 'resources'
        structural_elements = self.get_structural_elements(instance)
        assert len(structural_elements) == 1
        self.init_adapter_conf(instance)
        api_schema = {resource: schema[self.DRF_CONF_KEY]
                      for resource, schema in doc.doc_get(
                          instance, (structural_elements[0],)).iteritems()}
        instance[self.DRF_CONF_KEY][adapter_key] = api_schema
        return instance

    def construct_collection(self, instance, spec, loc, top_spec):
        structural_elements = self.get_structural_elements(instance)
        self.init_adapter_conf(instance)
        for element in structural_elements:
            instance[self.DRF_CONF_KEY].update(doc.doc_get(
                instance, (element, self.DRF_CONF_KEY)) or {})
        instance[self.DRF_CONF_KEY].update(**spec)
        return instance

    def construct_resource(self, instance, spec, loc, top_spec):
        resource_schema = self.construct_field_schema(instance)
        resource_schema.update(self.construct_resource_schema(instance))
        instance[self.DRF_CONF_KEY].update(resource_schema)
        return instance

    def construct_field(self, instance, spec, loc, top_spec, field_type=None):
        self.init_adapter_conf(instance)
        self.validate_model_field(top_spec, loc, field_type, **spec)
        return instance

    def construct_struct(self, instance, spec, loc, top_spec):
        self.validate_model_field(top_spec, loc, 'struct')
        nested_schema = self.construct_nested_objects(instance)
        instance[self.DRF_CONF_KEY][self.NESTED_CONF_KEY] = dict(
            nested_schema, **spec)
        return instance

    def construct_structarray(self, instance, spec, loc, top_spec):
        self.validate_model_field(top_spec, loc, 'structarray')
        nested_schema = self.construct_nested_objects(instance)
        instance[self.DRF_CONF_KEY][self.NESTED_CONF_KEY] = dict(
            nested_schema, **spec)
        return instance

    def construct_ref(self, instance, spec, loc, top_spec):
        return self.construct_field(instance, spec, loc, top_spec, 'ref')

    def construct_serial(self, instance, spec, loc, top_spec):
        return self.construct_field(instance, spec, loc, top_spec, 'serial')

    def construct_integer(self, instance, spec, loc, top_spec):
        return self.construct_field(instance, spec, loc, top_spec, 'integer')

    def construct_big_integer(self, instance, spec, loc, top_spec):
        return self.construct_field(instance, spec, loc, top_spec,
                                    'big-integer')

    def construct_string(self, instance, spec, loc, top_spec):
        return self.construct_field(instance, spec, loc, top_spec, 'string')

    def construct_boolean(self, instance, spec, loc, top_spec):
        return self.construct_field(instance, spec, loc, top_spec, 'boolean')

    def construct_datetime(self, instance, spec, loc, top_spec):
        return self.construct_field(instance, spec, loc, top_spec, 'datetime')

    def construct_date(self, instance, spec, loc, top_spec):
        return self.construct_field(instance, spec, loc, top_spec, 'date')

    def construct_blankable(self, instance, spec, loc, top_spec):
        return self.construct_property(instance, loc, 'allow_blank')

    def construct_required(self, instance, spec, loc, top_spec):
        return self.construct_property(instance, loc, 'required')

    def construct_nullable(self, instance, spec, loc, top_spec):
        return self.construct_property(instance, loc, 'allow_null')

    def construct_readonly(self, instance, spec, loc, top_spec):
        return self.construct_property(instance, loc, 'read_only')

    def construct_writeonly(self, instance, spec, loc, top_spec):
        return self.construct_property(instance, loc, 'write_only')

    def construct_indexable(self, instance, spec, loc, top_spec):
        return instance

    def construct_aggregate(self, instance, spec, loc, top_spec):
        return instance

    def construct_property(self, instance, loc, key):
        self.init_adapter_conf(instance)
        if self.PROPERTIES_CONF_KEY not in instance[self.DRF_CONF_KEY]:
            instance[self.DRF_CONF_KEY][self.PROPERTIES_CONF_KEY] = {}
        instance[self.DRF_CONF_KEY][self.PROPERTIES_CONF_KEY][key] = True
        return instance

    @handle_exception
    def validate_model_field(self, spec, loc, field_type, source=None):
        django_conf = self.get_constructor_params(spec, loc[:-1], [])
        model = self.extract_model(source or loc[-2], django_conf)
        if model is None:
            raise ApimasException('Invalid argument, model cannot be `None`')
        model_field = model._meta.get_field(source or loc[-2])
        django_field_type = self.FIELD_MAPPING[field_type]
        if isinstance(django_field_type, Iterable):
            matches = any(type(model_field) is d_field
                          for d_field in django_field_type)
        else:
            matches = type(model_field) is django_field_type
        if not matches:
            raise ApimasException(
                'Field %s is not %s type in your django model' % (
                    repr(loc[-2]), repr(field_type)))

    def validate_intersectional_pairs(self, properties):
        for field_name, prop in properties.iteritems():
            for u, v in self.NON_INTERSECTIONAL_PAIRS:
                if prop.get(u, False) and prop.get(v, False):
                    raise ApimasException(
                        'Field `%s` cannot be both %s and %s' % (
                            field_name, u, v))

    def construct_field_schema(self, instance):
        adapter_key = 'field_schema'
        self.init_adapter_conf(instance)
        field_properties = doc.doc_get(instance, ('*',))
        attrs = {self.PROPERTIES_CONF_KEY: {}, self.NESTED_CONF_KEY: {}}
        for field_name, field_spec in field_properties.iteritems():
            for k, v in attrs.iteritems():
                if k in field_spec[self.DRF_CONF_KEY]:
                    v[field_name] = field_spec[self.DRF_CONF_KEY][k]
        self.validate_intersectional_pairs(attrs[self.PROPERTIES_CONF_KEY])
        fields = [field_name for field_name, _ in field_properties.iteritems()]
        field_schema = {adapter_key: {
            'fields': fields,
        }}
        for k, v in attrs.iteritems():
            if v:
                field_schema[adapter_key].update({k: v})
        return field_schema

    def get_constructor_params(self, spec, loc, params):
        for structure in self.STRUCTURES:
            struct_doc = doc.doc_get(spec, loc[:-1] + (structure,))
            if struct_doc:
                params.append((structure, struct_doc))
        if loc[:-1]:
            return self.get_constructor_params(spec, loc[:-1], params)
        return params

    def extract_model(self, related_field, django_conf):
        structure, params = django_conf[0]
        if len(django_conf) > 1:
            return self.extract_related_model(
                params.get('source', related_field), django_conf[1:])
        return import_object(params.get('model', None))

    @handle_exception
    def extract_related_model(self, related_field, django_conf):
        model = self.extract_model(related_field, django_conf)
        related_field = model._meta.get_field(related_field)
        if related_field.related_model is None:
            raise ApimasException(
                'Field %s is not related with another model' % (
                    repr(related_field)))
        return related_field.related_model

    def construct_resource_schema(self, instance):
        adapter_key = 'filter_fields'
        field_properties = doc.doc_get(instance, ('*',))
        filter_fields = [
            field_name for field_name, spec in field_properties.iteritems()
            if spec.get('.indexable', None) is not None]
        return {adapter_key: filter_fields}

    def construct_nested_objects(self, instance, many=True):
        nested_schema = self.construct_field_schema(instance)
        return nested_schema

    def init_adapter_conf(self, instance):
        if self.DRF_CONF_KEY not in instance:
            instance[self.DRF_CONF_KEY] = {}
