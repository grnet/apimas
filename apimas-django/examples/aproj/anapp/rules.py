# COLUMNS = ('collection', 'action', 'role', 'field', 'state', 'comment')

RULES = [
    ('*', 'list', '*', '*', '*', '*'),
    ('*', 'retrieve', '*', 'url', '*', '*'),
    ('*', 'retrieve', '*', 'name', '*', '*'),
    ('*', 'create', '*', '*', '*', '*'),
]

def get_rules():
    return RULES


def get_rules2():
    return RULES
