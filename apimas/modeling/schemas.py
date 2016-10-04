from cerberus import Validator, schema_registry


FIELD_SCHEMA = {
    'fields': {
        'type': 'list',
        'required': True,
        'schema': {'type': 'string'}
    },
    'read_only_fields': {
        'type': 'list',
        'schema': {'type': 'string'}
    },
    'write_only_fields': {
        'type': 'list',
        'schema': {'type': 'string'}
    },
    'required_fields': {
        'type': 'list',
        'schema': {'type': 'string'}
    },
    'nullable_fields': {
        'type': 'list',
        'schema': {'type': 'string'}
    },
    'blankable_fields': {
        'type': 'list',
        'schema': {'type': 'string'}
    },
    'custom_mixins': {
        'type': 'list',
        'schema': {'type': 'string'}
    },
    'properties': {
        'type': 'dict',
        'allow_unknown': True,
        'valueschema': {
            'type': 'dict',
            'schema': {
                'allow_null': {
                    'type': 'boolean'
                },
                'allow_blank': {
                    'type': 'boolean'
                },
                'allow_empty': {
                    'type': 'boolean'
                },
                'required': {
                    'type': 'boolean'
                },
                'read_only': {
                    'type': 'boolean'
                },
                'write_only': {
                    'type': 'boolean'
                },
                'label': {
                    'type': 'string'
                },
                'help_text': {
                    'type': 'string'
                },
                'validators': {
                    'type': 'list'
                },
                'error_messages': {
                    'type': 'dict',
                    'allow_unknown': True,
                    'valueschema': {
                        'type': 'list',
                        'schema': {'type': 'string'}
                    }
                },
                'source': {
                    'type': 'string'
                },
            }
        }
    },
    'nested_objects': {
        'type': 'dict',
        'allow_unknown': True,
        'valueschema': {
            'type': 'dict',
            'schema': 'nested'
        }
    }
}


NESTED_OBJECT_SCHEMA = {
    'model_field': {
        'required': True,
        'type': 'string',
    },
    'model': {
        'type': 'string'
    },
    'field_schema': {
        'required': True,
        'type': 'dict',
        'schema': 'nested_fields',
    }
}


schema_registry.add('nested_fields', FIELD_SCHEMA)
schema_registry.add('nested', NESTED_OBJECT_SCHEMA)


RESOURCE_SCHEMA = {
    'hyperlinked': {
        'type': 'boolean'
    },
    'authentication_classes': {
        'type': 'list',
        'schema': {'type': 'string'},
    },
    'permission_classes': {
        'type': 'list',
        'schema': {'type': 'string'},
    },
    'custom_mixins': {
        'type': 'list',
        'schema': {'type': 'string'},
    },
    'hook_class': {
        'type': 'string',
    },
    'model': {
        'type': 'string',
        'required': True,
    },
    'filter_fields': {
        'type': 'list',
        'schema': {'type': 'string'},
    },
    'search_fields': {
        'type': 'list',
        'schema': {'type': 'string'},
    },
    'ordering_fields': {
        'type': 'list',
        'schema': {'type': 'string'},
    },
    'allowable_operations': {
        'type': 'list',
        'allowed': ['list', 'retrieve', 'create', 'update', 'delete']
    },
    'field_schema': {
        'type': 'dict',
        'schema': FIELD_SCHEMA,
    }
}


API_SCHEMA = {
    'resources': {
        'required': True,
        'type': 'dict',
        'allow_unknown': True,
        'valueschema': {
            'type': 'dict',
            'schema': RESOURCE_SCHEMA
        }
    },
    'global': {
        'type': 'dict',
        'schema': {
            'hyperlinked': {
                'type': 'boolean'
            },
            'authentication_classes': {
                'type': 'list',
                'schema': {'type': 'string'},
            },
            'permission_classes': {
                'type': 'list',
                'schema': {'type': 'string'},
            }
        }
    }
}


RESOURCE_SCHEMA_VALIDATOR = Validator(RESOURCE_SCHEMA)
API_SCHEMA_VALIDATOR = Validator(API_SCHEMA)
