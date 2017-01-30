API_SPEC = {
    'api': {
        '.endpoint': {
            'permissions': [('*',) * 6],
        },
        'manufacturers': {
            '.collection': {},
            '.drf_collection': {
                'model': 'eshop.models.Manufacturer',
            },
            '*': {
                'name': {
                    '.required': {},
                    '.drf_field': {},
                    '.string': {'max_length': 10},
                },
            },
            'actions': {
                '.create': {},
                '.list': {},
                '.retrieve': {},
            }
        },
        'products': {
            '.collection': {
            },
            '.drf_collection': {
                'model': 'eshop.models.Product',
            },
            '*': {
                'key': {
                    '.drf_field': {},
                    '.string': {'max_length': 10}
                },
                'name': {
                    '.drf_field': {},
                    '.string': {},
                },
                'description': {
                    '.drf_field': {},
                    '.string': {},
                },
                'stock': {
                    '.drf_field': {},
                    '.integer': {},
                },
                'price': {
                    '.drf_field': {},
                    '.float': {},
                },
                'manufacturer': {
                    '.ref': {'to': 'manufacturers'},
                    '.drf_field': {},
                },
            },
            'actions': {
                '.list': {},
                '.retrieve': {},
            }
        },
        'cities': {
            '.collection': {},
            '.drf_collection': {'model': 'eshop.models.City'},
            '.cli_commands': {},
            '*': {
                'city': {
                    '.drf_field': {'source': 'name'},
                    '.string': {},
                },
                'country': {
                    '.drf_field': {},
                    '.struct': {
                        'name': {
                            '.drf_field': {},
                            '.string': {},
                        },
                    },
                },
            },
            'actions': {
                '.list': {},
                '.retrieve': {},
            }
        },
        'users': {
            '.drf_collection': {
                'model': 'eshop.models.UserProfile',
            },
            '.collection': {},
            '*': {
                'id': {
                    '.drf_field': {},
                    '.serial': {},
                },
                'username': {
                    '.drf_field': {},
                    '.string': {},
                    '.required': {},
                },
                'first_name': {
                    '.drf_field': {},
                    '.string': {},
                    'required': {},
                },
                'last_name': {
                    '.drf_field': {},
                    '.string': {},
                    '.required': {},
                },
                'password': {
                    '.drf_field': {},
                    '.string': {},
                    '.required': {},
                    '.writeonly': {},
                },
                'email': {
                    '.drf_field': {},
                    '.email': {},
                    '.required': {},
                },
            },
            'actions': {
                '.create': {},
                '.update': {},
                '.retrieve': {},
            }
        },
        'carts': {
            '.collection': {},
            '.drf_collection': {
                'authentication_classes': ['rest_framework.authentication.BasicAuthentication'],
                'permission_classes': ['rest_framework.permissions.IsAuthenticated'],
                'model': 'eshop.models.Cart',
            },
            '*': {
                'customer': {
                    '.required': {},
                    '.drf_field': {},
                    '.ref': {'to': 'users'},
                },
                'ordered': {
                    '.drf_field': {},
                    '.boolean': {},
                    '.readonly': {},
                },
                'products': {
                    '.required': {},
                    '.drf_field': {},
                    '.ref': {'to': 'products', 'many': True},
                    '.writeonly': {},
                },
                'products-view': {
                    '.drf_field': {'source': 'products'},
                    '.readonly': {},
                    '.structarray': {
                        'key': {
                            '.drf_field': {},
                            '.string': {},
                        },
                        'name': {
                            '.drf_field': {},
                            '.string': {},
                        },
                        'price': {
                            '.drf_field': {},
                            '.float': {},
                        },
                    }
                },

            },
            'actions': {
                '.list': {},
                '.retrieve': {},
                '.create': {},
                '.update': {},
                '.delete': {},
            },
        },
        'orders': {
            '.collection': {},
            '.drf_collection': {
                'model': 'eshop.models.Order',
                'authentication_classes': ['rest_framework.authentication.BasicAuthentication'],
                'permission_classes': ['rest_framework.permissions.IsAuthenticated'],
                'hook_class': 'eshop.hooks.CreateOrder'
            },
            '*': {
                'id': {
                    '.cli_option': {},
                    '.drf_field': {},
                    '.field': {},
                    '.serial': {},
                    '.readonly': {},
                },
                'city': {
                    '.field': {},
                    '.required': {},
                    '.drf_field': {},
                    '.ref': {
                        'to': 'cities',
                    },
                },
                'date': {
                    '.datetime': {'format': '%Y-%m-%d %H:%M'},
                    '.required': {},
                    '.drf_field': {},
                },
                'cart': {
                    '.drf_field': {},
                    '.ref': {'to': 'carts'},
                    '.required': {},
                }
            },
            'actions': {
                '.list': {},
                '.create': {},
                '.update': {},
                '.delete': {},
                '.retrieve': {},
            }
        },
    }
}
