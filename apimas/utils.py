from os.path import expanduser, join, isfile
import yaml
from cerberus import Validator
from apimas.exceptions import ApimasException


HOME_DIR = expanduser("~")
DEFAULT_FILENAME = join(HOME_DIR, '.apimas')


VALIDATION_SCHEMA = {
    'root': {
        'type': 'string'
    },
    'spec': {
        'type': 'dict'
    }
}


def _load_document(path):
    if not isfile(path):
        msg = 'Given path {!r} is not a file'.format(path)
        raise ApimasException(message=msg)

    with open(path) as data_file:
        try:
            return yaml.safe_load(data_file)
        except yaml.YAMLError as e:
            msg = 'File cannot be understood: {!s}.'.format(str(e))
            raise ApimasException(message=msg)


def _validate_document(document):
    if not isinstance(document, dict):
        raise ApimasException('File cannot be understood. It seems not to be'
                              ' a document.')
    validator = Validator(VALIDATION_SCHEMA)
    is_valid = validator.validate(document)
    if not is_valid:
        raise ApimasException(validator.errors)
    return document


def configure(path):
    path = DEFAULT_FILENAME if not path else expanduser(path)
    document = _load_document(path)
    return _validate_document(document)
