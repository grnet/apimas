from datetime import date, datetime
import re
import time
from cerberus import Validator


class CerberusValidator(Validator):
    """
    Extends cerberus `Validator` by adding a new types, e.g. `file`, `email`,
    etc.
    """
    def _validate_type_choices(self, value):
        return isinstance(value, (bool, int, long, float, str, unicode))

    def _validate_type_file(self, value):
        return isinstance(value, file)

    def _validate_type_date(self, value):
        return isinstance(value, date)

    def _validate_type_datetime(self, value):
        return isinstance(value, datetime)

    def _validate_type_email(self, value):
        if not isinstance(value, (str, unicode)):
            return False

        regex = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\."
                           r"[a-zA-Z0-9-.]+$)")
        return bool(regex.match(value))

    def _validate_date_format(self, date_format, field, value):
        if isinstance(value, (str, unicode)):
            try:
                time.strptime(value, date_format)
            except ValueError:
                msg = '{!r} does not match with {!r} format'
                self._error(field, msg.format(value, date_format))