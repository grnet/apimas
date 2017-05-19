import json
from datetime import datetime
import re
import click
from click.types import StringParamType
import yaml


class Email(StringParamType):
    name = 'email'

    regex = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

    def convert(self, value, param, ctx):
        value = super(Email, self).convert(value, param, ctx)
        matched = self.regex.match(value)
        if not matched:
            self.fail('Email is invalid')
        return value


class Json(click.ParamType):
    name = 'json'

    def convert(self, value, param, ctx):
        try:
            return json.loads(value)
        except ValueError as e:
            self.fail(e.message)


class DateTime(click.ParamType):
    name = 'datetime'

    DEFAULT_FORMAT = '%Y-%m-%dT%H:%M:%S'

    def __init__(self, date_formats=None, **kwargs):
        self.date_formats = date_formats or [self.DEFAULT_FORMAT]

    def convert(self, value, param, ctx):
        for date_format in self.date_formats:
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                pass
        self.fail('The given date formats are invalid')


class Date(DateTime):
    name = 'date'

    DEFAULT_FORMAT = '%Y-%m-%d'

    def __init__(self, date_formats=None, **kwargs):
        self.date_formats = date_formats or [self.DEFAULT_FORMAT]

    def convert(self, value, param, ctx):
        return super(self.__class__, self).convert(value, param, ctx).date()


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
            self.fail(e.message)

    def load_json(self, f):
        try:
            return json.load(f)
        except ValueError as e:
            self.fail(e.message)

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
            self.fail('{!r} format is not supported'.format(self.file_type))
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
            self.fail(
                '{!r} is not part of supported authentication schemas'.format(
                    auth_type))
        if not auth_schema:
            self.fail(
                'Cannot authentication schema of find {!r}'.format(auth_type))

        if isinstance(auth_type, dict) or set(auth_schema).difference(
                self.schema[auth_type]):
            self.fail(
                'Schema of {!r} does not conform to the specification'.format(
                    auth_type))
        return auth_type, auth_schema
