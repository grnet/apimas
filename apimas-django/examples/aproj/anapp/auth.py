from collections import namedtuple


User = namedtuple('User', ('apimas_roles',))


def token_verifier(token):
    return "verified-%s" % token


def user_resolver(identity, context=None):
    """
    Given a user identity resolve user attributes
    """
    _, username, roles, token = identity.split('-')
    return User(apimas_roles=roles.split(","))
