import docular

spec_list = [
    {'.boolean': {}},
    {'.string': {}},
    {'.integer': {}},
    {'.float': {}},

    {'.processor.*': {},
     'module_path': {'.string': {}},
     ':*': {}},

    {'.flag.*': {}},
    {'.flag.readonly': {}},
    {'.flag.writeonly': {}},
    {'.flag.nullable.*': {}},

    {'.flag.nullable.default': {},
     'default': {'=': None}},

    {'.flag.filterable': {}},
    {'.flag.orderable': {}},
    {'.flag.searchable': {}},

    {
        '.field.*': {},
        'source': {'.string': {}},
        '.flag.*': {},
        'default': {},
        'default_fn': {'.string': {}},
        '*': {},
    },

    {'.field.string': {},
     'default': {'.string': {}}},

    {'.field.serial': {},
     '.flag.readonly': {}},
    {'.field.integer': {}},
    {'.field.float': {}},

    {'.field.ref': {},
     ':root_url': {'.string': {}},
     'to': {'.string': {}}},

    {'.field.identity': {},
     ':root_url': {'.string': {}},
     'to': {'.string': {}}},

    {'.field.uuid': {}},
    {'.field.text': {}},
    {'.field.email': {}},

    {'.field.boolean': {},
     'default': {'.boolean': {}}},

    {'.field.datetime': {}},
    {'.field.date': {}},
    {'.field.file': {}},

    {'.field.choices': {},
     'allowed': {},
     'displayed': {}},

    {
        '.field.struct': {},
        'fields': {'*': {'.field.*': {}}},
    },

    {
        '.field.collection.*': {},
        'id_field': {'.string': {}},
        'flat': {'.boolean': {}},
        ':*': {},
        'actions': {
            '.action-template.*': {},
            '*': {
                ".action.*": {},
                ':*': {},
                'on_collection': {'.boolean': {}},
                'processors': {'*': {'.processor': {}}},
            }
        },
        'fields': {'*': {".field.*": {}}},
        '*': {},
    },

    {
        '.apimas_app': {},
        ':*': {},
        'endpoints': {
            '*': {
                ".endpoint": {},
                ':*': {},
                'collections': {
                    "*": {'.field.collection.*': {}},
                }
            }
        },
    },

    {
        '.processor.permissions.*': {},
        'module_path': 'apimas.components.permissions.Permissions',
        ':permission_rules': {'.string': {}},
        ':permissions_namespace': {'.string': {}},
        ':permissions_mode': {'.string': {}},
        ':permissions_strict': {'.boolean': {}},
        ':permissions_read': {'.string': {}},
        ':permissions_write': {'.string': {}},
    },

    {
        '.processor.permissions.write': {},
        ':permissions_mode': 'write',
    },

    {
        '.processor.permissions.read.*': {},
        ':permissions_mode': 'read',
    },

    {
        '.processor.permissions.read.nonstrict': {},
        ':permissions_strict': False,
    },

    {
        '.processor.authentication': {},
        'module_path': 'apimas.components.auth.Authentication',
        ':authenticator': {'.string': {}},
        ':verifier': {'.string': {}},
    },

    {
        '.processor.user_retrieval': {},
        'module_path': 'apimas.components.auth.UserRetrieval',
        ':user_resolver': {'.string': {}},
    },

    {
        '.processor.import_write_data': {},
        'module_path': 'apimas.components.impexp.ImportWriteData',
    },

    {
        '.processor.import_params': {},
        'module_path': 'apimas.components.impexp.ImportParams',
        ':filter_compat': {'.boolean': {}},
    },

    {
        '.processor.export_data': {},
        'module_path': 'apimas.components.impexp.ExportData',
    },

]

PREDICATES = {}

for spec in spec_list:
    docular.doc_compile_spec(spec, PREDICATES)
