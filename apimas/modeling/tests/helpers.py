"""
Module with helper functions for unit testing.
"""

import mock


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
            raise AttributeError('Attribute %s cannot found on class %s' % (
                attr, cls.__name__))
        kwargs[attr] = cls_attr
    return mock.Mock(spec=cls, **kwargs) if not ismagic else\
        mock.MagicMock(spec=cls, **kwargs)
