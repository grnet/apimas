import pytest
import json

from django.test.client import Client as DjangoClient, MULTIPART_CONTENT
from django.conf import settings


JSON = 'application/json'


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

    def _encode_data(self, data, content_type):
        if content_type == JSON:
            # apimas override for common json requests
            return json.dumps(data)
        else:
            # multipart handling
            return super(Client, self)._encode_data(data, content_type)

    def post(self, path, data=None, content_type=JSON, **kwargs):
        # DjangoClient calls _encode_data for post requests
        return super(Client, self).post(
            path, data, content_type=content_type, **kwargs)

    def put(self, path, data='', content_type=JSON, **kwargs):
        data = self._encode_data(data, content_type)
        return super(Client, self).put(
            path, data, content_type=content_type, **kwargs)

    def patch(self, path, data='', content_type=JSON, **kwargs):
        data = self._encode_data(data, content_type)
        return super(Client, self).patch(
            path, data, content_type=content_type, **kwargs)

    def options(self, path, data='', content_type=JSON, **kwargs):
        if content_type == JSON and data:
            data = json.dumps(data)
        return super(Client, self).options(
            path, data, content_type=content_type, **kwargs)

    def delete(self, path, data='', content_type=JSON, **kwargs):
        if content_type == JSON and data:
            data = json.dumps(data)
        return super(Client, self).delete(
            path, data, content_type=content_type, **kwargs)

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
