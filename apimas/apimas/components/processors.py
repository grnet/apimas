from copy import deepcopy
from collections import Iterable, Mapping
from apimas import documents as doc
from apimas import serializers as srs
from apimas.components import BaseProcessor
from apimas.errors import InvalidSpec
from apimas.constructors import Flag, Object


class BaseSerialization(BaseProcessor):
    """
    Base processor used for serialization purposes.

    It uses the Serializer classes provided by apimas and reads from
    specification to construct them accordingly.
    """

    CONSTRUCTORS = {
        'ref':        Object(srs.Ref, kwargs_spec=True, kwargs_instance=True,
                             last=True),
        'serial':     Object(srs.Serial, kwargs_spec=True,
                             kwargs_instance=True, last=True),
        'integer':    Object(srs.Integer, kwargs_spec=True,
                             kwargs_instance=True, last=True),
        'float':      Object(srs.Float, kwargs_spec=True, kwargs_instance=True,
                             last=True),
        'string':     Object(srs.String, kwargs_spec=True,
                             kwargs_instance=True, last=True),
        'text':       Object(srs.String, kwargs_spec=True,
                             kwargs_instance=True, last=True),
        'choices':    Object(srs.Choices, kwargs_spec=True,
                             kwargs_instance=True, last=True),
        'email':      Object(srs.Email, kwargs_spec=True,
                             kwargs_instance=True, last=True),
        'boolean':    Object(srs.Boolean, kwargs_spec=True,
                             kwargs_instance=True, last=True),
        'datetime':   Object(srs.DateTime, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             kwargs_spec_mapping={'format': 'date_format'}),
        'date':       Object(srs.Date, kwargs_spec=True, kwargs_instance=True,
                             kwargs_spec_mapping={'format': 'date_format'},
                             last=True),
        'file':       Object(srs.File, kwargs_spec=True, kwargs_instance=True,
                             last=True),
        'identity':   Object(srs.Identity, kwargs_spec=True,
                             kwargs_instance=True, last=True),
        'struct':     Object(srs.Struct, args_spec=True,
                             args_spec_name='schema', kwargs_instance=True,
                             last=True),
        'array of':   Object(srs.List, args_spec=True,
                             args_spec_name='serializer', kwargs_instance=True,
                             last=True),
        'readonly':   Flag('readonly'),
        'writeonly':  Flag('writeonly')
    }

    def __init__(self, spec):
        self.spec = {k: v for k, v in spec.get('*').iteritems()
                     if not k.startswith('.')}
        if spec is None:
            msg = 'Processor {!r}: Node \'*\' of given spec is empty'
            raise InvalidSpec(msg.format(self.name))

        self.serializers = self._construct()

    def _construct(self):
        spec = deepcopy(self.spec)
        instance = doc.doc_construct(
            {}, spec, constructors=self.CONSTRUCTORS,
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
