"""
Module with helper functions for unit testing.
"""

import mock
from apimas.documents import ConstructorContext


def create_mock_object(cls, isolated_attrs, ismagic=False):
    """
    Function to create a `mock.Mock` object with functionality taken from
    a specific class. This mock object contains all functionality (attributes,
    methods) which are specified by arguments.
    """
    kwargs = {}
    for attr in isolated_attrs:
        cls_attr = cls.__dict__.get(attr)
        if cls_attr is None:
            raise AttributeError(
                'Attribute {!r} cannot found on class {!r}'.format(
                    attr, cls.__name__))
        kwargs[attr] = cls_attr
    return mock.Mock(spec=cls, **kwargs) if not ismagic else\
        mock.MagicMock(spec=cls, **kwargs)


def create_mock_constructor_context(**kwargs):
    """
    It creates a mock object to be passed as the context of constructors.
    """
    # Dictionary of constructor context fields and their default values.
    field_default = {
        'instance': {},
        'loc': (),
        'spec': {},
        'cons_round': 0,
        'parent_name': None,
        'parent_spec': {},
        'top_spec': {},
        'sep': None,
        'constructor_index': None,
        'cons_siblings': [],
        'constructed': [],
        'context': None,
    }
    cons_kwargs = {field: kwargs.get(field, default)
                   for field, default in field_default.iteritems()}
    return ConstructorContext(**cons_kwargs)
