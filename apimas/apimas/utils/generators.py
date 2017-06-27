from cStringIO import StringIO
from copy import deepcopy
from datetime import datetime
import os
import random
import zipfile
from faker import Factory
from pytz import timezone as py_timezone
from apimas import documents as doc
from apimas.utils import urljoin
from apimas.errors import InvalidInput
from apimas.decorators import after


fake = Factory.create()


def generate_integer(upper=10, lower=0):
    return random.randint(lower, upper)


def generate_float(upper=10, lower=0):
    return random.uniform(lower, upper)


def generate_string(max_length=255):
    size = random.randint(1, max_length)
    return fake.pystr(max_chars=size)


generate_email = fake.email


def generate_choices(choices=None):
    return random.choice(choices or [])


def generate_boolean():
    return random.choice([True, False])


class DateGenerator(object):
    """
    Date generator.

    Args:
        native (bool): `True` if a python date object is generated; `False`
            otherwise.
    """
    DEFAULT_FORMATS = ['%Y-%m-%d']

    def __init__(self, native):
        self.native = native

    def __call__(self, date_formats=None, **kwargs):
        """
        Generates a random python date object or a string representing a date
        based on the allowed date formats.

        Args:
            date_formats (list): (optional) List of allowed string formats
                which are used to represent date.
        """
        date_obj = fake.date_object()
        if self.native:
            return date_obj
        date_formats = date_formats or self.DEFAULT_FORMATS
        return datetime.strftime(date_obj, random.choice(date_formats))


class DateTimeGenerator(DateGenerator):
    DEFAULT_FORMATS = ['%Y-%m-%dT%H:%M:%S']

    def __call__(self, date_formats=None, timezone='UTC'):
        """
        Generates a random python datetime object or a string representing a
        datetime based on the allowed date formats and the timezone.

        Args:
            date_formats (list): (optional) List of allowed string formats
                which are used to represent date.
            timezone (str): (optional) Timezone info.
        """
        tzinfo = None
        if timezone:
            tzinfo = py_timezone(fake.timezone()) if timezone is True\
                else py_timezone(timezone)
        date_obj = fake.date_time(tzinfo=tzinfo)
        if self.native:
            return date_obj
        date_formats = date_formats or self.DEFAULT_FORMATS
        return datetime.strftime(date_obj, random.choice(date_formats))


def generate_fake_file(size=8, archived=False):
    """
    Generates a file-like object using `cStringIO` library.

    Args:
        size (int): (optional) Size of the generated file in bytes.
        archived (bool): `True` if generated file should be archived.
    """
    if archived:
        return generate_zipfile(files=1, size=size)
    content = os.urandom(size)
    buff = StringIO()
    buff.write(content)
    return buff


def generate_zipfile(files, size=8):
    """
    Generates a fake a zip file which includes the number of specified
    files.

    The files included in zip file are also fake.

    Args:
        files: A positive integer which specifies the number of files
            included in zip file or a list of file names. In the former case
            random files names are generated.
        size (int):  (optional) Size of every file in zip in bytes.
    """
    files_type = type(files)
    if files_type not in [int, list]:
        raise InvalidInput('"files" must be either an integer or a list of'
                           ' file names')
    if files_type is int:
        if files <= 0:
            raise InvalidInput('Number of files must be positive')
        files = [fake.file_name() for _ in range(files)]
    zip_file = generate_fake_file()
    with zipfile.ZipFile(zip_file, mode='w',
                         compression=zipfile.ZIP_DEFLATED) as zf:
        for filename in files:
            fil = generate_fake_file(size=size)
            zf.writestr(filename, fil.getvalue())
            fil.close()
    return zip_file


def generate_ref(to, root_url=None):
    random_pk = random.randint(1, 10)
    ref = to.strip('/') + '/'
    if root_url:
        return urljoin(ref, str(random_pk))
    else:
        return urljoin(root_url, ref, str(random_pk))


class RequestGenerator(object):
    """
    Generator of random Request data.

    It reads from specification to construct the appropriate generators and
    field names.

    Args:
        spec (dict): Specification of a collection.

    Examples:
        >>> SPEC = {
        ...     '*': {
        ...         'foo': {
        ...             '.string': {}
        ...         },
        ...         'bar': {
        ...             '.integer': {}
        ...         },
        ...         'ignored': {
        ...             '.integer': {},
        ...             '.readonly': {},
        ...         }
        ...     }
        ... }
        >>> from apimas.utils.generators import RequestGenerator
        >>> generator = RequestGenerator(SPEC)
        >>> generator.construct()
        {'bar': 7, 'foo': u'PtkvOypcrcxaWfqouPWVbxFZzvaHMJrVSlJ'}
    """

    RANDOM_GENERATORS = {
        '.string': generate_string,
        '.text': generate_string,
        '.email': generate_email,
        '.integer': generate_integer,
        '.float': generate_float,
        '.datetime': DateTimeGenerator(native=False),
        '.date': DateGenerator(native=False),
        '.boolean': generate_boolean,
        '.file': generate_fake_file,
        '.choices': generate_choices,
        '.ref': generate_ref,
    }

    COMMON_FIELDS = {
        '.string',
        '.text',
        '.email',
        '.integer',
        '.float',
        '.datetime',
        '.date',
        '.boolean',
        '.file',
        '.choices',
        '.ref',
    }

    _SKIP = object()

    def __init__(self, spec, **meta):
        self.spec = spec.get('*')
        self._constructors = {
            'struct': self._struct,
            'readonly': self._readonly,
            'array of': self._array_of,
            'serial': self._serial,
            'default': self._default
        }
        self.meta = meta
        self._constructors.update(
            {k[1:]: self._common_constructor(k) for k in self.COMMON_FIELDS})

    def _default(self, context):
        return context.instance

    def _common_constructor(self, field_type):
        @after(['.readonly'])
        def generate(context):
            if context.instance is self._SKIP:
                return None
            if field_type == '.ref':
                root_url = self.meta.get('root_url')
                return generate_ref(
                    **dict(context.spec, **{'root_url': root_url}))
            return self.RANDOM_GENERATORS[field_type](**context.spec)
        return generate

    @after(['.readonly'])
    def _serial(self, context):
        return None

    def _readonly(self, context):
        return self._SKIP

    def _compound(self, instance, spec):
        if instance is self._SKIP:
            return None
        assert spec is not None
        return spec

    @after(['.readonly'])
    def _struct(self, context):
        return self._compound(context.instance, context.spec)

    @after(['.readonly'])
    def _array_of(self, context):
        return [self._compound(context.instance, context.spec)]

    def construct(self):
        """
        Generates random data based on specification.

        Returns:
            dict: A dictionary of random data per field.
        """
        spec = deepcopy(self.spec)
        # Remove readonly fields.
        for k, v in spec.items():
            if '.readonly' in v:
                del spec[k]

        instance = doc.doc_construct(
            {}, spec, constructors=self._constructors,
            allow_constructor_input=False, autoconstruct='default',
            construct_spec=True)
        return instance
