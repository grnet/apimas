from apimas.modeling.adapters.drf.testing import (
    set_apimas_context, ApimasTestCase)
from apimas.modeling.adapters.drf.tests.utils import ACTIONS


def get_value(instance):
    return 'foo'


SPEC = {
    '.endpoint': {
        'permissions': [('*',) * 6],
    },
    'api': {
        'mymodel': {
            '.collection': {},
            '.drf_collection': {
                'model': 'apimas.modeling.adapters.drf.tests.models.MyModel',
            },
            '*': {
                'data': {
                    '.required': {},
                    '.drf_field': {'onmodel': False},
                    '.struct': {
                        'node': {
                            '.required': {},
                            '.drf_field': {'onmodel': False},
                            '.struct': {
                                'id': {
                                    '.serial': {},
                                    '.drf_field': {},
                                    '.readonly': {},
                                },
                                'string': {
                                    '.required': {},
                                    '.drf_field': {},
                                    '.string': {},
                                },
                                'text': {
                                    '.drf_field': {},
                                    '.string': {},
                                    '.required': {},
                                },
                                'number': {
                                    '.drf_field': {},
                                    '.integer': {},
                                    '.required': {},
                                },
                                'big_number': {
                                    '.drf_field': {},
                                    '.biginteger': {},
                                    '.required': {},
                                },
                                'float_number': {
                                    '.drf_field': {},
                                    '.float': {},
                                    '.required': {},
                                },
                                'boolean': {
                                    '.drf_field': {},
                                    '.boolean': {},
                                    '.required': {},
                                },
                                'date_field': {
                                    '.drf_field': {},
                                    '.date': {},
                                    '.required': {},
                                },
                                'datetime_field': {
                                    '.drf_field': {},
                                    '.datetime': {},
                                    '.required': {},
                                },
                                'url': {
                                    '.identity': {},
                                    '.drf_field': {},
                                },
                                'extra_field': {
                                    '.string': {},
                                    '.drf_field': {
                                        'onmodel': False,
                                        'instance_source': __name__ + '.get_value'}
                                },
                            }
                        }
                     }
                },
                'extra': {
                    '.writeonly': {},
                    '.drf_field': {'onmodel': False},
                    '.struct': {
                        'foo': {
                            '.drf_field': {'onmodel': False},
                            '.string': {}
                        },
                        'bar': {
                            '.drf_field': {'onmodel': False},
                            '.integer': {},
                        },
                    }
                },
            },
            'actions': ACTIONS
        },
    }
}


@set_apimas_context(__name__, SPEC)
class TestNonModelFields(ApimasTestCase):
    pass
