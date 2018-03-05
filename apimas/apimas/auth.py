import base64
from apimas.errors import UnauthorizedError


class MissingCredentials(UnauthorizedError):
    pass


class AuthenticationMethod(object):
    """ Base class which represents an authentication method. """

    def authenticate(self, headers):
        """
        This method must be implemented.

        Typically, this method reads from headers in order to authenticate
        requested parties. If a party is authenticated successfully, a
        dict representing the identity must be returned, `None` otherwise.

        Args:
            headers (dict): A dictionary of request headers.

        Returns:
            A dictionary of identity in case of a successful authentication,
            `None` otherwise.
        """
        raise NotImplementedError('authenticate() must be implemented')

    def extract_from_headers(self, headers):
        raise NotImplementedError('extract_from_headers() must be implemented')


class BasicAuthentication(AuthenticationMethod):
    """
    Basic HTTP authentication method.

    Reads username and password from headers and decides if the given
    credentials match based on a callable provided by user.

    Args:
        verifier: (callable) A function which takes an argument that represents
        the provided authentication credentials and decides if these
        credentials are valid or not.
        This function must return a dict of identity information.
    """

    AUTH_HEADERS = 'Basic realm="api"'

    def __init__(self, verifier):
        self.verifier = verifier

    def authenticate(self, headers):
        credentials = self.extract_from_headers(headers)
        user = self.verifier(credentials)
        if user is None:
            raise UnauthorizedError('Invalid credentials')
        return user

    def extract_from_headers(self, headers):
        authorization = headers.get('HTTP_AUTHORIZATION')
        if authorization is None:
            raise UnauthorizedError('Missing credentials')

        _, match, credentials = authorization.partition('Basic ')
        if not match:
            raise UnauthorizedError('Invalid credentials')

        try:
            username, match, password = base64.b64decode(
                credentials).partition(':')
        except TypeError:
            raise UnauthorizedError('Invalid credentials')
        if not match:
            raise UnauthorizedError('Invalid credentials')

        return (username, password)


class TokenAuthentication(BasicAuthentication):
    """ Token Based Authentication """

    AUTH_HEADERS = 'Bearer'

    def extract_from_headers(self, headers):
        authorization = headers.get('HTTP_AUTHORIZATION')
        if authorization is None:
            raise MissingCredentials('Missing token')
        _, match, token = authorization.partition(
                '{} '.format(self.AUTH_HEADERS))
        if not match:
            _, match, token = authorization.partition('Token ')
            if not match:
                raise UnauthorizedError('Invalid token given')
        return token


class DjoserAuthentication(TokenAuthentication):
    """ Djoser Based Authentication """

    AUTH_HEADERS = 'Token'


class ClientBasicAuthentication(object):
    AUTH_HEADERS = 'Basic'

    def attach_to_headers(self, username, password):
        credentials = '%s:%s' % (username, password)
        encoded_credentials = base64.b64encode(credentials)
        auth = '%s %s' % (self.AUTH_HEADERS, encoded_credentials)
        return {
            'Authorization': auth,
        }


class ClientTokenAuthentication(object):
    AUTH_HEADERS = 'Bearer'

    def attach_to_headers(self, token):
        auth = '%s %s' % (self.AUTH_HEADERS, token)
        return {
            'Authorization': auth
        }
