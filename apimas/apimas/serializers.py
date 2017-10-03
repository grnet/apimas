import numbers
import uuid
import re
import types
from collections import Iterable, Mapping
from datetime import date, datetime
from urlparse import urlparse
from apimas import utils
from apimas.errors import ValidationError, InvalidInput, GenericFault


_SKIP = object()


def isnumeric(value):
    return isinstance(value, numbers.Number) or (
            isinstance(value, (str, unicode)) and value.isdigit())


def extract_value(obj, attr):
    """
    Tries to extract the value denoted by the second argument from the given
    object.

    * First, it tries to evaluate the `obj[attr]` expression.
    * Secondly, it tries to find any attribute named as `attr`.

    Args:
        obj: Object to extract its value.
        attr (str): An identifier used to extract the value from object.

    Raises:
        InvalidInput: if value cannot be extracted from the given object.
    """
    try:
        return obj[attr]
    except (KeyError, TypeError):
        try:
            return getattr(obj, attr)
        except AttributeError:
            raise InvalidInput(
                'Cannot access attribute {attr!r} from given object'.format(
                    attr=attr))


class BaseSerializer(object):
    """
    Class used to convert a value taken from a request into a python native
    value ready to be used for the business logic of an application and
    vice versa.

    Attributes:
        default: (Optional) Default deserialized value if `None` is found
            during deserialization.
        readonly (bool): `True` if value must not be deserialized; `False`
            otherwise.
        writeonly (bool): `True` if value must not be serialized; `False`
            otherwise.
        extractor (callablel): A callable used to extract the python native
            value from a given object during serialization.
    """
    def __init__(self, default=None, readonly=False, writeonly=False,
                 extractor=None, nullable=False, *args, **kwargs):
        assert not (readonly and writeonly), (
            '`readonly` and `writeonly` properties are mutually exclusive')
        self.default = default
        self.nullable = nullable
        self.readonly = readonly
        self.writeonly = writeonly
        if extractor:
            assert callable(extractor), ('extractor must be a callable')
        self.extractor = extractor

    def get_native_value(self, value):
        """ Gets the python native value from a given value. """
        raise NotImplementedError('get_native_value() must be implemented')

    def get_repr_value(self, value):
        """
        Gets the representative format of a value, ready to be easily
        serialized into a content type, e.g. JSON.
        """
        raise NotImplementedError('get_repr_value() must be implemented')

    def serialize(self, value):
        """
        Converts given value into a representative format.

        It skips this process if `writeonly` is set `True`.
        """
        if self.writeonly:
            return _SKIP
        value = self.extractor(value) if self.extractor else value
        return self.get_repr_value(value)

    def deserialize(self, value):
        """
        Converts given value into a python native value.

        It skips this process if `readonly` is set `True`.
        """
        if self.readonly:
            return _SKIP
        value = self.default if value is None else value
        return self.get_native_value(value)


class String(BaseSerializer):
    def _get_value(self, value):
        valid_types = (str, unicode)
        if self.nullable:
            valid_types += (types.NoneType,)

        if not isinstance(value, valid_types):
            msg = ('Field is not of type \'string\'. {type!r} found instead.')
            raise ValidationError(msg.format(type=type(value)))

        return value

    def get_repr_value(self, value):
        return self._get_value(value)

    def get_native_value(self, value):
        return self._get_value(value)


class UUID(BaseSerializer):
    def get_repr_value(self, value):
        return str(value)

    def get_native_value(self, value):
        raise NotImplementedError('deserialize() is not meaningful for'
                                  ' \'UUID\' field')


class Email(String):
    # http://bit.ly/RVerWq
    EMAIL_REGEX = re.compile(
        r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

    def _get_email(self, value):
        value = super(Email, self).get_repr_value(value)
        if not self.EMAIL_REGEX.match(value):
            raise ValidationError('Field is not a valid email')
        return value

    def get_repr_value(self, value):
        return self._get_email(value)

    def get_native_value(self, value):
        return self._get_email(value)


class Serial(BaseSerializer):
    """
    Serialize serial numbers.

    Deserialization is not meaningful for serials because the value is
    set automatically.
    """
    def get_repr_value(self, value):
        if isinstance(value, str) and not value.isdigit():
            raise ValidationError('Field is not an integer')
        return int(value)

    def get_native_value(self, value):
        raise NotImplementedError('deserialize() is not meaningful for'
                                  ' \'serial\' field')


class Number(BaseSerializer):
    """
    Serializes and deserializes a numeric value.

    Attributes:
        value_type: Type of numeric value, e.g. int, float, etc.

    Examples:
        >>> from apimas.serializers import Number
        >>> field = Number(value_type=int)
        >>> field.serialize('10')
        10
        >>> field = Number(value_type=float)
        >>> field.serialize('10')
        10.0
    """
    def _get_value(self, value):
        number_type = getattr(self, 'NUMBER_TYPE', None)
        if number_type is None:
            raise GenericFault('`NUMBER_TYPE` needs to be set')
        if isnumeric(value):
            return number_type(value)
        raise ValidationError('Field is not numeric.')

    def get_repr_value(self, value):
        return self._get_value(value)

    def get_native_value(self, value):
        return self._get_value(value)


class Integer(Number):
    """
    Serializes and deserializes a numeric value.

    Attributes:
        value_type: Type of numeric value, e.g. int, float, etc.

    Examples:
        >>> from apimas.serializers import Number
        >>> field = Number(value_type=int)
        >>> field.serialize('10')
        10
        >>> field = Number(value_type=float)
        >>> field.serialize('10')
        10.0
    """
    NUMBER_TYPE = int


class Float(Number):
    NUMBER_TYPE = float


class Boolean(BaseSerializer):
    TRUE_VALUES = {
        'true',
        'True',
        'TRUE',
        True,
        1,
    }

    FALSE_VALUES = {
        'false',
        'False',
        'FALSE',
        False,
        0,
    }

    def _get_bool_value(self, value):
        if value is None:
            return None
        if value in self.TRUE_VALUES:
            return True
        if value in self.FALSE_VALUES:
            return False
        msg = 'Field is not boolean. {type!r} found instead.'
        raise ValidationError(msg.format(val=type(value)))

    def serialize(self, value):
        try:
            return self._get_bool_value(value)
        except ValidationError:
            return bool(value)

    def get_native_value(self, value):
        return self._get_bool_value(value)


class Date(BaseSerializer):
    """
    It converts a python string representing a date into a python date object
    and vice versa.

    Attributes:
        date_format (str): (optional) String representing date format. If
            `None`, 'iso-8601' format is used.

    Examples:
        >>> from datetime import datetime
        >>> from apimas.serializers import Date
        >>> field = Date(date_format='%Y-%m')
        >>> value = field.deserialize('1994-09')
        >>> value
        datetime.datetime(1994, 9, 1, 0, 0)
        >>> field.serialize(value)
        '1994-09'
    """
    DEFAULT_FORMAT = '%Y-%m-%d'

    def __init__(self, date_format=None, *args, **kwargs):
        self.date_format = date_format or self.DEFAULT_FORMAT
        super(Date, self).__init__(*args, **kwargs)

    def get_repr_value(self, value):
        if not isinstance(value, (date, datetime)):
            msg = ('Field cannot be serialized. It is not a date object.'
                   ' {type!r} found instead.')
            raise ValidationError(msg.format(type=type(value)))
        try:
            return value.strftime(self.date_format)
        except ValueError as e:
            msg = ('Date object cannot be converted into string with '
                   ' the given format: {format!r}.')
            raise ValidationError(
                msg.format(format=self.date_format) + e.message)

    def get_native_value(self, value):
        try:
            return datetime.strptime(value, self.date_format)
        except ValueError as e:
            msg = ('String cannot be converted into a date object with'
                   ' the given format: {format!r}.')
            raise ValidationError(
                msg.format(format=self.date_format) + e.message)


class DateTime(Date):
    DEFAULT_FORMAT = '%Y-%m-%dT%H:%M:%S'


class Choices(BaseSerializer):
    """
    The internal value can be one of the allowed. Similarly, the displayed
    value can be the one mapped to the corresponding internal.

    Attributes:
        allowed (list): List of the allowed values. The type of these values
             must be one of the python base types: `str`, `int`, `float`,
             'bool', `unicode`.
        displayed (list): (optional) A list with the same length as `allowed`.
             The displayed value of the corresponding element of `allowed`
             list.
    Examples:
        >>> from apimas.serializers import Choices
        >>> field = Choices(allowed=['foo', 'bar'],
        ...                 displayed=['foo_displayed', 'bar_displayed'])
        >>> field.deserialize('foo')
        'foo'
        >>> field.serialize('foo')
        'foo_displayed'
    """
    ERROR_MESSAGE = 'Given value must be one of [{allowed!s}]'

    def __init__(self, allowed, displayed=None, *args, **kwargs):
        self.allowed = allowed
        self.displayed = displayed or allowed

        assert len(self.allowed) == len(self.displayed)
        self._values_map = {k: displayed[i]
                            for i, k in enumerate(self.allowed)}
        super(Choices, self).__init__(*args, **kwargs)

    def get_repr_value(self, value):
        value = self._values_map.get(value, value)
        if value not in self.displayed:
            msg = self.ERROR_MESSAGE.format(allowed=','.join(self.allowed))
            raise ValidationError(msg)
        return value

    def get_native_value(self, value):
        if value not in self.allowed:
            msg = self.ERROR_MESSAGE.format(allowed=','.join(self.allowed))
            raise ValidationError(msg)
        return value


class Identity(BaseSerializer):
    """
    Constructs the URL pointing to an entity.

    By default, it tries to extract an attribute named 'pk' from the object
    we want to serialize. Deserialization process is not meaningful because
    `identity` fields are `readonly`.

    Attributes:
        to (str): Collection path of an entity, e.g. api/foo.

    Examples:
        >>> from apimas.serializers import Identity
        >>> field = Identity(to='api/foo')
        >>> field.serialize({'pk': 'bar'})
        'api/foo/bar/'
    """
    TRAILING_SLASH = '/'

    def __init__(self, to, root_url=None, *args, **kwargs):
        to = to.strip(
            self.TRAILING_SLASH) + self.TRAILING_SLASH

        # In case `root_url` (e.g. http://localhost) is not given, then we
        # work only with the relative URL.
        self.absolute_url = utils.urljoin(root_url, to) if root_url \
            else None
        self.rel_url = to
        super(Identity, self).__init__(*args, **kwargs)

    def get_repr_value(self, value):
        if value is None:
            return value
        if isnumeric(value) \
            or isinstance(value, (str, unicode)) \
            or isinstance(value, uuid.UUID):
            return utils.urljoin(self.absolute_url or self.rel_url, str(value))
        try:
            return self.get_repr_value(
                extract_value(value, 'pk'))
        except AttributeError:
            raise ValidationError(
                'Cannot construct identity URL for the given value: {}'.format(
                    value))

    def get_native_value(self, value):
        raise NotImplementedError(
            'get_native_value() is not meaningful for \'.identity\' field')


class Ref(Identity):
    def get_native_value(self, value):
        if value is None:
            return None
        parsed_value = urlparse(value)
        parsed_url = urlparse(self.absolute_url or self.rel_url)
        _, match, suffix = parsed_value.path.partition(self.rel_url)
        issame = (parsed_value.scheme == parsed_url.scheme and
                  parsed_value.netloc == parsed_url.netloc)
        if not match or not suffix and not issame:
            msg = ('Given URL {!r} does not correspond to the collection'
                   ' of {!r}')
            raise ValidationError(msg.format(
                value, self.absolute_url or self.rel_url))
        return suffix.split(self.TRAILING_SLASH, 1)[0]


class File(BaseSerializer):
    def get_repr_value(self, value):
        return value.name

    def get_native_value(self, value):
        return value


class Struct(BaseSerializer):
    """
    Serializes and deserializes a compound of fields.

    Each field has a unique name and a specific serializer is used for
    its value conversion. In essence, this serializer is a compound of
    other serializers responsible to serialize/deserialize a number
    of fields.

    Args:
        schema (dict): A dictionary of serializers and internal names
            per field.

    Examples:
        >>> from apimas.serializers import Struct, String, Number
        >>> schema = {'foo': (String(), 'foo_bar'),
        ...           'bar': (Number(), 'bar_mapped')}
        >>> field = Struct(schema=schema)
        >>> field.deserialize({'foo': 'x', 'bar': 10})
        {'foo_mapped': 'x', 'bar_mapped': 10}
        >>> field.serialize('foo_mapped': 'x', 'bar_mapped': 10})
        {'foo': 'x', 'bar': 10}
    """

    def __init__(self, schema, *args, **kwargs):
        self.schema = schema
        super(Struct, self).__init__(*args, **kwargs)

    def get_repr_value(self, obj):
        if obj is None:
            return obj
        serialized_data = {}
        for field_name, (serializer, map_to) in self.schema.iteritems():
            value = extract_value(obj, map_to)
            try:
                ser_value = serializer.serialize(value)
            except ValidationError as e:
                msg = 'Cannot serialize field {field!r}. ' + e.message
                raise ValidationError(msg.format(field=field_name))
            if ser_value is _SKIP:
                continue
            serialized_data[field_name] = ser_value
        return serialized_data

    def get_native_value(self, value):
        if value is None:
            return value
        deserialized_data = {}
        for k, v in value.iteritems():
            serializer, map_to = self.schema.get(k)
            if serializer is None:
                raise ValidationError('Invalid field {!r}'.format(k))
            try:
                value = serializer.deserialize(v)
            except ValidationError as e:
                msg = 'Cannot serialize field {field!r}. ' + e.message
                raise ValidationError(msg.format(field=k))
            if value is _SKIP:
                continue
            deserialized_data[map_to] = value

        return deserialized_data


class List(BaseSerializer):
    """
    Serializes and deserializes a list of items.

    Note that the same serializer should be used to serialize/deserialize all
    items.

    Attributes:
        serializer: Serializer used to serialize/deserialize all items.

    Examples:
        >>> from apimas.serializers import List, String
        >>> field = List(String())
        >>> field.deserialize(['foo', 'bar'])
        ['foo', 'bar']
        >>> field.deserialize(['foo', 'bar'])
        ['foo', 'bar']
    """
    def __init__(self, serializer, *args, **kwargs):
        self.serializer = serializer
        super(List, self).__init__(*args, **kwargs)

    def get_repr_value(self, value):
        if value is None:
            return value
        if not isinstance(value, Iterable) or isinstance(value, Mapping):
            raise ValidationError('Given value is not a list-like object')
        return [self.serializer.get_repr_value(v) for v in value]

    def get_native_value(self, value):
        if value is None:
            return value
        if not isinstance(value, Iterable) or isinstance(value, Mapping):
            raise ValidationError('Given value is not a list-like object')
        return [self.serializer.get_native_value(v) for v in value]
