import re
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

    def __init__(self, date_format=None):
        self.date_format = date_format or self.DEFAULT_FORMAT

    def __call__(self, value):
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time())
            return value.strftime(self.date_format)
        elif isinstance(value, datetime):
            return value.strftime(self.date_format)
        elif isinstance(value, str):
            datetime.strptime(value, self.date_format)
        return value


class DateNormalizer(DateTimeNormalizer):
    DEFAULT_FORMAT = '%Y-%m-%d'


class ApimasValidator(Validator):
    """
    Extends cerberus `Validator` by adding a new type, i.e. `file`, `email`.
    """
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
