from collections import namedtuple
from apimas.errors import UnauthorizedError
from anapp.models import User


def token_verifier(token):
    try:
        return User.objects.get(token=token)
    except User.DoesNotExist:
        return None


def user_resolver(identity, context=None):
    return identity
