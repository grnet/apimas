from copy import deepcopy
from collections import Iterable, Mapping
from apimas import documents as doc
from apimas import serializers as srs
from apimas.components import BaseProcessor
from apimas.errors import InvalidSpec
from apimas.decorators import last


class BaseSerialization(BaseProcessor):
    """
    Base processor used for serialization purposes.

    It uses the Serializer classes provided by apimas and reads from
    specification to construct them accordingly.
    """

    TYPE_SERIALIZERS = {
        '.struct': srs.Struct,
        '.ref': srs.Ref,
        '.serial': srs.Serial,
        '.integer': srs.Number,
        '.biginteger': srs.Number,
        '.float': srs.Number,
        '.string': srs.String,
        '.text': srs.String,
        '.choices': srs.Choices,
        '.email': srs.Email,
        '.boolean': srs.Boolean,
        '.datetime': srs.DateTime,
        '.date': srs.Date,
        '.file': srs.File,
        '.identity': srs.Identity,
    }

    COMMON_FIELDS = {
        '.ref',
        '.serial',
        '.integer',
        '.float',
        '.string',
        '.text',
        '.choices',
        '.email',
        '.boolean',
        '.datetime',
        '.date',
        '.file',
        '.identity',
    }

    KWARGS_MAPPER = {
        '.datetime': {
            'format': {
                'to': 'date_format',
                'default': None,
            }
        }
    }

    EXTRA_KWARGS = {
        '.integer': {
            'value_type': int
        },
        '.float': {
            'value_type': float,
        }
    }

    def __init__(self, spec):
        self.spec = {k: v for k, v in spec.get('*').iteritems()
                     if not k.startswith('.')}
        if spec is None:
            msg = 'Processor {!r}: Node \'*\' of given spec is empty'
            raise InvalidSpec(msg.format(self.name))

        # Declare constructors of predicates understood by processor.
        self._constructors = {
            'struct': self._struct,
            'array of': self._array_of,
            'writeonly': self._writeonly,
            'readonly': self._readonly,
            'default': self._default,
        }
        self._constructors.update(
            {k[1:]: self._type_constructor(k) for k in self.COMMON_FIELDS})
        self.serializers = self._construct()

    def _default(self, context):
        return context.instance

    def _construct_property(self, instance, key):
        doc = {
            key: True
        }
        if not instance:
            return doc
        instance.update(doc)
        return instance

    def _writeonly(self, context):
        return self._construct_property(context.instance, 'writeonly')

    def _readonly(self, context):
        return self._construct_property(context.instance, 'readonly')

    def _type_constructor(self, field_type):
        @last
        def construct_type(context):
            serializer = self.TYPE_SERIALIZERS[field_type]
            kwargs = {}
            kwargs.update(self.EXTRA_KWARGS.get(field_type, {}))
            kwargs.update(context.spec)
            kwargs.update(context.instance)
            if field_type == '.serial':
                kwargs.update({'readonly': True})
            return serializer(**kwargs)
        return construct_type

    @last
    def _struct(self, context):
        if context.spec is None:
            raise InvalidSpec('empty struct found')
        kwargs = {'schema': context.spec}
        serializer = srs.Struct(**kwargs)
        return serializer

    @last
    def _array_of(self, context):
        if context.spec is None:
            raise ('Array of undefined type')
        kwargs = {'serializer': context.spec}
        return srs.List(**kwargs)

    def _construct(self):
        spec = deepcopy(self.spec)
        instance = doc.doc_construct(
            {}, spec, constructors=self._constructors,
            allow_constructor_input=False, autoconstruct=True,
            construct_spec=True)
        return instance

    def get_serializer(self, data):
        if isinstance(data, Iterable) and not isinstance(data, Mapping):
            return srs.List(srs.Struct(self.serializers))
        return srs.Struct(self.serializers)

    def perform_serialization(self, context_data):
        raise NotImplementedError(
            'perform_serialization() must be implemented')

    def process(self, collection, url, action, context):
        """
        Reads data which we want to serialize from context, it performs
        serialization on them and finally it saves output to context.
        """
        context_data = self.read(context)
        output = self.perform_serialization(context_data)
        if output is not None:
            self.write(output, context)


class DeSerialization(BaseSerialization):
    """
    Processor responsible for the deserialization of data.
    """
    name = 'apimas.components.processors.DeSerialization'

    READ_KEYS = {
        'data': 'request/content',
    }

    WRITE_KEYS = {
        'data': 'store/' + name + '/deserialized_data',
    }

    def perform_serialization(self, context_data):
        data = context_data['data']
        if data is None:
            return None
        serializer = self.get_serializer(data)
        return {'data': serializer.deserialize(data)}


class Serialization(BaseSerialization):
    """
    Processor responsible for the serialization of data.
    """
    name = 'apimas.components.processors.Serialization'

    READ_KEYS = {
        'data': 'response/content',
    }
    WRITE_KEYS = {
        'data': 'response/content',
    }

    def perform_serialization(self, context_data):
        data = context_data['data']
        if data is None:
            return None
        serializer = self.get_serializer(data)
        return {'data': serializer.serialize(data)}
