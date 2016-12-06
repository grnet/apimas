import copy
import inspect
from collections import OrderedDict
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.utils import model_meta
from apimas.modeling.core import exceptions as ex
from apimas.modeling.core.documents import ANY
from apimas.modeling.adapters.drf import utils


class AbortException(Exception):
    pass


def lookup_value(field_name, source, instance):
    """
    Similar to Python's built in `getattr(instance, attr)`,
    but takes a list of nested attributes, instead of a single attribute.
    Also accepts either attribute lookup on objects or dictionary lookups.
    """
    if instance is None:
        return instance

    if source is None:
        raise ex.ApimasException(
            'Cannot retrieve instance value for the field `%s` given a'
            ' NoneType source' % (field_name))

    attrs = source.split(',')
    for attr in attrs:
        func = utils.import_object(attr)
        if callable(func):
            instance = func(instance)
        else:
            raise ex.ApimasException(
                'Cannot retrieve instance value of the'
                ' field %s given the source `%s`' % (field_name, source))
    return instance


def get_paths(serializer_fields):
    paths = []
    for k, v in serializer_fields.iteritems():
        fields = getattr(v, 'fields', None)
        if fields is None:
            child = getattr(v, 'child', None)
            if child is None:
                nested_paths = []
            else:
                nested_paths = get_paths(child.fields)
        else:
            nested_paths = get_paths(fields)
        paths.extend([k + '/' + p for p in nested_paths] or [k])
    return paths


class ContainerSerializer(serializers.BaseSerializer):
    model_ser_cls = None

    ser_cls = None

    def __init__(self, *args, **kwargs):
        super(ContainerSerializer, self).__init__(*args, **kwargs)
        self.model_ser = None
        self.ser = None
        self.build_serializers()
        self.contained_sers = [self.ser, self.model_ser]

    def _validate_configuration(self):
        meta_cls = getattr(self, 'Meta', None)
        if meta_cls is None:
            raise utils.DRFAdapterException('`Meta` class cannot be found')
        model_fields = getattr(meta_cls, 'model_fields', [])
        fields = getattr(meta_cls, 'extra_fields', [])
        if not (fields or model_fields):
            raise utils.DRFAdapterException(
                '`extra_fields` and `model_fields` attributes are unspecified')
        if not (self.model_ser_cls or self.ser_cls):
            raise utils.DRFAdapterException(
                'A `ContainerSerializer` must define a `ModelSerializer` class'
                ' or a `Serializer class')
        if not (self.model_ser_cls or self.ser_cls):
            raise utils.DRFAdapterException(
                'A `ContainerSerializer` must include a ModelSerializer'
                ' and Serializer class')
        if self.model_ser_cls:
            mro = inspect.getmro(self.model_ser_cls)
            if serializers.HyperlinkedModelSerializer not in mro:
                raise utils.DRFAdapterException(
                    'A model serializer class must inherit'
                    ' `serializers.ModelSerializer`')
        if self.ser_cls:
            mro = inspect.getmro(self.ser_cls)
            if serializers.BaseSerializer not in mro:
                raise utils.DRFAdapterException(
                    'A serializer class must implement'
                    ' `serializers.BaseSerializer`')
        return model_fields, fields

    def build_serializers(self):
        model_fields, fields = self._validate_configuration()
        self.model_ser = self._build_serializer(
            self.model_ser_cls,
            fields=model_fields, instance=self.instance)
        self.ser = self._build_serializer(
            self.ser_cls, fields=fields, instance=self.instance)

    def _build_serializer(self, serializer_class, fields=None, instance=None):
        if serializer_class is None:
            return None
        kwargs = {}
        if hasattr(self, 'initial_data'):
            initial_data = self.initial_data or {}
            data = {k: v for k, v in initial_data.iteritems()
                    if k in fields}
            kwargs['data'] = data
        return serializer_class(
            context=self._context, partial=self.partial, instance=instance, **kwargs)

    def is_valid(self, raise_exception=False):
        self._errors = {}
        for serializer in self.contained_sers:
            if serializer is None:
                continue
            isvalid = serializer.is_valid(raise_exception=False)
            if not isvalid:
                self._errors.update(serializer._errors)
        if self._errors and raise_exception:
            raise ValidationError(self.errors)
        return not bool(self._errors)

    def save(self, **kwargs):
        if self.ser:
            instance_a = self.ser.save(**kwargs)
        else:
            instance_a = None
        if self.model_ser:
            instance_b = self.model_ser.save(**kwargs)
        else:
            instance_b = None
        assert not (instance_a and instance_b), (
            'Creation of multiple instances is not supported.')
        self.instance = instance_a or instance_b
        return self.instance

    def perform_action(self, validated_data, instance=None):
        method_name = 'update' if instance else 'create'
        output = [None, None]
        for i, serializer in enumerate(self.contained_sers):
            if serializer is None:
                continue

            method = getattr(serializer, method_name)
            kwargs = {'validated_data': validated_data[i]}
            if instance:
                kwargs['instance'] = instance
            output[i] = method(**kwargs)
        assert not (output[0] and output[1])
        return output[0] or output[1]

    def create(self, validated_data):
        return self.perform_action(validated_data)

    def update(self, instance, validated_data):
        return self.perform_action(validated_data, instance=instance)

    def to_representation(self, instance):
        data = {}
        if self.ser:
            data.update(self.ser.to_representation(instance))
        if self.model_ser:
            data.update(self.model_ser.to_representation(instance))
        return data

    def to_internal_value(self, data):
        output = []
        for serializer in self.contained_sers:
            output.append(None if serializer is None else
                          serializer.to_internal_value(data))
        return tuple(output)

    @property
    def fields(self):
        fields = {}
        for serializer in self.contained_sers:
            if serializer is None:
                continue
            fields.update(serializer.fields)
        return fields

    @property
    def data(self):
        self._data = {}
        if self.instance is not None:
            return self.to_representation(
                self.instance)
        for serializer in self.contained_sers:
            if serializer:
                self._data.update(serializer.data)
        return self._data

    def get_attribute(self, instance):
        try:
            return super(ContainerSerializer, self).get_attribute(instance)
        except AttributeError:
            return instance


class ApimasSerializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        super(ApimasSerializer, self).__init__(
            *args, **kwargs)
        self.adapt_fields_to_rules()

    def adapt_fields_to_rules(self):
        request = self._context.get('request')
        if not request:
            return
        readonly_fields = self._context['request'].parser_context.get(
            'non_writable_fields', [])
        permitted_fields = self._context['request'].parser_context.get(
            'permitted_fields', [])
        serializer_fields = self.fields
        for field in readonly_fields:
            self.set_field_property(
                field.split('/'), serializer_fields, 'read_only')
        if permitted_fields == ANY:
            return
        non_permitted_fields = set(
            get_paths(serializer_fields)) - set(permitted_fields)
        for field in non_permitted_fields:
            self.set_field_property(field.split('/'), serializer_fields,
                                    'write_only')

    def set_field_property(self, segments, fields, property_key):
        if len(segments) == 1:
            field = fields.get(segments[0])
            if field:
                setattr(field, property_key, True)
            return
        serializer = fields.get(segments[0])
        fields = serializer.child.fields\
            if type(serializer) is serializers.ListSerializer else\
            serializer.fields
        return self.set_field_property(
            segments[1:], fields, property_key)

    def get_attribute(self, instance):
        try:
            return super(ApimasSerializer, self).get_attribute(instance)
        except AttributeError:
            return instance

    def _update_model_data(self, additional_data, data=None):
        if data is None:
            data = self.validated_data
        model_data = []
        for _, v in data.iteritems():
            if isinstance(v, dict):
                model_data.append(v)
            if isinstance(v, tuple):
                node_extra_data, node_model_data = v
                if node_model_data is not None:
                    model_data.append(node_model_data)
                else:
                    node_model_data = self._get_model_data(
                        additional_data, node_extra_data)
                    if node_model_data is not None:
                        model_data.append(node_model_data)
        assert 0 <= len(model_data) <= 1, 'Diverse model_data found'
        if model_data:
            model_data[0].update(additional_data)

    def save(self, **kwargs):
        self._update_model_data(kwargs)
        try:
            self.instance = super(ApimasSerializer, self).save()
            return self.instance
        except AbortException:
            return None

    def _set_new_instance(self, new_instance, instance, drf_field, value):
        out = drf_field.update(instance, value) if instance\
            else drf_field.create(value)
        if out and new_instance:
            raise ex.ApimasException('Found multiple instances')
        if not new_instance:
            return out

    def perform_action(self, validated_data, instance=None):
        new_instance = None
        for k, v in validated_data.iteritems():
            drf_field = self.fields[k]
            if isinstance(drf_field, serializers.BaseSerializer):
                try:
                    new_instance = self._set_new_instance(
                        new_instance, instance, drf_field, v)
                except AbortException:
                    pass
            elif instance:
                self.update_non_model_field(drf_field, instance, v,
                                            validated_data)
            else:
                self.create_non_model_field(drf_field, v, validated_data)
        if new_instance is None:
            raise AbortException
        return new_instance

    def create(self, validated_data):
        return self.perform_action(validated_data)

    def update(self, instance, validated_data):
        return self.perform_action(validated_data, instance=instance)

    def create_non_model_field(self, field, value, context):
        return value

    def update_non_model_field(self, field, instance, value, context):
        return value

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = self._readable_fields
        for field in fields:
            try:
                instance_sources = getattr(self, 'instance_sources', {})
                attribute = lookup_value(
                    field.field_name,
                    instance_sources.get(field.field_name),
                    instance)
            except (ImportError, ex.ApimasException):
                try:
                    attribute = field.get_attribute(instance)
                except serializers.SkipField:
                    continue

            # We skip `to_representation` for `None` values so that fields
            # do not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            check_for_none = attribute.pk if isinstance(
                attribute, serializers.PKOnlyObject) else attribute
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret


class ApimasModelSerializer(serializers.HyperlinkedModelSerializer,
                            ApimasSerializer):

    def get_fields(self):
        """
        Return the dict of field names -> field instances that should be
        used for `self.fields` when instantiating the serializer.
        """
        if self.url_field_name is None:
            self.url_field_name = api_settings.URL_FIELD_NAME

        assert hasattr(self, 'Meta'), (
            'Class {serializer_class} missing "Meta" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        assert hasattr(self.Meta, 'model'), (
            'Class {serializer_class} missing "Meta.model" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        if model_meta.is_abstract_model(self.Meta.model):
            raise ValueError(
                'Cannot use ModelSerializer with Abstract Models.'
            )

        declared_fields = copy.deepcopy(self._declared_fields)
        model = getattr(self.Meta, 'model')
        depth = getattr(self.Meta, 'depth', 0)

        if depth is not None:
            assert depth >= 0, "'depth' may not be negative."
            assert depth <= 10, "'depth' may not be greater than 10."

        # Retrieve metadata about fields & relationships on the model class.
        info = model_meta.get_field_info(model)
        field_names = self.get_field_names(declared_fields, info)

        # Determine any extra field arguments and hidden fields that
        # should be included
        extra_kwargs = self.get_extra_kwargs()
        extra_kwargs, hidden_fields = self.get_uniqueness_extra_kwargs(
            field_names, declared_fields, extra_kwargs
        )

        # Determine the fields that should be included on the serializer.
        fields = OrderedDict()

        for field_name in field_names:
            # If the field is explicitly declared on the class then use that.
            if field_name in declared_fields:
                fields[field_name] = declared_fields[field_name]
                continue

            extra_field_kwargs = extra_kwargs.get(field_name, {})
            source = extra_field_kwargs.get('source') or field_name
            # Determine the serializer field class and keyword arguments.
            field_class, field_kwargs = self.build_field(
                source, info, model, depth
            )

            # Include any kwargs defined in `Meta.extra_kwargs`
            field_kwargs = self.include_extra_kwargs(
                field_kwargs, extra_field_kwargs
            )

            # Create the serializer field.
            fields[field_name] = field_class(**field_kwargs)

        # Add in any hidden fields.
        fields.update(hidden_fields)

        return fields

    def save(self, **kwargs):
        return super(ApimasModelSerializer, self).save(**kwargs)


def generate_container_serializer(model_fields, extra_fields, name,
                                  model, model_serializers=None,
                                  extra_serializers=None,
                                  instance_sources=None):
    model_serializer = generate_serializer(
        model_fields, name, model_serializers, model=model)
    serializer = generate_serializer(
        extra_fields, name, extra_serializers, model=None,
        instance_sources=instance_sources)
    content = {'extra_fields': extra_fields.keys(),
               'model_fields': model_fields.keys()}
    meta_cls = type('Meta', (object,), content)
    content = {
        'model_ser_cls': model_serializer,
        'ser_cls': serializer,
        'Meta': meta_cls,
    }
    return type(name, (ContainerSerializer,), content)


def generate_serializer(field_properties, name, bases=None, model=None,
                        instance_sources=None):
    if not field_properties:
        return None
    content = {}
    for field_name, properties in field_properties.iteritems():
        content[field_name] = properties
    meta_cls_content = {'fields': field_properties.keys()}
    base_classes = {
        True: ApimasModelSerializer,
        False: ApimasSerializer,
    }
    if model:
        meta_cls_content['model'] = model
    else:
        content['instance_sources'] = instance_sources
    custom_bases = map(utils.LOAD_CLASS, bases or [])
    base_cls = tuple(custom_bases) + (base_classes[bool(model)],)
    meta_cls = type('Meta', (object,), meta_cls_content)
    cls_content = dict({'Meta': meta_cls}, **content)
    return type(name, base_cls, cls_content)
