import copy
import inspect
from collections import OrderedDict
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.utils import model_meta
from rest_framework.utils.serializer_helpers import ReturnDict
from apimas.modeling.core import exceptions as ex
from apimas.modeling.core.documents import ANY
from apimas.modeling.adapters.drf import utils


def lookup_value(field_name, source, instance):
    """
    Get the actual value of a non-model field from the specified source.

    The `source` is expected to be a string that indicates the location of
    a callable.

    Subsequently, this function imports this callable. This callable takes
    the instance a parameter and it must return the python value of this
    field.
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
    """
    This class represents a `ContainerSerializer`.

    A `ContainerSerializer` consists of two child serializer, that is an
    `ModelSerializer` for saving model data, and a `Serializer` which is
    responsible for non-model data.

    This class is not actually responsible for the saving, serializing,
    deserializing and validation of data. This is responsibility of child
    serializers. The `ContainerSerializer`, however, it combines the output of
    child serializers.
    """
    model_ser_cls = None

    ser_cls = None

    def __init__(self, *args, **kwargs):
        super(ContainerSerializer, self).__init__(*args, **kwargs)
        self.model_ser = None
        self.ser = None
        self.build_serializers()
        # Bind child serializers to the parent
        if self.ser is not None:
            self.ser.bind(field_name='', parent=self)
        if self.model_ser is not None:
            self.model_ser.bind(field_name='', parent=self)
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
            # Route initial data to the corresponding child serializer, e.g.
            # model data --> ModelSerializer.
            initial_data = self.initial_data or {}
            data = {k: v for k, v in initial_data.iteritems()
                    if k in fields}
            kwargs['data'] = data
        return serializer_class(
            context=self._context, partial=self.partial, instance=instance,
            **kwargs)

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

    def perform_action(self, validated_data, instance=None, **kwargs):
        method_name = 'update' if instance else 'create'
        output = [None, None]
        for i, serializer in enumerate(self.contained_sers):
            if serializer is None:
                continue

            method = getattr(serializer, method_name)
            method_kwargs = {'validated_data': validated_data[i]}
            if isinstance(serializer, ApimasModelSerializer):
                validated_data[i].update(kwargs)
            else:
                method_kwargs.update(kwargs)
            if instance:
                method_kwargs['instance'] = instance
            output[i] = method(**method_kwargs)
        assert not (output[0] and output[1])
        return output[0] or output[1]

    def create(self, validated_data, **kwargs):
        return self.perform_action(validated_data, **kwargs)

    def update(self, instance, validated_data, **kwargs):
        return self.perform_action(validated_data, instance=instance, **kwargs)

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
        self._fields = {}
        for serializer in self.contained_sers:
            if serializer is None:
                continue
            self._fields.update(serializer.fields)
        return self._fields

    @property
    def validated_data(self):
        self._validated_data = {}
        for serializer in self.contained_sers:
            if serializer is None:
                continue
            self._validated_data.update(serializer.validated_data)
        return self._validated_data

    @property
    def data(self):
        self._data = {}
        if self.instance is not None:
            return self.to_representation(
                self.instance)
        for serializer in self.contained_sers:
            if serializer:
                self._data.update(serializer.data)
        return ReturnDict(self._data, serializer=self)

    def get_attribute(self, instance):
        return instance

    def __iter__(self):
        for field in self.fields.values():
            yield self[field.field_name]

    def __getitem__(self, key):
        field = self.fields[key]
        value = self.data.get(key)
        error = self.errors.get(key) if hasattr(self, '_errors') else None
        if isinstance(field, serializers.Serializer):
            return serializers.NestedBoundField(field, value, error)
        return serializers.BoundField(field, value, error)


class ApimasSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super(ApimasSerializer, self).__init__(
            *args, **kwargs)
        self.adapt_fields_to_rules()

    def adapt_fields_to_rules(self):
        request = self._context.get('request')
        if not request:
            return
        writable_fields = self._context['request'].parser_context.get(
            'writable_fields', ANY)
        accessible_fields = self._context['request'].parser_context.get(
            'accesible_fields', ANY)
        serializer_fields = self.fields
        serializer_field_paths = set(get_paths(serializer_fields))
        non_accessible_fields = [] if isinstance(accessible_fields, type(ANY))\
            else serializer_field_paths - set(accessible_fields)
        non_writable_fields = [] if isinstance(writable_fields, type(ANY))\
            else serializer_field_paths - set(writable_fields)
        for field in non_accessible_fields:
            self.set_field_property(field.split('/'), serializer_fields,
                                    'write_only')
        for field in non_writable_fields:
            self.set_field_property(field.split('/'), serializer_fields,
                                    'read_only')

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

    def save(self, **kwargs):
        ismodel = isinstance(self, ApimasModelSerializer)

        assert not hasattr(self, 'save_object'), (
            'Serializer `%s.%s` has old-style version 2 `.save_object()` '
            'that is no longer compatible with REST framework 3. '
            'Use the new-style `.create()` and `.update()` methods instead.' %
            (self.__class__.__module__, self.__class__.__name__)
        )

        assert hasattr(self, '_errors'), (
            'You must call `.is_valid()` before calling `.save()`.'
        )

        assert not self.errors, (
            'You cannot call `.save()` on a serializer with invalid data.'
        )

        # Guard against incorrect use of `serializer.save(commit=False)`
        assert 'commit' not in kwargs, (
            "'commit' is not a valid keyword argument to the 'save()' method. "
            "If you need to access data before committing to the database then "
            "inspect 'serializer.validated_data' instead. "
            "You can also pass additional keyword arguments to 'save()' if you "
            "need to set extra attributes on the saved model instance. "
            "For example: 'serializer.save(owner=request.user)'.'"
        )

        assert not hasattr(self, '_data'), (
            "You cannot call `.save()` after accessing `serializer.data`."
            "If you need to access data before committing to the database then "
            "inspect 'serializer.validated_data' instead. "
        )

        if ismodel:
            validated_data = dict(
                list(self.validated_data.items()) +
                list(kwargs.items())
            )
        else:
            validated_data = self.validated_data

        if self.instance is not None:
            self.instance = self.update(self.instance, validated_data)\
                if ismodel else self.update(self.instance, validated_data,
                                            **kwargs)
            if ismodel:
                assert self.instance is not None, (
                    '`update()` did not return an object instance.'
                )
        else:
            self.instance = self.create(validated_data) if ismodel\
                else self.create(validated_data, **kwargs)
            if ismodel:
                assert self.instance is not None, (
                    '`create()` did not return an object instance.'
                )

        return self.instance

    def _set_new_instance(self, new_instance, instance, drf_field, value,
                          **kwargs):
        out = drf_field.update(instance, value, **kwargs) if instance\
            else drf_field.create(value, **kwargs)
        if out and new_instance:
            raise ex.ApimasException('Found multiple instances')
        if not new_instance:
            return out

    def perform_action(self, validated_data, instance=None, **kwargs):
        new_instance = None
        for k, v in validated_data.iteritems():
            drf_field = self.fields[k]
            if isinstance(drf_field, serializers.BaseSerializer):
                value = self._set_new_instance(
                    new_instance, instance, drf_field, v, **kwargs)
                if value:
                    new_instance = value
            elif instance:
                self.update_non_model_field(drf_field, instance, v,
                                            validated_data)
            else:
                self.create_non_model_field(drf_field, v, validated_data)
        return new_instance or self.instance

    def create(self, validated_data, **kwargs):
        return self.perform_action(validated_data, **kwargs)

    def update(self, instance, validated_data, **kwargs):
        return self.perform_action(validated_data, instance=instance,
                                   **kwargs)

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


def generate_container_serializer(model_fields, extra_fields, name,
                                  model, model_serializers=None,
                                  extra_serializers=None,
                                  instance_sources=None):
    """
    Generates a `ContainerSerializer`. It also generates the required
    child serializer based on the given `model_fields` and `extra_fields`.
    """
    model_serializer = generate_model_serializer(
        name, model, model_fields, bases=model_serializers)
    serializer = generate_serializer(
        name, extra_fields, bases=extra_serializers,
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


def generate_model_serializer(name, model, model_fields, bases=None):
    """
    Generates a `ModelSerializer` given the model_fields.

    The specified `model_fields` is a tuple of model fields properties and
    the already created drf_fields. The former are passed to the `Meta` class
    of serializer in order to be created afterwards, whereas the latter are
    specified directly to the serializer class.
    """
    field_properties, drf_fields = classify_model_fields(
        model_fields)
    if not (field_properties or drf_fields):
        return None
    drf_fields = drf_fields or {}
    meta_cls_content = {
        'model': model,
        'fields': drf_fields.keys() + field_properties.keys(),
        'extra_kwargs': field_properties,
    }
    cls_content = {
        field_name: serializer
        for field_name, serializer in drf_fields.iteritems()
    }
    custom_bases = map(utils.LOAD_CLASS, bases or [])
    base_cls = tuple(custom_bases) + (ApimasModelSerializer,)
    meta_cls = type('Meta', (object,), meta_cls_content)
    cls_content['Meta'] = meta_cls
    return type(name, base_cls, cls_content)


def generate_serializer(name, drf_fields, bases=None,
                        instance_sources=None):
    if not drf_fields:
        return None
    content = {}
    meta_cls_content = {'fields': drf_fields.keys()}
    content = {
        field_name: serializer
        for field_name, serializer in drf_fields.iteritems()
    }
    content['instance_sources'] = instance_sources
    custom_bases = map(utils.LOAD_CLASS, bases or [])
    base_cls = tuple(custom_bases) + (ApimasSerializer,)
    meta_cls = type('Meta', (object,), meta_cls_content)
    cls_content = dict({'Meta': meta_cls}, **content)
    return type(name, base_cls, cls_content)


def classify_model_fields(model_fields):
    """ Seperate already initialized drf_fields from the rest. """
    drf_fields = {}
    field_properties = {}
    for field_name, value in model_fields.iteritems():
        if isinstance(value, serializers.Field):
            drf_fields[field_name] = value
        else:
            assert isinstance(value, dict)
            field_properties[field_name] = value
    return field_properties, drf_fields
