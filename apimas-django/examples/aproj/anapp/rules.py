# COLUMNS = ('collection', 'action', 'role', 'field', 'state', 'comment')

RULES = [


    ('api/prefix/institutions', 'list', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'create', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'create_response', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'partial_update', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'partial_update_response', '*', '*', '*', '*'),

    ('api/prefix/groups', 'list', '*', '*', '*', '*'),
#    ('api/prefix/groups', 'list', '*', 'users/username', '*', '*'),
#    ('api/prefix/groups', 'list', '*', 'users', '*', '*'),
#    ('api/prefix/groups', 'list', '*', 'users/name_variants/el', '*', '*'),
#    ('api/prefix/groups', 'list', '*', 'users/name_variants', '*', '*'),

    ('api/prefix/groups', 'partial_update', '*', '*', '*', '*'),
    ('api/prefix/groups', 'partial_update_response', '*', '*', '*', '*'),

    ('api/prefix/groups', 'create', '*', 'users/name_variants', '*', '*'),
    ('api/prefix/groups', 'create', '*', 'users', '*', '*'),
    ('api/prefix/groups', 'create', '*', 'name', '*', '*'),

    ('api/prefix/groups', 'create', '*', '*', '*', '*'),

    ('api/prefix/groups', 'retrieve', '*', '*', '*', '*'),
    ('api/prefix/groups', 'delete', '*', '*', '*', '*'),

    ('api/prefix/groups', 'create_response', '*', '*', '*', '*'),
    ('api/prefix/groups', 'create_response', '*', 'url', '*', '*'),
    ('api/prefix/groups', 'create_response', '*', 'users/username', '*', '*'),
    ('api/prefix/groups', 'create_response', '*', 'users/age', '*', '*'),

    ('api/prefix/groups/users', 'list', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'create', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'create_response', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'retrieve', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'partial_update', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'partial_update_response', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'delete', '*', '*', '*', '*'),

    ('*', 'retrieve', '*', 'url', '*', '*'),
    ('*', 'retrieve', '*', 'name', '*', '*'),
    ('*', 'create', '*', '*', '*', '*'),
]

def get_rules():
    return RULES


def get_rules2():
    return RULES
