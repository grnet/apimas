from collections import namedtuple
from apimas.errors import UnauthorizedError


User = namedtuple('User', ('apimas_roles',))


def token_verifier(token):
    if not token.startswith('admin-'):
        raise UnauthorizedError('Unauthorized token: %s' % token)

    return "verified-%s" % token


def user_resolver(identity, context=None):
    """
    Given a user identity resolve user attributes
    """
    _, username, roles, token = identity.split('-')
    return User(apimas_roles=roles.split(","))
