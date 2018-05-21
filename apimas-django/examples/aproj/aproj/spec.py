import copy

DEPLOY_CONFIG = {
    ":root_url": "http://127.0.0.1:8000/",
}

ENHANCEDUSERS = {
    '.field.collection.django': {},
    ":authenticator": "apimas.auth.TokenAuthentication",
    ":verifier": "anapp.auth.token_verifier",
    ":user_resolver": "anapp.auth.user_resolver",

    'model': 'anapp.models.EnhancedUser',
    'actions': {
        '.action-template.django.create': {},
        '.action-template.django.list': {},
        '.action-template.django.retrieve': {},
        '.action-template.django.partial_update': {},

        'verify': {
            '.action.django.recipe.partial_update': {},
            'method': 'POST',
            'status_code': 200,
            'url': '/*/verify/',
            ':custom_update_handler': 'anapp.actions.verify_user',
        },

    },
    'fields': {
        'id': {
            '.field.serial': {}},
        'is_verified': {
            '.field.boolean': {},
            '.flag.nowrite': {}},
        'verified_at': {
            '.field.datetime': {},
            '.flag.nullable': {},
            '.flag.nowrite': {}},
        'feature': {
            '.field.string': {}},
        'user': {
            '.field.struct': {},
            'fields': {
                'id': {
                    '.field.serial': {}},
                'username': {
                    '.field.string': {}},
                'role': {
                    '.field.string': {}},
                'token': {
                    '.field.string': {}},
                'password': {
                    '.field.string': {},
                    '.flag.noread': {}},
                'first_name': {
                    '.field.string': {}},
                'last_name': {
                    '.field.string': {}},
                'email': {
                    '.field.email': {}},
            }
        },
        'institutions': {
            '.field.collection.django': {},
            'model': 'anapp.models.EnhancedUser.institutions.through',
            'bound': 'enhanceduser',
            'fields': {
                'id': {
                    '.field.serial': {}},
                'institution': {'.field.ref': {},
                                'source': 'institution_id',
                                'to': 'api/prefix/institutions'},
            },
            'actions': {
                '.action-template.django.retrieve': {},
                '.action-template.django.list': {},
                '.action-template.django.create': {},
                '.action-template.django.delete': {},
            },
        },
        'institutions_flat': {
            '.field.collection.django': {},
            'model': 'anapp.models.EnhancedUser.institutions.through',
            'bound': 'enhanceduser',
            'id_field': 'institution',
            'source': 'institutions',
            'flat': True,
            'fields': {
                'institution': {'.field.ref': {},
                                'source': 'institution_id',
                                'to': 'api/prefix/institutions'},
            },
            'actions': {
                '.action-template.django.retrieve': {},
            },
        },

    }
}

ENHANCEDADMINS = {
    '.field.collection.django': {},
    ":authenticator": "apimas.auth.TokenAuthentication",
    ":verifier": "anapp.auth.token_verifier",
    ":user_resolver": "anapp.auth.user_resolver",

    'model': 'anapp.models.EnhancedUser',
    'subset': 'anapp.models.filter_enhanced_admins',
    'actions': {
        '.action-template.django.create': {},
        '.action-template.django.list': {},
        '.action-template.django.retrieve': {},
        '.action-template.django.partial_update': {},
    },
    'fields': {
        'id': {
            '.field.serial': {}},
        'is_verified': {
            '.field.boolean': {},
            '.flag.nowrite': {}},
        'feature': {
            '.field.string': {}},
        'user': {
            '.field.struct': {},
            'fields': {
                'id': {
                    '.field.serial': {}},
                'username': {
                    '.field.string': {}},
                'email': {
                    '.field.email': {}},
                'role': {
                    '.field.string': {}},
                'token': {
                    '.field.string': {}},
                'password': {
                    '.field.string': {},
                    '.flag.noread': {}},
            },
        },
    },
}

UUIDRESOURCES = {
    '.field.collection.django': {},
    'model': 'anapp.models.UUIDResource',
    'id_field': 'uuid',
    'actions': {
        '.action-template.django.create': {},
        '.action-template.django.list': {},
        '.action-template.django.retrieve': {},
        '.action-template.django.partial_update': {},
    },
    'fields': {
        'uuid': {
            '.field.uuid': {},
            '.flag.nowrite': {}},
        'value': {'.field.string': {}},
        'institutions': {
            '.field.collection.django': {},
            'model': 'anapp.models.UUIDResource.institutions.through',
            'bound': 'uuidresource',
            'id_field': 'institution',  # together with bound
            'fields': {
                'id': {
                    '.field.serial': {}},
                'institution': {'.field.integer': {},
                                'source': 'institution_id'},
            },
            'actions': {
                '.action-template.django.list': {},
                '.action-template.django.create': {},
                '.action-template.django.retrieve': {},
            },
        },
    },
}

POSTS = {
    ".field.collection.django": {},

    ':permissions_namespace': 'anapp.checks',
    ":authenticator": "apimas.auth.TokenAuthentication",
    ":verifier": "anapp.auth.token_verifier",
    ":user_resolver": "anapp.auth.user_resolver",
    ":pagination_default_limit": 5,

    "model": "anapp.models.Post",
    "actions": {
        '.action-template.django.list': {},
        '.action-template.django.create': {},
        '.action-template.django.retrieve': {},
        '.action-template.django.partial_update': {},
        '.action-template.django.delete': {},
        'create': {
            ':post_handler': 'anapp.models.post_create_post',
        },
        'delete': {
            ':post_handler': 'anapp.models.post_delete_post',
        },
    },
    "fields": {
        "id": {".field.serial": {}},
        "url": {".field.identity": {},
                '.flag.nowrite': {},
                "to": "api/prefix/groups",
                "source": "id"},
        "title": {".field.string": {}},
        "body": {".field.string": {}},
        "status": {".field.string": {},
                   "default": "pending"},
    }
}

POSTS2 = copy.deepcopy(POSTS)
POSTS2[':permissions_namespace'] = 'anapp'

NULLTEST = {
    '.field.collection.django': {},
    'model': 'anapp.models.Nulltest',
    "actions": {
        '.action-template.django.list': {},
        '.action-template.django.create': {},
        '.action-template.django.retrieve': {},
    },
    'fields': {
        "id": {".field.serial": {}},
        'fdef': {'.field.integer': {},
                 '.flag.nullable.default': {}},
        'fnodef': {'.field.integer': {},
                   '.flag.nullable': {}},
        'fstr': {'.field.string': {},
                 'default': 'other'},
        'fbool': {'.field.boolean': {},
                  'default': True},
    },
}

INSTITUTIONS = {
    ".field.collection.django": {},
    "model": "anapp.models.Institution",
    "actions": {
        '.action-template.django.list': {},
        '.action-template.django.retrieve': {},
        '.action-template.django.create': {},
        '.action-template.django.partial_update': {},
        '.action-template.django.update': {},
        '.action-template.django.delete': {},
    },
    "fields": {
        "id": {".field.serial": {}},
        "name": {".field.string": {},
                 '.flag.orderable': {}},
        "active": {".field.boolean": {},
                   "default": True,
                   ".flag.orderable": {}},
        "category": {".field.choices": {},
                     ".flag.filterable": {},
                     "allowed": {
                         '=': ["Institution", "Research"]},
                     "displayed": {
                     '=': ["Institution", "Research Center"]},
                     "default": "Research"},
        "category_raw": {
            ".field.choices": {},
            ".flag.nowrite": {},
            "source": "category",
            "allowed": {
                '=': ["Institution", "Research"]},
        },
        "logo": {'.field.file': {},
                 'default': ''},
    }
}

GROUPS = {
    ".field.collection.django": {},
    "model": "anapp.models.Group",
    "actions": {
        '.action-template.django.list': {},
        '.action-template.django.partial_update': {},
        '.action-template.django.create': {},
        '.action-template.django.retrieve': {},
        '.action-template.django.delete': {},
    },
    "fields": {
        "id": {".field.uuid": {},
               '.flag.nowrite': {}},
        "url": {".field.identity": {},
                '.flag.nowrite': {},
                "to": "api/prefix/groups",
                "source": "id"},
        "name": {".field.string": {}},
        "founded": {".field.date": {},
                   'default_fn': 'datetime.datetime.now'},
        "active": {".field.boolean": {},
                   '.flag.filterable': {},
                   'default': True},
        "email": {".field.email": {}},
        "institution_id": {".field.ref": {},
                           '.flag.filterable': {},
                           "to": "api/prefix/institutions"},
        'institution': {
            '.field.struct': {},
            '.flag.nowrite': {},
            'fields': INSTITUTIONS['fields']},
        "members": {
            '.field.collection.django': {},
            ':filter_compat': True,
            'model': 'anapp.models.Member',
            'source': 'members',
            'bound': 'group',
            'actions': {
                '.action-template.django.list': {},
                '.action-template.django.create': {},
                '.action-template.django.retrieve': {},
                '.action-template.django.partial_update': {},
                '.action-template.django.delete': {},
            },
            'fields': {
                'id': {'.field.serial': {}},
                'onoma': {'.field.string': {},
                          '.flag.filterable': {},
                          '.flag.searchable': {},
                          '.flag.orderable': {},
                          'source': 'username'},
                "variants": {
                    ".field.struct": {},
                    '.flag.nullable': {},
                    'default': {'=': None},
                    "source": "name_variants",
                    "fields": {
                        "en": {".field.string": {},
                               '.flag.searchable': {},
                               '.flag.filterable': {},
                               '.flag.orderable': {}},
                        "el": {".field.string": {},
                               '.flag.searchable': {}},
                    },
                },
                'age': {'.field.integer': {},
                        '.flag.filterable': {}},
            }
        }
    }
}

FEATURES = {
    ".field.collection.django": {},
    "model": "anapp.models.Feature",
    "actions": {
        '.action-template.django.retrieve': {},
        '.action-template.django.create': {},
    },
    "fields": {
        "id": {".field.serial": {}},
        "name": {".field.string": {},
                 '.flag.orderable': {}},
        "group_id": {'.field.ref': {},
                     'to': 'api/prefix/groups'},
        'group_name': {
            '.field.string': {},
            '.flag.nowrite': {},
            'source': 'group.name'},
        'institution_name': {
            '.field.string': {},
            '.flag.nowrite': {},
            'source': 'group.institution.name'},
    }
}

NEGOTIATIONS = {
    '.field.collection.django': {},
    'model': 'anapp.models.Negotiation',
    'actions': {
        '.action-template.django.retrieve': {},
        '.action-template.django.create': {},
    },
    'fields': {
        'id': {
            '.field.serial': {}},
        'status': {
            '.field.string': {}},
        'contributions': {
            '.field.collection.django': {},
            '.flag.nowrite': {},
            'model': 'anapp.models.Contribution',
            'bound': 'negotiation',
            'fields': {
                'id': {
                    '.field.serial': {}},
                'text': {
                    '.field.text': {}},
            },
            'actions': {
                '.action-template.django.retrieve': {},
                '.action-template.django.create': {},
            },
        },
    },
}

ACCOUNTS = {
    '.field.collection.django': {},
    'model': 'anapp.models.Account',
    ':decimal_places': 4,
    'actions': {
        '.action-template.django.retrieve': {},
        '.action-template.django.create': {},
    },
    'fields': {
        'id': {
            '.field.serial': {}},
        'balance': {
            '.field.decimal': {},
            ':decimal_places': 2},
        'change': {
            '.field.decimal': {}},
    },
}

PAIRS = {
    '.field.collection.django': {},
    'model': 'anapp.models.Pair',
    'actions': {
        '.action-template.django.retrieve': {},
        '.action-template.django.create': {},
        '.action-template.django.partial_update': {},
    },
    'fields': {
        'id': {
            '.field.serial': {}},
        'alpha': {
            '.field.string': {}},
        'beta': {
            '.field.string': {}},
    },
}

APP_CONFIG = {
    ".apimas_app": {},
    ":permission_rules": "anapp.rules.get_rules",
    'endpoints': {
        "api/prefix": {
            "collections": {
                "enhancedusers": ENHANCEDUSERS,
                "enhancedadmins": ENHANCEDADMINS,
                "uuidresources": UUIDRESOURCES,
                "posts": POSTS,
                "posts2": POSTS2,
                'nulltest': NULLTEST,
                "institutions": INSTITUTIONS,
                "groups": GROUPS,
                "features": FEATURES,
                "negotiations": NEGOTIATIONS,
                "accounts": ACCOUNTS,
                "pairs": PAIRS,
            },
        },
    },
}
