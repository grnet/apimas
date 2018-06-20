import numbers
import decimal
import uuid
import re
from collections import Iterable, Mapping
from datetime import date, datetime
from urlparse import urlparse
from apimas import utils
from apimas.errors import ValidationError, InvalidInput, AccessDeniedError


Nothing = object()


def isnumeric(value):
    return isinstance(value, numbers.Number) or (
            isinstance(value, (str, unicode)) and value.isdigit())


class DataConverter(object):
    """
    Class used to convert a value taken from a request into a python native
    value ready to be used for the business logic of an application and
    vice versa.

    Attributes:
        noread (bool): `True` if value must not be exported.
        nullable (bool): `True` if value can be None.
    """
    def __init__(self, noread=False, nullable=False):
        self.noread = noread
        self.nullable = nullable

    def get_native_value(self, value, permissions, single):
        """ Gets the python native value from a given value. """
        raise NotImplementedError('get_native_value() must be implemented')

    def get_repr_value(self, value, permissions, single):
        """
        Gets the representative format of a value, ready to be easily
        serialized into a content type, e.g. JSON.
        """
        raise NotImplementedError('get_repr_value() must be implemented')

    def export_data(self, value, permissions, single=False, toplevel=False):
        """
        Converts given value into a representative format.
        """
        if not permissions:
            return Nothing

        if not toplevel and self.noread:
            return Nothing

        if value is None:
            return None

        return self.get_repr_value(value, permissions, single)

    def import_data(self, value, permissions, single=False):
        """
        Converts given value into a python native value.
        """
        if value is Nothing:
            return Nothing
        elif not permissions:
            raise AccessDeniedError(
                "You do not have permission to write field")

        if value is None:
            if self.nullable:
                return None
            raise ValidationError("Field cannot be None")

        return self.get_native_value(value, permissions, single)


class String(DataConverter):
    def _get_value(self, value):
        valid_types = (str, unicode)
        if not isinstance(value, valid_types):
            msg = ('Field is not of type \'string\'. {type!r} found instead.')
            raise ValidationError(msg.format(type=type(value)))

        return value

    def get_repr_value(self, value, permissions, single):
        return self._get_value(value)

    def get_native_value(self, value, permissions, single):
        return self._get_value(value)


class UUID(DataConverter):
    def get_repr_value(self, value, permissions, single):
        return str(value)

    def get_native_value(self, value, permissions, single):
        raise NotImplementedError('deserialize() is not meaningful for'
                                  ' \'UUID\' field')


class Email(String):
    # http://bit.ly/RVerWq
    EMAIL_REGEX = re.compile(
        r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

    def _get_email(self, value, permissions, single):
        value = super(Email, self).get_repr_value(value, permissions, single)
        if not self.EMAIL_REGEX.match(value):
            raise ValidationError('Field is not a valid email')
        return value

    def get_repr_value(self, value, permissions, single):
        return self._get_email(value, permissions, single)

    def get_native_value(self, value, permissions, single):
        return self._get_email(value, permissions, single)


class Serial(DataConverter):
    """
    Serialize serial numbers.

    Deserialization is not meaningful for serials because the value is
    set automatically.
    """
    def get_repr_value(self, value, permissions, single):
        if isinstance(value, str) and not value.isdigit():
            raise ValidationError('Field is not an integer')
        return int(value)

    def get_native_value(self, value, permissions, single):
        return self.get_repr_value(value, permissions, single)


class Number(DataConverter):
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
            raise InvalidInput('`NUMBER_TYPE` needs to be set')
        if isnumeric(value):
            return number_type(value)

        raise ValidationError('Field is not numeric.')

    def get_repr_value(self, value, permissions, single):
        return self._get_value(value)

    def get_native_value(self, value, permissions, single):
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


class Decimal(DataConverter):
    def __init__(self, decimal_places=None, **kwargs):
        if decimal_places is None:
            raise InvalidInput("'decimal_places' must be set.")

        self.decimal_places = decimal_places
        self.quantizer = decimal.Decimal(10) ** (-decimal_places)
        super(Decimal, self).__init__(**kwargs)

    def get_repr_value(self, value, permissions, single):
        if not isinstance(value, decimal.Decimal):
            raise InvalidInput("Value must be of type Decimal.")
        return str(value.quantize(self.quantizer))

    def get_native_value(self, value, permissions, single):
        return decimal.Decimal(value).quantize(self.quantizer)


class Boolean(DataConverter):
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
        if value in self.TRUE_VALUES:
            return True
        if value in self.FALSE_VALUES:
            return False
        msg = 'Field is not boolean. {typ!r} found instead.'
        raise ValidationError(msg.format(typ=type(value)))

    def get_repr_value(self, value, permissions, single):
        try:
            return self._get_bool_value(value)
        except ValidationError:
            return bool(value)

    def get_native_value(self, value, permissions, single):
        return self._get_bool_value(value)


class Date(DataConverter):
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

    def __init__(self, date_format=None, **kwargs):
        self.date_format = date_format or self.DEFAULT_FORMAT
        super(Date, self).__init__(**kwargs)

    def get_repr_value(self, value, permissions, single):
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

    def get_native_value(self, value, permissions, single):
        try:
            return datetime.strptime(value, self.date_format)
        except ValueError as e:
            msg = ('String cannot be converted into a date object with'
                   ' the given format: {format!r}.')
            raise ValidationError(
                msg.format(format=self.date_format) + e.message)


class DateTime(Date):
    DEFAULT_FORMAT = '%Y-%m-%dT%H:%M:%S'


class Choices(DataConverter):
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
    ERROR_MESSAGE = 'Given value must be one of [{values!s}]'

    def __init__(self, allowed, displayed=None, **kwargs):
        self.allowed = allowed
        self.displayed = displayed or allowed

        assert len(self.allowed) == len(self.displayed)
        self.to_native = dict(zip(self.displayed, self.allowed))
        self.from_native = dict(zip(self.allowed, self.displayed))
        super(Choices, self).__init__(**kwargs)

    def get_repr_value(self, value, permissions, single):
        try:
            return self.from_native[value]
        except KeyError:
            msg = self.ERROR_MESSAGE.format(values=','.join(self.allowed))
            raise ValidationError(msg)

    def get_native_value(self, value, permissions, single):
        try:
            return self.to_native[value]
        except KeyError:
            msg = self.ERROR_MESSAGE.format(values=','.join(self.displayed))
            raise ValidationError(msg)


class Identity(DataConverter):
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

    def __init__(self, to, root_url, **kwargs):
        to = to.strip(
            self.TRAILING_SLASH) + self.TRAILING_SLASH

        self.rel_url = utils.urljoin(root_url, to) if root_url else to
        self.parsed_rel_url = urlparse(self.rel_url)
        super(Identity, self).__init__(**kwargs)

    def get_repr_value(self, value, permissions, single):
        if isnumeric(value) \
            or isinstance(value, (str, unicode)) \
            or isinstance(value, uuid.UUID):
            return utils.urljoin(self.rel_url, str(value))

    def get_native_value(self, value, permissions, single):
        raise NotImplementedError(
            'get_native_value() is not meaningful for \'.identity\' field')


class Ref(Identity):
    def get_native_value(self, value, permissions, single):
        if isinstance(value, numbers.Number):
            return str(value)

        if not isinstance(value, basestring):
            raise ValidationError('Ref is neither number nor string')

        parsed_value = urlparse(value)
        if not parsed_value.netloc:
            # It's not a URL; assume it's a plain id
            return value

        _, match, suffix = parsed_value.path.partition(
            self.parsed_rel_url.path)
        issame = (parsed_value.scheme == self.parsed_rel_url.scheme and
                  parsed_value.netloc == self.parsed_rel_url.netloc)
        if not match or not suffix or not issame:
            msg = ('Given URL {!r} does not correspond to the collection'
                   ' of {!r}')
            raise ValidationError(msg.format(
                value, self.rel_url))

        return suffix.split(self.TRAILING_SLASH, 1)[0]


class File(DataConverter):
    def get_repr_value(self, value, permissions, single):
        return value.name

    def get_native_value(self, value, permissions, single):
        return value


def pick_converter(converter, importing):
    if importing:
        return converter.import_data
    return converter.export_data


class Struct(DataConverter):
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

    def __init__(self, schema, flat=False, **kwargs):
        self.schema = schema
        self.flat = flat
        if flat and len(self.schema) != 1:
            raise InvalidInput(
                'Flat collections must specify exactly one field')
        super(Struct, self).__init__(**kwargs)

    def get_dict_values(self, value, permissions, single, importing):
        data = {}
        for field_name, field_schema in self.schema.iteritems():
            field_permissions = permissions.get(field_name)
            field_value = value.get(field_name, Nothing)
            func = pick_converter(field_schema['converter'], importing)
            try:
                computed_value = func(field_value, field_permissions, single)
            except ValidationError as e:
                msg = 'Cannot serialize field {field!r}. ' + e.message
                raise ValidationError(msg.format(field=field_name))

            if computed_value is not Nothing:
                data[field_name] = computed_value

        return data

    def get_repr_value(self, value, permissions, single):
        if not isinstance(value, dict):
            raise ValidationError("Must be a dict")

        value = self.get_dict_values(
            value, permissions, single, importing=False)

        if self.flat:
            key = self.schema.keys()[0]
            value = value[key]
        return value

    def get_native_value(self, value, permissions, single):
        if not self.flat and not isinstance(value, dict):
            raise ValidationError("Must be a dict")

        if self.flat:
            key = self.schema.keys()[0]
            value = {key: value}

        input_keys = set(value.keys())
        permitted_keys = set(permissions.keys())
        disallowed_keys = input_keys - permitted_keys
        if disallowed_keys:
            raise AccessDeniedError(
                "Writing fields %s is not allowed" % disallowed_keys)

        return self.get_dict_values(value, permissions, single, importing=True)


class List(DataConverter):
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
    def __init__(self, converter, **kwargs):
        self.converter = converter
        super(List, self).__init__(**kwargs)

    def get_list_elems(self, value, permissions, single, importing):
        func = pick_converter(self.converter, importing)
        if single:
            return func(value, permissions, single)

        if not isinstance(value, Iterable) or isinstance(value, Mapping):
            raise ValidationError('Given value is not a list-like object')

        return [func(elem, permissions, single) for elem in value]

    def get_repr_value(self, value, permissions, single):
        return self.get_list_elems(value, permissions, single, importing=False)

    def get_native_value(self, value, permissions, single):
        return self.get_list_elems(value, permissions, single, importing=True)
