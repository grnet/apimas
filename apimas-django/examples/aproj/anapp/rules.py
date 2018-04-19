# COLUMNS = ('collection', 'action', 'role', 'filter', 'check', 'fields', 'comment')

RULES = [

    ('api/prefix/enhanceduser', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/enhanceduser', 'retrieve', 'anonymous', '*', '*', 'id', '*'),
    ('api/prefix/enhanceduser', 'retrieve', 'user',
     'anapp.models.EnhancedUser.is_own', '*', '*', '*'),

    ('api/prefix/enhanceduser', 'partial_update', 'user',
     'anapp.models.EnhancedUser.is_own', '*',
     'user/first_name,user/last_name,user/password', '*'),

    ('api/prefix/institutions', 'retrieve', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'list', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'partial_update', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'update', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'delete', '*', '*', '*', '*', '*'),

    ('api/prefix/groups', 'list', '*', '*', '*', '*', '*'),
    ('api/prefix/groups', 'retrieve', '*', '*', '*', '*', '*'),
    ('api/prefix/groups', 'partial_update', '*', '*', '*', '*', '*'),
    ('api/prefix/groups', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/groups', 'delete', '*', '*', '*', '*', '*'),

    ('api/prefix/groups/members', 'list', '*', '*', '*', '*', '*'),
    ('api/prefix/groups/members', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/groups/members', 'retrieve', '*', '*', '*', '*', '*'),
    ('api/prefix/groups/members', 'partial_update', '*', '*', '*', '*', '*'),
    ('api/prefix/groups/members', 'delete', '*', '*', '*', '*', '*'),

    ('api/prefix/posts', 'list', 'admin', '*', '*', '*', '*'),
    ('api/prefix/posts', 'list', 'user', 'non_hidden', 'censor_all', '*', '*'),

    ('api/prefix/posts', 'create', 'admin', '*', '*', '*', '*'),
    ('api/prefix/posts', 'create', 'user', '*', 'create_check', '*', '*'),

    ('api/prefix/posts', 'partial_update', 'admin', '*', '*', '*', '*'),
    ('api/prefix/posts', 'partial_update', 'user', 'is_pending', 'update_check', 'title,status', '*'),

    ('api/prefix/posts', 'delete', 'admin', 'is_hidden', '*', '*', '*'),

    ('api/prefix/posts', 'retrieve', 'admin', '*', '*', '*', '*'),
    ('api/prefix/posts', 'retrieve', 'user', 'non_hidden', 'censor_one', '*', '*'),
    ('api/prefix/posts', 'retrieve', 'anonymous', 'is_posted', '*', 'id,title,status', '*'),

    ('api/prefix/posts2', 'retrieve', '*', 'checks.is_posted', '*', '*', '*'),

    ('api/prefix/nulltest', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/nulltest', 'retrieve', '*', '*', '*', '*', '*'),

    ('api/prefix/features', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/features', 'retrieve', '*', '*', '*', '*', '*'),
]

def get_rules():
    return RULES


def get_rules2():
    return RULES
