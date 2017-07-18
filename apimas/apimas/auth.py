import base64
from apimas.errors import AccessDeniedError


class AuthenticationMethod(object):
    """
    Base class which represents an authentication method.
    """

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
        verifier: (callable) A function which takes two arguments i.e.
        (username and password) and decides if these credentials match or not.
        This function must return a dict of identity information.
    """

    AUTH_HEADERS = 'Basic realm="api"'

    def __init__(self, verifier):
        self.verifier = verifier

    def authenticate(self, headers):
        username, password = self.extract_from_headers(headers)
        user = self.verifier(username, password)
        if user is None:
            raise AccessDeniedError('Given credentials does not match')
        return user

    def extract_from_headers(self, headers):
        authorization = headers.get('HTTP_AUTHORIZATION')
        if authorization is None:
            raise AccessDeniedError('Missing credentials')
        _, match, credentials = authorization.partition('Basic ')
        if not match:
            raise AccessDeniedError('Invalid credentials')
        try:
            username, match, password = base64.b64decode(
                credentials).partition(':')
        except TypeError:
            raise AccessDeniedError('Invalid credentials')
        if not match:
            raise AccessDeniedError('Invalid credentials')
        return username, password


class TokenAuthentication(AuthenticationMethod):
    """ Token Based Authentication """

    AUTH_HEADERS = 'Bearer'

    def __init__(self, verifier):
        self.verifier = verifier

    def authenticate(self, headers):
        token = self.extract_from_headers(headers)
        user = self.verifier(token)
        if user is None:
            raise AccessDeniedError('Given credentials does not match')
        return user

    def extract_from_headers(self, headers):
        authorization = headers.get('HTTP_AUTHORIZATION')
        if authorization is None:
            raise AccessDeniedError('Missing token')
        _, match, token = authorization.partition('Bearer ')
        if not match:
            raise AccessDeniedError('Invalid token given')
        return token
