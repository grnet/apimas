from copy import deepcopy
from collections import Iterable, Mapping
from apimas import documents as doc, serializers as srs, utils, auth
from apimas.components import BaseProcessor
from apimas.errors import UnauthorizedError, InvalidSpec, ValidationError
from apimas.constructors import Flag, Object, Dummy
from apimas.validators import CerberusValidator


def _post_hook(context, instance):
    # If the parent node is `.array of` constructor, then simply return the
    # constructed instance. Otherwise, we need to pass the information
    # regarding the source of the field.
    if context.parent_name == '.array of=':
        return instance
    node = doc.doc_get(context.top_spec, context.loc[:-1])
    meta = node.get('.meta', {})
    source = meta.get('source', context.parent_name)
    return (instance, source)


class BaseSerialization(BaseProcessor):
    """
    Base processor used for serialization purposes.

    It uses the Serializer classes provided by apimas and reads from
    specification to construct them accordingly.
    """

    CONSTRUCTORS = {
        'ref':        Object(srs.Ref, kwargs_spec=True, kwargs_instance=True,
                             last=True, post_hook=_post_hook),
        'serial':     Object(srs.Serial, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'integer':    Object(srs.Integer, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'float':      Object(srs.Float, kwargs_spec=True, kwargs_instance=True,
                             last=True, post_hook=_post_hook),
        'string':     Object(srs.String, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'uuid':       Object(srs.UUID, kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'text':       Object(srs.String, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'choices':    Object(srs.Choices, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'email':      Object(srs.Email, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'boolean':    Object(srs.Boolean, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'datetime':   Object(srs.DateTime, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             kwargs_spec_mapping={'format': 'date_format'},
                             post_hook=_post_hook),
        'date':       Object(srs.Date, kwargs_spec=True, kwargs_instance=True,
                             kwargs_spec_mapping={'format': 'date_format'},
                             last=True, post_hook=_post_hook),
        'file':       Object(srs.File, kwargs_spec=True, kwargs_instance=True,
                             last=True, post_hook=_post_hook),
        'identity':   Object(srs.Identity, kwargs_spec=True,
                             kwargs_instance=True, last=True,
                             post_hook=_post_hook),
        'struct':     Object(srs.Struct, args_spec=True,
                             args_spec_name='schema', kwargs_instance=True,
                             last=True, post_hook=_post_hook),
        'array of':   Object(srs.List, args_spec=True,
                             args_spec_name='serializer', kwargs_instance=True,
                             last=True, post_hook=_post_hook),
        'readonly':   Flag('readonly'),
        'writeonly':  Flag('writeonly'),
        'nullable':   Flag('nullable'),
        'default':    Dummy(),
    }

    def __init__(self, collection, spec, **meta):
        super(BaseSerialization, self).__init__(collection, spec, **meta)
        self.spec = self.spec.get('*')
        if self.spec is None:
            msg = 'Processor {!r}: Node \'*\' of given spec is empty'
            raise InvalidSpec(msg.format(self.name))

        self.root_url = self.meta.get('root_url')
        self.serializers = self._construct()

    def _construct(self):
        spec = deepcopy(self.spec)
        ref_paths = doc.doc_search(spec, '.ref')
        for ref_path in ref_paths:
            ref_spec = doc.doc_get(spec, ref_path)
            ref_spec.update({'root_url': self.root_url})
        instance = doc.doc_construct(
            {}, spec, constructors=self.CONSTRUCTORS,
            allow_constructor_input=False, autoconstruct='default',
            construct_spec=True)
        return instance

    def _update_nested_serializers(self, allowed_fields, serializer_info):
        """
        Helper function to update and filter nested serializers in case of
        structural fields.
        """
        serializer, map_to = serializer_info
        if isinstance(serializer, srs.List):
            serializer = serializer.serializer
        assert isinstance(serializer, srs.Struct), (
            'Unexpected Error: You declared field {!r} in your permission'
            ' rules as a structural one, but the field is not a compound one.')
        allowed_serializers = self._get_serializers(
            allowed_fields, serializers=serializer.schema)
        serializer.schema = allowed_serializers
        return (serializer, map_to)

    def _get_serializers(self, allowed_fields, serializers=None):
        """
        This method gets a subset of constructed serializers.

        Actually, this method gets only serializers which are responsible for
        handling the allowed fields defined in the context of request.
        """
        serializers = serializers or self.serializers
        if allowed_fields is doc.ANY:
            return serializers
        allowed_fields = utils.paths_to_dict(allowed_fields)
        allowed_serializers = {}
        for k, v in allowed_fields.iteritems():
            serializer_info = serializers.get(k)
            assert serializer_info is not None, (
                'Unexpected error: Not any serializer found for field {!r}.'
                ' Perhaps, there is a typo in permission rules or'
                ' specification.'.format(k))
            if not v:
                # We reach at the end of hierarchy so we add serializer to our
                # list
                allowed_serializers[k] = serializer_info
                continue

            # At this point, we presume that we have nested serializers,
            # i.e. `.struct`, or an array of structs.
            allowed_serializers[k] = self._update_nested_serializers(
                v.keys(), serializer_info)
        return allowed_serializers

    def get_serializer(self, data, allowed_fields):
        if allowed_fields is not None:
            serializers = self._get_serializers(allowed_fields)
        else:
            serializers = self.serializers
        if isinstance(data, Iterable) and not isinstance(data, Mapping):
            return srs.List(srs.Struct(serializers))
        return srs.Struct(serializers)

    def perform_serialization(self, context_data):
        raise NotImplementedError(
            'perform_serialization() must be implemented')

    def process(self, collection, url, action, context):
        """i
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
        'allowed_fields': 'store/permissions/allowed_fields',
    }

    WRITE_KEYS = {
        'data': 'store/' + name + '/deserialized_data',
    }

    def perform_serialization(self, context_data):
        data = context_data['data']
        if data is None:
            return None
        allowed_fields = context_data['allowed_fields']
        serializer = self.get_serializer(data, allowed_fields)
        return {'data': serializer.deserialize(data)}


class Serialization(BaseSerialization):
    """
    Processor responsible for the serialization of data.
    """
    name = 'apimas.components.processors.Serialization'

    READ_KEYS = {
        'data': 'response/content',
        'allowed_fields': 'store/permissions/allowed_fields',
    }

    WRITE_KEYS = {
        'data': 'response/content',
    }

    def perform_serialization(self, context_data):
        data = context_data['data']
        if data is None:
            return None
        allowed_fields = context_data['allowed_fields']
        serializer = self.get_serializer(data, allowed_fields)
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

    def __init__(self, collection, spec, **meta):
        super(CerberusValidation, self).__init__(collection, spec, **meta)

        # Attach constructor for '.validator' predicate.
        self.constructors.update({'validator': self._validator_constructor})
        self.spec = self.spec.get('*')
        if self.spec is None:
            msg = 'Processor {!r}: Node \'*\' of given spec is empty'
            raise InvalidSpec(msg.format(self.name))
        schema = self._construct()

        # Remove validators from the field schema in order to attach them
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

        If validation failed, methods should raise
        `apimas.errors.ValidationError`.
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


def _get_verifier(verifier_type):
    def func(context):
        meta = context.top_spec.get('.meta', {})
        verifier = meta.get(verifier_type)
        if verifier is None:
            raise InvalidSpec('Verifier is missing.', loc=context.loc)
        verifier = utils.import_object(verifier)
        if not callable(verifier):
            raise InvalidSpec('Verifier must be a callable', loc=context.loc)
        return {'verifier': verifier}
    return func


def protected(context):
    return context.spec


class Authentication(BaseProcessor):
    """
    Processor for performing authentication based on a selected method.
    """
    name = 'apimas.components.processors.Authentication'

    READ_KEYS = {
        'headers': 'request/meta/headers'
    }

    WRITE_KEYS = (
        'store/auth/identity',
    )

    CONSTRUCTORS = {
        'token':     Object(auth.TokenAuthentication, kwargs_spec=True,
                            pre_hook=_get_verifier('token_verifier')),
        'basic':     Object(auth.BasicAuthentication, kwargs_spec=True,
                            pre_hook=_get_verifier('basic_verifier')),
        'djoser':    Object(auth.DjoserAuthentication, kwargs_spec=True,
                            pre_hook=_get_verifier('djoser_verifier')),
        'protected': protected,
        'default':   Dummy()
    }

    def __init__(self, collection, spec, **meta):
        super(Authentication, self).__init__(collection, spec)
        self.spec.update({'.meta': meta})
        if spec.get('.protected=') is not None:
            # Construct an authentication backend only if `.protected=` is
            # present.
            self.auth = self._construct()
        else:
            self.auth = None

    def _construct(self):
        spec = deepcopy(self.spec)
        instance = doc.doc_construct(
            {}, spec, constructors=self.CONSTRUCTORS,
            allow_constructor_input=False, autoconstruct='default',
            construct_spec=True)
        return instance

    def process(self, collection, url, action, context):
        if self.auth is None:
            # If there is not any constructed authentication backend, then
            # we presume that the collection is not protrected, so we skip
            # this processor.
            return
        data = self.read(context)
        try:
            identity = self.auth.authenticate(data['headers'])
        except UnauthorizedError:
            # Provide the appropriate headers, so that handler can read them
            # later.
            auth_headers = getattr(self.auth, 'AUTH_HEADERS',
                                   None)
            if auth_headers:
                response_headers = {'WWW-Authenticate': auth_headers}
                path = 'response/meta/headers'
                self.save(context, path, response_headers)
            raise
        self.write((identity,), context)


class ClientAuthentication(Authentication):
    READ_KEYS = {
        'credentials': 'request/meta/credentials'
    }

    WRITE_KEYS = (
        'request/meta/headers',
    )

    CONSTRUCTORS = {
        'token':     Object(auth.ClientTokenAuthentication, kwargs_spec=True),
        'basic':     Object(auth.ClientBasicAuthentication, kwargs_spec=True),
        'protected': protected,
        'default':   Dummy()
    }

    def process(self, collection, url, action, context):
        if self.auth is None:
            return

        credentials = self.read(context)['credentials']
        try:
            headers = self.auth.attach_to_headers(**credentials)
        except TypeError:
            raise UnauthorizedError('Missing or invalid credentials')
        self.write((headers,), context)
