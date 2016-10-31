import pdb
from apimas.modeling.mixins import HookMixin


class Hooks(HookMixin):
    def preprocess_create(self):
        pdb.set_trace()

    def finalize_create(self):
        pdb.set_trace()


user = {
    'model': 'eshop.models.UserProfile',
    'authentication_classes': ['rest_framework.authentication.BasicAuthentication'],
    'permission_classes': ['rest_framework.permissions.IsAuthenticated'],
    'allowable_operations': ['retrieve'],
    'field_schema': {
        'fields': ['id', 'url', 'first_name', 'last_name'],
    }
}


country = {
    'model': 'eshop.models.Country',
    'allowable_operations': ['list', 'retrieve'],
    'field_schema': {
        'fields': ['id', 'url', 'name'],
    }
}


city = {
    'model': 'eshop.models.City',
    'allowable_operations': ['list', 'retrieve'],
    'field_schema': {
        'fields': ['id', 'url', 'name', 'country'],
    }
}


manufacturer = {
    'model': 'eshop.models.Manufacturer',
    'authentication_classes': ['rest_framework.authentication.BasicAuthentication'],
    'permission_classes': ['rest_framework.permissions.IsAuthenticated'],
    'allowable_operations': ['list', 'retrieve'],
    'field_schema': {
        'fields': ['id', 'url', 'name'],
    }
}


product = {
    'model': 'eshop.models.Product',
    'allowable_operations': ['list', 'retrieve', 'create'],
    'hook_class': 'eshop.api_schema.Hooks',
    'field_schema': {
        'fields': ['id', 'url', 'name', 'key', 'description', 'stock',
                   'price'],
    }
}


cart = {
   'model': 'eshop.models.Cart',
   'authentication_classes': ['rest_framework.authentication.BasicAuthentication'],
   'permission_classes': ['rest_framework.permissions.IsAuthenticated'],
   'field_schema': {
        'fields': ['id', 'url', 'products', 'customer'],
        'nested_objects': {
            'products': {
                'model_field': 'products',
                'field_schema': {
                    'fields': ['id', 'url', 'name', 'key',
                               'description', 'stock',
                               'manufacturer', 'price'],
                }
            }
        }
    }
}


order = {
   'model': 'eshop.models.Order',
   'authentication_classes': ['rest_framework.authentication.BasicAuthentication'],
   'permission_classes': ['rest_framework.permissions.IsAuthenticated'],
   'field_schema': {
        'fields': ['id', 'url', 'city', 'street_addres', 'cart'],
        'nested_objects': {
            'cart': {
                'model_field': 'cart',
                'field_schema': cart['field_schema'],
            }
        }
    }
}


API_SCHEMA = {
   'resources': {
       'users': user,
       'manufacturers': manufacturer,
       'cities': city,
       'countries': country,
       'products': product,
       'carts': cart,
       'orders': order,
   }
}


API_SPEC = {
    '.endpoint': {},
    'api': {
        'productz': {
            '.collection': {'model': 'eshop.models.Product'},
            '*': {
                '.resource': {},
                '*': {
                    'stock': {
                        '.integer': {},
                        '.readonly': {}
                    },
                    'name': {
                        '.string': {},
                        '.indexable': {},
                        '.blankable': {}
                    }
                }
            }
        },
        'carts': {
            '.collection': {'model': 'eshop.models.Cart'},
            '*': {
                '.resource': {},
                '*': {
                    'products': {
                        '.structarray': {'source': 'products'},
                        '*': {
                            'stock': {
                                '.integer': {},
                                '.required': {},
                            },
                            'name': {
                                '.string': {},
                                '.blankable': {}
                            }
                        }
                    }
                }
            }
        },
        'orders': {
            '.collection': {
                'model': 'eshop.models.Order',
            },
            '*': {
                '.resource': {},
                '*': {
                    'id': {
                        '.serial': {}
                    },
                    'cart': {
                        '.struct': {'source': 'cart'},
                        '*': {
                            'products': {
                                '.structarray': {'source': 'products'},
                                '*': {
                                    'name': {
                                        '.string': {}
                                    }
                                }
                            }
                        }
                    }
                },
            },
            'actions': {
                '.list': {}
            }
        }
    }
}
