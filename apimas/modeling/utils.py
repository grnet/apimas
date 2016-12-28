from os.path import expanduser, join, isfile
import yaml
from cerberus import Validator
from apimas.modeling.core.exceptions import ApimasException


HOME_DIR = expanduser("~")


VALIDATION_SCHEMA = {
    'root': {
        'type': 'string'
    },
    'spec': {
        'type': 'dict'
    }
}


def load_config(path=None, config_file=".apimas"):
    filepath = join(path or HOME_DIR, config_file)
    if not isfile(filepath):
        raise ApimasException('.apimas file not found')

    with open(filepath) as data_file:
        data = yaml.load(data_file)
    validator = Validator(VALIDATION_SCHEMA)
    is_valid = validator.validate(data)
    if not is_valid:
        raise ApimasException(validator.errors)
    return data
