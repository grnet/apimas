from copy import deepcopy
from collections import Iterable, Mapping
from apimas import documents as doc, serializers as srs, utils
from apimas.components import BaseProcessor
from apimas.errors import InvalidSpec, ValidationError
from apimas.constructors import Flag, Object, Dummy
from apimas.validators import CerberusValidator


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
        'writeonly':  Flag('writeonly'),
        'default':    Dummy(),
    }

    def __init__(self, collection, spec):
        super(BaseSerialization, self).__init__(collection, spec)
        self.spec = self.spec.get('*')
        if self.spec is None:
            msg = 'Processor {!r}: Node \'*\' of given spec is empty'
            raise InvalidSpec(msg.format(self.name))

        self.serializers = self._construct()

    def _construct(self):
        spec = deepcopy(self.spec)
        instance = doc.doc_construct(
            {}, spec, constructors=self.CONSTRUCTORS,
            allow_constructor_input=False, autoconstruct='default',
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


class CerberusValidation(BaseProcessor):
    """
    Processor for validating request data using Cerberus
    tool (http://docs.python-cerberus.org/en/stable/).
    """
    name = 'apimas.components.processors.CerberusValidation'

    constructors = {
        'ref':        Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'string'}),
        'integer':    Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'integer'}),
        'float':      Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'float'}),
        'string':     Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'string'}),
        'text':       Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'string'}),
        'choices':    Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'choices'}),
        'email':      Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'email'}),
        'boolean':    Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'boolean'}),
        'datetime':   Object(dict, kwargs_instance=True,
                             pre_hook=lambda x: {'type': 'datetime'}),
        'date':       Object(dict, kwargs_instance=True, kwargs_spec=True,
                             pre_hook=lambda x: {'type': 'date'}),
        'datetime':   Object(dict, kwargs_instance=True, kwargs_spec=True,
                             pre_hook=lambda x: {'type': 'datetime'}),
        'file':       Object(dict, kwargs_instance=True, kwargs_spec=True),
        'struct':     Object(dict, kwargs_instance=True, args_spec=True,
                             args_spec_name='schema',
                             pre_hook=lambda x: {'type': 'dict'}),
        'array of':   Object(dict, kwargs_instance=True, args_spec=True,
                             args_spec_name='schema',
                             pre_hook=lambda x: {'type': 'list'}),
        'readonly':   Flag('readonly'),
        'required':   Flag('required'),
        'nullable':   Flag('nullable'),
        'default':    Dummy(),
    }

    READ_KEYS = DeSerialization.WRITE_KEYS

    def __init__(self, collection, spec):
        super(CerberusValidation, self).__init__(collection, spec)

        # Attach constructor for '.validator' predicate.
        self.constructors.update({'validator': self._validator_constructor})
        self.spec = self.spec.get('*')
        if self.spec is None:
            msg = 'Processor {!r}: Node \'*\' of given spec is empty'
            raise InvalidSpec(msg.format(self.name))
        schema = self._construct()

        # Remove validators from the field schema in order to attach it
        # one level above.
        global_validators = schema.pop('validator', [])

        self.validation_schema = {
            'data': {
                'type': 'dict',
                'schema': schema,
                'validator': global_validators
            }
        }

    def _construct(self):
        instance = doc.doc_construct(
            {}, self.spec, constructors=self.constructors,
            allow_constructor_input=False, autoconstruct='default',
            construct_spec=True)
        return instance

    def _validator_constructor(self, context):
        """
        Constuctor for `.validator` predicate.

        This constructor is provided by the
        `apimas.components.processors.CerberusValidation` processor for the
        invocation of custom validators.

        These validators can be performed on field level or on top level
        (i.e. validating all data).

        The signature of custom validators should be the following:
            - (loc, value)

        where `loc` is the location of the node being validated at spec and
        `value` is the runtime value of it based on the request data.

        If validation failed, methods should raise `apimas.errors.ValidationError`.
        """
        field_location = self.collection + ('*',) + context.loc[:-1]
        while field_location[-1].startswith('.'):
            # Strip predicates from current location.
            field_location = field_location[:-1]

        def to_cerberus(func):
            def cerberus_validator_wrapper(field, value, error):
                try:
                    func(field_location, value)
                except ValidationError as e:
                    error(field, e.message)
            return cerberus_validator_wrapper

        funcs = context.spec
        if not isinstance(funcs, list):
            msg = 'A list of callables is expected, not {!r}'
            raise InvalidSpec(msg.format(type(funcs)), loc=context.loc)
        cerberus_funcs = [to_cerberus(utils.import_object(func))
                          for func in funcs]
        context.instance.update({'validator': cerberus_funcs})
        return context.instance

    def process(self, collection, url, action, context):
        """
        It reads from request data and it applies Cerberus validation based
        on the validation schema constructed during object initialization.

        If validation fails, then `apimas.errors.ValidationError` is raised.
        """
        data = self.read(context)
        validator = CerberusValidator(self.validation_schema)
        isvalid = validator.validate(data)
        if not isvalid:
            data_errors = validator.errors.pop('data')
            raise ValidationError(data_errors)
