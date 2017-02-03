import random
import re
from collections import Iterable
from datetime import datetime, date
from cerberus import Validator
from requests.compat import urljoin


class RefNormalizer(object):
    """
    Normalizer of a value that implies an id of a referenced collection.

    It constructs the URL location where the referenced resource specified
    by the given id is located.
    """
    def __init__(self, ref_endpoint):
        self.ref_endpoint = ref_endpoint

    def __call__(self, value):
        if value is None:
            return value
        return urljoin(self.ref_endpoint, value).rstrip('/') + '/'


class DateTimeNormalizer(object):
    """
    Normalize a datetime object to a string value based on the given format.

    If value is string, then it is checked if it follows the given format.
    """
    DEFAULT_FORMAT = '%Y-%m-%dT%H:%M:%S'

    def __init__(self, string_formats=None, date_format=None):
        self.string_formats = string_formats or [self.DEFAULT_FORMAT]
        self.date_format = date_format or random.choice(self.string_formats)

    def __call__(self, value):
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time())
            return value.strftime(self.date_format)
        elif isinstance(value, datetime):
            return value.strftime(self.date_format)
        elif isinstance(value, str):
            self._to_date(value)
        return value

    def _to_date(self, value):
        for string_format in self.string_formats:
            try:
                return datetime.strptime(value, string_format)
            except ValueError:
                pass
        raise ValueError('Given date formats are invalid')


class DateNormalizer(DateTimeNormalizer):
    DEFAULT_FORMAT = '%Y-%m-%d'


class ApimasValidator(Validator):
    """
    Extends cerberus `Validator` by adding a new type, i.e. `file`, `email`.
    """
    def _validate_type_choices(self, value):
        return not (isinstance(value, Iterable) and not isinstance(value, str))

    def _validate_type_file(self, value):
        return isinstance(value, file)

    def _validate_type_email(self, value):
        if not isinstance(value, (str, unicode)):
            return False
        # http://haacked.com/archive/2007/08/21/i-knew-how-to-validate-an-email-address-until-i.aspx/
        regex = re.compile(r"^(?!\.)(""([^""\r\\]|\\[""\r\\])*""|"
                           r"([-a-z0-9!#$%&'*+/=?^_`{|}~]|(?<!\.)\.)*)(?<!\.)"
                           r"@[a-z0-9][\w\.-]*[a-z0-9]\.[a-z][a-z\.]*[a-z]$")
        return bool(regex.match(value))