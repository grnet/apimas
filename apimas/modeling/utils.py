from os.path import expanduser, join, isfile
import yaml
from cerberus import Validator
from apimas.modeling.core.exceptions import ApimasException


HOME_DIR = expanduser("~")
CONFIG_FILE = '.apimas'


VALIDATION_SCHEMA = {
    'root': {
        'type': 'string'
    },
    'spec': {
        'type': 'dict'
    }
}


def load_config(path=None):
    filepath = join(path or HOME_DIR, CONFIG_FILE)
    if not isfile(filepath):
        raise ApimasException('.apimas file not found')

    with open(filepath) as data_file:
        data = yaml.load(data_file)
    validator = Validator(VALIDATION_SCHEMA)
    is_valid = validator.validate(data)
    if not is_valid:
        raise ApimasException(validator.errors)
    return data
