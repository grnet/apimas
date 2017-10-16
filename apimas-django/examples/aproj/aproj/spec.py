CONFIG = {
    ".apimas_app": {},
    ".meta": {"get_rules": "anapp.rules.get_rules"},
    "api/prefix": {
       ".endpoint": {},
        "groups": {
            ".field.collection.django": {},
            "model": "anapp.models.Group",
            "actions": {
                '.action-template.django.list': {},
                '.action-template.django.create': {},
                '.action-template.django.retrieve': {},
            },
            "fields": {
                "id": {".field.serial": {}},
                "url": {".field.identity": {"to": "api/prefix/groups"},
                        "source": "id"},
                "name": {".field.string": {}},
                "users": {
                    '.field.collection.django': {},
                    '.field.collection.*': {},
                    'model': 'anapp.models.User',
                    'source': 'user_set',
                    'bound': 'group',
                    'actions': {
                        '.action-template.django.list': {},
                        '.action-template.django.create': {},
                        '.action-template.django.retrieve': {},
                    },
                    'fields': {
                        'id': {'.field.serial': {}},
                        'username': {'.field.string': {}},
                #         'emails': {
                #             '.field.collection.django': {},
                #             'model': 'anapp.models.Email',
                #             'source': 'email_set',
                #             'bound': 'user',
                #             'actions': {
                #                 '.action-template.django.list': {},
                #                 '.action-template.django.create': {},
                #                 '.action-template.django.retrieve': {},
                #             },
                #             'fields': {
                #                 'id': {'.field.serial': {}},
                #                 'email': {'.field.string': {}},
                #             }
                #         }
                    }
                }
            }
        },  # "col1" ends here
    },
    # "api/prefix2": {
    #     ".endpoint": {},
    #     ".meta": {"get_rules": "anapp.rules.get_rules2"},
    #     "col1": {
    #        ".collection.django": {},
    #         "model": "anapp.models.Collection1",
    #         "actions": {
    #             '.action-template.django.list': {},
    #             '.action-template.django.create': {},
    #             '.action-template.django.retrieve': {},
    #         },
    #         "fields": {
    #             "id": {".field.serial": {}},
    #             "name": {".field.string": {}},
    #         },
    #     },  # "col1" ends here
    # }
}
