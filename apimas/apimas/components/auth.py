import docular

from apimas.errors import UnauthorizedError
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas.components import impexp
from apimas.auth import MissingCredentials
from apimas import utils


class AuthenticationProcessor(BaseProcessor):
    """
    Processor for performing authentication based on a selected method.
    """
    name = 'apimas.components.processors.Authentication'

    READ_KEYS = {
        'headers': 'request/meta/headers'
    }

    WRITE_KEYS = (
        'auth/identity',
    )

    authenticator = None

    def __init__(self, collection, action, authenticator, verifier):

        if authenticator:
            assert verifier
            verifier = utils.import_object(verifier)
            _cls = utils.import_object(authenticator)
            self.authenticator = _cls(verifier)

    def process(self, context):
        if self.authenticator is None:
            # If there is not any constructed authentication backend, then
            # we presume that the collection is not protrected, so we skip
            # this processor.
            return
        data = self.read(context)
        try:
            identity = self.authenticator.authenticate(data['headers'])
        except MissingCredentials:
            # this indicates anonymous access, permissions processor will
            # handle authorization for this request
            return
        except UnauthorizedError:
            # Provide the appropriate headers, so that handler can read them
            # later.
            auth_headers = getattr(self.authenticator, 'AUTH_HEADERS',
                                   None)
            if auth_headers:
                response_headers = {'WWW-Authenticate': auth_headers}
                path = 'response/meta/headers'
                self.save(context, path, response_headers)
            raise
        self.write((identity,), context)


class UserRetrievalProcessor(BaseProcessor):
    """
    """

    READ_KEYS = {
        'identity': 'auth/identity'
    }

    WRITE_KEYS = (
        'auth/user',
    )

    def __init__(self, collection, action, user_resolver=None):
        if user_resolver:
            user_resolver = utils.import_object(user_resolver)
            assert callable(user_resolver), (
                '"user_resolver" must be a callable')
        self.user_resolver = user_resolver

    def process(self, context):
        data = self.read(context)
        identity = data.get('identity')

        if not identity:
            user = None
        else:
            if not self.user_resolver:
                raise Exception("No user_resolver set")
            user = self.user_resolver(identity, context)

        self.write((user,), context)


def construct_user_retrieval_args_from_collection(instance, loc):
    user_resolver = docular.doc_spec_get(
        docular.doc_get(instance, ("auth", "user_resolver")))
    value = dict(user_resolver=user_resolver)
    docular.doc_spec_set(instance, value)


USER_RETRIEVAL_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.field.collection.*': construct_user_retrieval_args_from_collection
}, default=impexp.no_constructor)


UserRetrieval = ProcessorConstruction(
    USER_RETRIEVAL_CONSTRUCTORS, UserRetrievalProcessor)


def construct_authenticator_args_from_collection(instance, loc):
    authenticator = docular.doc_spec_get(
        docular.doc_get(instance, ("auth", "authenticator")))
    verifier = docular.doc_spec_get(
        docular.doc_get(instance, ("auth", "verifier")))
    value = dict(authenticator=authenticator, verifier=verifier)
    docular.doc_spec_set(instance, value)


AUTHENTICATE_CONSTRUCTORS = docular.doc_spec_init_constructor_registry({
    '.field.collection.*': construct_authenticator_args_from_collection
}, default=impexp.no_constructor)

Authentication = ProcessorConstruction(
    AUTHENTICATE_CONSTRUCTORS, AuthenticationProcessor)
