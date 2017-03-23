from collections import Iterable
from django.db import models
from django.conf.urls import url, include
from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers
from rest_framework import routers
from apimas import documents as doc
from apimas.drf import utils
from apimas.drf.serializers import (
    generate_container_serializer, generate_model_serializer)
from apimas.drf.views import generate_view
from apimas.adapters.cookbooks import NaiveAdapter


def handle_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FieldDoesNotExist as e:
            raise utils.DRFAdapterException(e, loc=kwargs.get('loc', ()))
    return wrapper


def _validate_model_type(api_field_name, model_field, django_field_type,
                         loc=()):
    """
    Checks that the type of the specified model field matches with the
    `django_field_type` passed as parameter.

    `django_field_type` may be an iterable of types. If at least one type
    matches with the type of given model field, then we have a match.
    """
    if isinstance(django_field_type, Iterable):
        matches = any(isinstance(model_field, d_field)
                      for d_field in django_field_type)
    else:
        matches = isinstance(model_field, django_field_type)
    if not matches:
        raise utils.DRFAdapterException(
            'Field {!r} is not a {!r} in your django model'.format(
                api_field_name, django_field_type), loc=loc)
    return model_field


def _validate_relational_field(api_field_name, ref_model, model_field,
                               loc=()):
    """
    Checks that the given model field is related to the model given as
    parameter.
    """
    if model_field.related_model is not ref_model:
        raise utils.DRFAdapterException(
            'Model field {!r} is not related to {!r}.'.format(
                model_field.name, ref_model), loc=loc)
    return model_field


def _validate_model_attribute(api_field_name, model, model_attr_name,
                              loc=()):
    """ Checks that model have an attribute named as `model_attr_name`."""
    model_attr = getattr(model, model_attr_name, None)
    if model_attr is None:
        raise utils.DRFAdapterException(
            'Attribute {!r} ({!r}) not found in model {!r}'.format(
                model_attr_name, api_field_name, model.__name__), loc=loc)
    return model_attr


class DjangoRestAdapter(NaiveAdapter):
    STRUCTURES = {
        '.struct': '.drf_field',
        '.structarray': '.drf_field',
        '.collection': '.drf_collection',
    }

    ADAPTER_CONF = 'drf_conf'
    PROPERTIES_CONF_KEY = 'properties'
    NESTED_CONF_KEY = 'nested_objects'

    NON_INTERSECTIONAL_PAIRS = [
        ('read_only', 'write_only'),
        ('required', 'read_only')
    ]

    # Dictionary which contains expected extra parameters for some types.
    # Defines a mapping of the APIMAS parameter with that of adapter, and a
    # default value if it is optional.
    EXTRA_PARAMS = {
        '.string': {
            'max_length': {
                'default': 255,
                'map': 'max_length',
            }
        },
        '.choices': {
            'allowed': {
                'default': [],
                'map': 'allowed',
            },
            'display': {
                'default': [],
                'map': 'display',
            }
        },
        '.date': {
            'format': {
                'default': ['%Y-%m-%d'],
                'map': 'input_formats',
            }
        },
        '.datetime': {
            'format': {
                'default': ['%Y-%m-%dT%H:%M:%S'],
                'map': 'input_formats',
            }
        }
    }

    PROPERTY_MAPPING = {
        'readonly': 'read_only',
        'writeonly': 'write_only',
        'blankable': 'allow_blank',
        'nullable': 'allow_null',
        'required': 'required',
    }

    SERILIZERS_TYPE_MAPPING = {
        'serial': serializers.IntegerField,
        'integer': serializers.IntegerField,
        'biginteger': serializers.IntegerField,
        'float': serializers.FloatField,
        'string': serializers.CharField,
        'text': serializers.CharField,
        'choices': serializers.ChoiceField,
        'email': serializers.EmailField,
        'boolean': serializers.BooleanField,
        'date': serializers.DateField,
        'datetime': serializers.DateTimeField,
        'structarray': serializers.ListSerializer,
        'struct': serializers.Serializer,
        'ref': serializers.HyperlinkedRelatedField,
        'file': serializers.FileField,
        'identity': serializers.HyperlinkedIdentityField,
    }

    TYPE_MAPPING = {
        'serial': models.AutoField,
        'integer': models.IntegerField,
        'biginteger': models.BigIntegerField,
        'float': models.FloatField,
        'string': models.CharField,
        'text': models.TextField,
        'choices': models.CharField,
        'email': models.EmailField,
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
        'file': models.FileField,
        'identity': None,
    }

    PREDICATES = list(NaiveAdapter.PREDICATES) + [
        '.drf_field', '.drf_collection']

    def __init__(self):
        self.gen_adapter_spec = {}
        self.urls = {}
        self.models = {}
        self.serializers = {}
        self.views = {}

    def get_views(self):
        """ Get `ViewSet`classes for every collection. """
        return self.views

    def get_serializers(self):
        """ Get `Serializer`classes for every collection. """
        return self.serializers

    def get_class(self, class_container, endpoint, collection):
        """
        Utitily method for getting the generated class based on the given
        collection.
        """
        collection_name = endpoint + '/' + collection
        if not class_container:
            raise utils.DRFAdapterException(
                'Classes have not been constructed yet.'
                ' Run {!s}.construct()`'.format(self.__class__.__name__))
        if collection_name not in class_container:
            raise utils.DRFAdapterException(
                'Class not found for collection {!r}'.format(collection_name))
        return class_container[collection_name]

    def get_serializer(self, endpoint, collection):
        """ Get `Serializer` class based on the given collection. """
        return self.get_class(self.serializers, endpoint, collection)

    def get_view(self, endpoint, collection):
        """ Get `ViewSet` class based on the given collection. """
        return self.get_class(self.views, endpoint, collection)

    def construct_endpoint(self, instance, spec, loc, context):
        """
        Constructor of '.endpoint' predicate.

        It gets the generated views and it maps them with urlpatterns which
        will later be used from django.
        """
        parent_name = context.get('parent_name')
        collections = self.get_structural_elements(instance)
        if not collections:
            raise utils.DRFAdapterException(
                '.endpoint without any collection found.', loc=loc)
        router = routers.DefaultRouter()
        for collection in collections:
            collection_spec = instance.get(collection)
            view = collection_spec.get(self.ADAPTER_CONF)
            basename = parent_name + '_' + collection
            router.register(collection, view, base_name=basename)
        self.urls[parent_name] = url(
            r'^' + parent_name + '/', include(router.urls))

    def construct_CRUD_action(self, instance, spec, loc, context, action):
        """ Adds an action to the list of allowable. """
        self.init_adapter_conf(instance, initial=[])
        instance[self.ADAPTER_CONF].append(action)
        return instance

    def construct_list(self, instance, spec, loc, context):
        """
        Constuctor for `.list` predicate.

        Allows list operation to be performed on a resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'list')

    def construct_retrieve(self, instance, spec, loc, context):
        """
        Constuctor for `.retrieve` predicate.

        Allows retrieval of specific resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'retrieve')

    def construct_create(self, instance, spec, loc, context):
        """
        Constuctor for `.retrieve` predicate.

        Allows creation of a new resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'create')

    def construct_update(self, instance, spec, loc, context):
        """
        Constuctor for `.retrieve` predicate.

        Allows update of a specific resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'update')

    def construct_delete(self, instance, spec, loc, context):
        """
        Constuctor for `.retrieve` predicate.

        Allows deletion of specific resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'delete')

    def get_permissions(self, collection_path, top_spec):
        """
        It constructs permissions rules for every collection.

        Typically, permission rules are provided at a global scope. Then,
        this method, actually matches all permissions rules which are applied
        to a specific collection and then it returns all permissions that
        are compatible and apply on the collection.
        """
        permission_path = ('.endpoint', 'permissions')
        collection = collection_path[-1]
        nu_columns = 6
        permission_doc = {}
        permissions = doc.doc_get(top_spec,
                                  collection_path[:-1] + permission_path) or []
        permissions = [[doc.parse_pattern(segment) for segment in row]
                       for row in permissions]
        for rule in permissions:
            doc.doc_set(permission_doc, rule[:-1], rule[-1])
        patterns = [[collection], [doc.ANY], [doc.ANY], [doc.ANY],
                    [doc.ANY]]
        matches = list(doc.doc_match_levels(
            permission_doc, patterns,
            expand_pattern_levels=range(nu_columns)))
        if not matches:
            return None
        return map((lambda x: x[1:]), matches)

    def generate_serializer(self, field_schema, name, model=None,
                            onmodel=False, model_serializers=None,
                            extra_serializers=None):
        """
        Generate a `Serializer` class to serve the given `field_schema`.

        There are two scenarios:

        * If `field_schema` only consists of model fields and `onmodel` flag
          is specified as True, then a `ModelSerializer` class is generated.
        * If `field_schema` consists of non-model fields or a mixture of
          model fields and non-model fields, then a `ContainerSerializer` class
          is created.
        """
        model_fields, extra_fields, sources = self._classify_fields(
            field_schema)
        if onmodel:
            assert model, ('You cannot create a model serializer without'
                           ' specifying its model')
            serializer = generate_model_serializer(
                name, model, model_fields, bases=model_serializers)
        else:
            serializer = generate_container_serializer(
                model_fields, extra_fields, name, model,
                instance_sources=sources,
                model_serializers=model_serializers,
                extra_serializers=extra_serializers)
        return serializer

    def construct_drf_collection(self, instance, spec, loc, context):
        """
        Constructor for `.drf_collection` predicate.

        It generates the required, `Serializer` class, and `ViewSet` class
        based on the field schema, actions, permissions and additional
        configuation (filter_fields, mixins) as specified on spec.
        """
        endpoint = loc[0]
        parent = context.get('parent_name')
        constructed = context.get('constructed')
        if '.collection' not in constructed:
            raise doc.DeferConstructor
        field_schema = doc.doc_get(instance, ('*',))
        actions = doc.doc_get(instance, ('.actions', self.ADAPTER_CONF)) or []
        model = self._get_or_import_model(loc[0] + '/' + parent,
                                          loc + ('model',),
                                          context.get('top_spec'))
        model_serializers = spec.pop('model_serializers', [])
        extra_serializers = spec.pop('serializers', [])
        serializer = self.generate_serializer(
            field_schema, parent, model=model,
            model_serializers=model_serializers,
            extra_serializers=extra_serializers)
        kwargs = {k: v for k, v in spec.iteritems() if k != 'model'}
        permissions = self.get_permissions(loc[:-1], context.get('top_spec'))
        view = generate_view(parent, serializer, model, actions=actions,
                             permissions=permissions, **kwargs)
        instance[self.ADAPTER_CONF] = view
        self.serializers[endpoint + '/' + parent] = serializer
        self.views[endpoint + '/' + parent] = view
        return instance

    def _classify_fields(self, field_schema):
        """
        Seperates the model fields fro the non-model fields.

        It also returns a dictionary of instance sources (if they are exist)
        for the non-model fields.
        """
        model_fields = {}
        extra_fields = {}
        instance_sources = {}
        for field_name, properties in field_schema.iteritems():
            onmodel = doc.doc_get(properties, ('.drf_field', 'onmodel'))
            if onmodel is None:
                onmodel = True
            field_path = (self.ADAPTER_CONF, 'field')
            instance_path = (self.ADAPTER_CONF, 'source')
            field = doc.doc_get(properties, field_path)
            if onmodel:
                model_fields[field_name] = field
            else:
                extra_fields[field_name] = field
            instance_sources[field_name] = doc.doc_get(properties,
                                                       instance_path)
        return model_fields, extra_fields, instance_sources

    def generate_nested_drf_field(self, instance, name, predicate_type, model,
                                  onmodel=True, **kwargs):
        """
        Generate a nested drf field, which is actually a `Serializer` class.
        """
        kwargs.update(self.get_default_properties(predicate_type, kwargs))
        field_schema = doc.doc_get(instance, (predicate_type,))
        many = predicate_type == '.structarray'
        model_serializers = kwargs.pop('model_serializers', [])
        extra_serializers = kwargs.pop('serializers', [])
        serializer = self.generate_serializer(
            field_schema, name, onmodel=onmodel,
            model_serializers=model_serializers,
            extra_serializers=extra_serializers, model=model)
        return serializer(many=many, **kwargs)

    def construct_identity_field(self, instance, spec, loc, context,
                                 predicate_type):
        """ Construct an `.identity` field. """
        collection_name = loc[1]
        drf_field = self.SERILIZERS_TYPE_MAPPING[predicate_type[1:]](
            view_name='%s-detail' % (loc[0] + '_' + collection_name))
        doc.doc_set(instance, (self.ADAPTER_CONF, 'field'), drf_field)
        return instance

    def get_default_properties(self, predicate_type, field_kwargs):
        default = {}
        for prop in self.PROPERTY_MAPPING.itervalues():
            if predicate_type != '.string' and prop == 'allow_blank':
                continue
            if predicate_type == '.boolean' and prop == 'allow_null':
                continue
            if not field_kwargs.get(prop):
                default[prop] = False
        return default

    def _generate_field(self, instance, name, predicate_type, model,
                        automated, **field_kwargs):
        if predicate_type in self.STRUCTURES:
            drf_field = self.generate_nested_drf_field(
                instance, name, predicate_type, model, onmodel=automated,
                **field_kwargs)
        else:
            # In case of a `.choices` field, we create a drf-field manually.
            if not automated or predicate_type == '.choices':
                field_kwargs.update(self.get_default_properties(
                    predicate_type, field_kwargs))
                drf_field = self.SERILIZERS_TYPE_MAPPING[predicate_type[1:]](
                    **field_kwargs)
            else:
                drf_field = field_kwargs
        return drf_field

    def _get_ref_params(self, instance, loc, top_spec, automated,
                        field_kwargs):
        """
        Get extra params needed to initialize a
        `serializers.HyperlinkedIdentityField`.
        """
        ref_kwargs = instance['.ref']
        many = ref_kwargs.get('many', False)
        ref = ref_kwargs['to']
        endpoint, collection = tuple(ref.split('/'))
        extra = {'view_name': '%s-detail' % (endpoint + '_' + collection)}
        if not automated:
            extra['many'] = many
            if not field_kwargs.get('read_only'):
                # In case it is not a read only field, specify its queryset.
                ref_model = self._get_or_import_model(
                    endpoint + '/' + collection,
                    loc[:1] + ('.drf_collection', 'model'), top_spec)
                extra['queryset'] = ref_model.objects.all()
        return extra

    def _get_extra_field_kwargs(self, predicate_type, instance, loc, context,
                                automated, field_kwargs):
        if predicate_type == '.ref':
            return self._get_ref_params(
                instance, loc, context.get('top_spec'), automated,
                field_kwargs)
        extra_params = self.get_extra_params(instance, predicate_type)
        if predicate_type == '.choices':
            # In case of a `.choices` field, we merge the parameters of
            # allowed and display into a list of tuples.
            allowed, display = (extra_params.pop('allowed'),
                                extra_params.pop('display'))
            extra_params['choices'] = zip(allowed, display) or allowed
        return extra_params

    def default_field_constructor(self, instance, spec, loc, context,
                                  predicate_type):
        """
        A common constructor for the drf fields.

        There are two cases:
        * If the field is a model field, then it does not initialize a
          `serializers.Field` object, but it stores all its properties in
          dictionary in order to be initialized later from the serializer.
        * If the field is a non-model field or its type is either `.struct`
          or `.structarry`, then the corresponding `serializers.Field` is
          contructed.

        Moreover, this method checks if the field conforms to the model
        configuations before being constructed.
        """
        model, automated = self.validate_model_configuration(
            instance, spec, loc, context, predicate_type)
        path = (self.ADAPTER_CONF,)
        instance_source = spec.pop('instance_source', None)
        onmodel = spec.get('onmodel', True)
        if instance_source and onmodel:
            raise utils.DRFAdapterException(
                '`instance_source` and `onmodel=True` are mutually'
                ' exclusive.', loc=loc)
        field_kwargs = {k: v for k, v in spec.iteritems() if k != 'onmodel'}
        field_kwargs.update(doc.doc_get(instance, path) or {})
        field_kwargs.update(self._get_extra_field_kwargs(
            predicate_type, instance, loc, context, automated, field_kwargs))
        doc.doc_set(instance, (self.ADAPTER_CONF, 'source'), instance_source)
        drf_field = self._generate_field(
            instance, context.get('parent_name'), predicate_type, model,
            automated and onmodel, **field_kwargs)
        doc.doc_set(instance, (self.ADAPTER_CONF, 'field'), drf_field)
        return instance

    def _get_or_import_model(self, collection, model_path, top_spec):
        """
        This function checks if a model of a collection is already specified
        and imported and retrieves it. If this is not the case, then it
        imports it and retrieves it.
        """
        if collection not in self.models:
            try:
                model = utils.import_object(
                    doc.doc_get(top_spec, model_path))
                self.models[collection] = model
            except ImportError as e:
                raise utils.DRFAdapterException(e.message, loc=model_path)
        else:
            model = self.models[collection]
        return model

    def validate_model_configuration(self, instance, spec, loc, context,
                                     predicate_type):
        """
        Validates that the instance, that is a field, conforms to the
        model configuration.

        For instance, a model field must correspond to a django model field.
        """
        onmodel = spec.get('onmodel', True)
        source = spec.get('source')
        parent_name = context.get('parent_name')
        top_spec = context.get('top_spec')
        model_path = loc[:2] + ('.drf_collection', 'model')
        collection = loc[1]
        full_collection_name = loc[0] + '/' + collection
        model = self._get_or_import_model(
            full_collection_name, model_path, top_spec)
        structures = {'.struct', '.structarray'}
        automated = False
        if onmodel:
            field_type = self.TYPE_MAPPING[predicate_type[1:]]
            if predicate_type == '.ref':
                _, model, automated = self.validate_ref(
                    instance, parent_name, loc, top_spec, source)
            else:
                model_field, model, automated = self.validate_model_field(
                    top_spec, parent_name, loc, field_type, source)
                if predicate_type in structures:
                    model = model_field.related_model
        return model, automated

    def construct_drf_field(self, instance, spec, loc, context):
        """
        Constructor of `.drf_field` predicate.

        This constructor validates the existence of a django model field to
        the extracted model class.

        In case of nested fields, e.g. `.struct`, `.structarray`, the field
        should be related to another model.
        """
        parent = context.get('parent_name')
        field_constructors = {
            '.identity': self.construct_identity_field,
        }
        all_constructors = context.get('all_constructors')
        constructed = context.get('constructed')
        if len(constructed) < len(all_constructors) - 1:
            raise doc.DeferConstructor
        type_predicate = self.extract_type(instance)
        if type_predicate is None:
            raise utils.DRFAdapterException(
                'Cannot construct drf field {!r} without specifying its'
                ' type'.format(parent), loc=loc)
        return field_constructors.get(
            type_predicate, self.default_field_constructor)(
                instance, spec, loc, context, type_predicate)

    def validate_ref(self, instance, name, loc, top_spec, source):
        """
        Validates that the referenced field is a foreign key to the same
        django model table as the model defined in the referenced collection
        of spec. Otherwise, an exception with explanatory message is raised.
        """
        ref = doc.doc_get(instance, ('.ref', 'to'))
        django_conf = self.get_constructor_params(top_spec, loc, [])
        model = self.extract_model(source or name, django_conf, loc)
        auto = True
        try:
            model_field = model._meta.get_field(source or name)
            endpoint, collection = tuple(ref.split('/'))
            path = (endpoint, collection, '.drf_collection', 'model')
            collection = endpoint + '/' + collection
            ref_model = self._get_or_import_model(collection, path, top_spec)
            model_attr = _validate_relational_field(
                name, ref_model, model_field, loc)
        except FieldDoesNotExist:
            auto = False
            model_attr = _validate_model_attribute(
                name, model, source or name, loc)
        return model_attr, model, auto

    def construct_type(self, instance, spec, loc, context, field_type=None):
        """
        Contructor for predicates that indicate the type of a field.

        This constructor produces the corresponding cerberus syntax for
        specifying the type of a field.
        """
        return instance

    def construct_property(self, instance, spec, loc, context, property_name):
        """
        Constuctor for predicates that indicate a property of a field,
        e.g. nullable, readonly, required, etc.

        This constructor generates the corresponding cerberus syntax. However,
        it requires field to be initialized, otherwise, construction is
        defered.
        """
        if property_name not in self.PROPERTY_MAPPING:
            raise utils.DRFAdapterException(
                'Unknown property {!r}'.format(property_name), loc=loc)
        self.init_adapter_conf(instance)
        instance[self.ADAPTER_CONF].update(
            {self.PROPERTY_MAPPING[property_name]: True})
        return instance

    def validate_model_field(self, spec, name, loc, django_field_type,
                             source=None):
        """
        Validate that a field specified in spec is field of the model
        given as input.
        """
        django_conf = self.get_constructor_params(spec, loc[:-1], [])
        model = self.extract_model(source or name, django_conf, loc)
        automated = True
        if model is None:
            raise utils.DRFAdapterException(
                'Invalid argument, model cannot be `None`.', loc=loc)
        try:
            model_field = model._meta.get_field(source or name)
            model_attr = _validate_model_type(name, model_field,
                                              django_field_type, loc)
        except FieldDoesNotExist:
            automated = False
            model_attr = _validate_model_attribute(
                name, model, source or name, loc)
        return model_attr, model, automated

    def get_constructor_params(self, spec, loc, params):
        """
        Get constructor params for all the constructors that represent a
        structure, e.g. `.struct`, `.collection`, etc.
        """
        for structure in self.STRUCTURES.keys():
            struct_doc = doc.doc_get(spec, loc[:-1]) or {}
            structure_params = doc.doc_get(
                struct_doc, (self.STRUCTURES[structure],)) or {}
            onmodel = structure_params.get('onmodel', True)
            if structure in struct_doc and onmodel:
                if structure == '.collection':
                    collection = '/'.join(loc[:2])
                    params.append(
                        (structure, {'model': self.models[collection]}))
                    continue
                source = structure_params.get('source')
                params.append((structure, {'source': source or loc[-2]}))
        if loc[:-1]:
            return self.get_constructor_params(spec, loc[:-1], params)
        return params

    def extract_model(self, related_field, django_conf, loc):
        """
        Exctact model according to the django configuration.

        However, if a field is related to another model, then the related model
        is extracted.
        """
        _, params = django_conf[0]
        if len(django_conf) > 1:
            return self.extract_related_model(
                params.get('source'), django_conf[1:], loc)
        return params.get('model', None)

    @handle_exception
    def extract_related_model(self, related_field, django_conf, loc=()):
        """
        Extracts related model based on given field. It also checks that
        given field is related to another model.
        """
        model = self.extract_model(related_field, django_conf, loc)
        related_field = model._meta.get_field(related_field)
        if related_field.related_model is None:
            raise utils.DRFAdapterException(
                'Field {!r} is not related with another model'.format(
                    related_field), loc=loc)
        return related_field.related_model
