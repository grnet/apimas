import pytest

from django.test.client import Client as DjangoClient
from django.conf import settings


class Client(DjangoClient):

    def __init__(self, *args, **kwargs):
        self.auth_token = None
        self.prefix = kwargs.pop('prefix', '')
        if not self.prefix.endswith('/'):
            self.prefix += '/'
        auth_token = kwargs.pop('auth_token', None)
        super(Client, self).__init__(*args, **kwargs)
        if auth_token:
            self.auth(auth_token)

    def copy(self, **kwargs):
        defaults = dict(self.defaults)
        defaults.update(kwargs.pop('defaults', {}))
        prefix = kwargs.pop('prefix', self.prefix)
        auth_token = kwargs.pop('auth_token', self.auth_token)
        return Client(defaults=defaults, prefix=prefix, auth_token=auth_token,
                      **kwargs)

    def auth(self, token):
        self.auth_token = token
        self.defaults['HTTP_AUTHORIZATION'] = 'Token {}'.format(token)

    def generic(self, *args, **kwargs):
        method = args[0]
        path = args[1]
        args = args[2:]

        if not path.startswith('http'):
            path = '{}{}'.format(self.prefix, path).replace('//', '/')

        if settings.APPEND_SLASH and not path.endswith('/'):
            path = '{}/'.format(path)

        return super(Client, self).generic(method, path, *args, **kwargs)


@pytest.fixture('function')
def client(request):
    return Client()


pytestmark = pytest.mark.django_db
