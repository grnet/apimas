from requests.auth import AuthBase, HTTPBasicAuth
from apimas.errors import ValidationError


class HTTPTokenAuth(AuthBase):
    """
    Attaches HTTP Token Authentication to the given request object.
    """
    def __init__(self, token):
        self.token = token

    def __eq__(self, other):
        return self.token == getattr(other, 'token', None)

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers['Authorization'] = 'Token ' + self.token
        return r


class ApimasClientAuth(AuthBase):
    """
    Attaches HTTP authentication to the given request object based on the
    auth type.
    """
    AUTHENTICATION_BACKENDS = {
        'basic': HTTPBasicAuth,
        'token': HTTPTokenAuth,
    }

    def __init__(self, auth_type, **credentials):
        self.credentials = credentials
        self.auth_type = auth_type

    def __call__(self, r):
        if self.auth_type is None:
            return r
        if self.auth_type not in self.AUTHENTICATION_BACKENDS:
            raise ValidationError(
                '{!r} auth type is not supported'.format(self.auth_type))
        try:
            auth = self.AUTHENTICATION_BACKENDS[self.auth_type](
                **self.credentials)
        except TypeError:
            raise ValidationError(
                'Given credentials do not match with that of {!r} auth'
                ' type'.format(self.auth_type))
        return auth(r)
