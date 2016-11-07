import json
import click
import yaml


class Json(click.ParamType):
    name = 'json'

    def convert(self, value, param, ctx):
        try:
            return json.loads(value)
        except ValueError as e:
            self.fail(e)


class Credentials(click.File):
    name = 'credentials'

    def __init__(self, file_type='yaml', schema=None, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        self.schema = schema
        self.file_type = file_type

    def load_yaml(self, f):
        try:
            return yaml.load(f)
        except yaml.YAMLError as e:
            self.fail(e)

    def load_json(self, f):
        try:
            return json.load(f)
        except ValueError as e:
            self.fail(e)

    def convert(self, value, param, ctx):
        """
        Extracts authentication model and schema from the configuration file.
        """
        file_loaders = {
            'yaml': self.load_yaml,
            'json': self.load_json,
        }
        f = super(self.__class__, self).convert(value, param, ctx)
        if self.file_type not in file_loaders:
            self.fail('%s format is not supported' % (self.file_type))
        credentials = file_loaders[self.file_type](f)
        return self.parse_credentials(credentials)

    def parse_credentials(self, credentials):
        """
        Checks that credentials are valid based on initial authentication
        schema and extracts both authentication mode and schema.

        If a default authentication mode is provided, then this method extracts
        its authentication schema. Otherwise, it fetches the first
        authentication mode defined in the file along with its schema.
        """
        default = credentials.get('default', None)
        if not default:
            auth_type, auth_schema = credentials.items()[0]
        else:
            auth_type, auth_schema = default, credentials.get(default, None)
        if auth_type not in self.schema:
            self.fail('%s is not part of supported authentication schemas' % (
                default))
        if not auth_schema:
            self.fail('Cannot find %s as authentication schema' % (auth_type))

        if isinstance(auth_type, dict) or set(auth_schema).difference(
                self.schema[auth_type]):
            self.fail('Schema of %s does not conform to the specification' % (
                auth_type))
        return auth_type, auth_schema
