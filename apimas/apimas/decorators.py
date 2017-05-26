from functools import wraps
from apimas.errors import InvalidInput
from apimas.documents import DeferConstructor


def after(constructors):
    """
    Defer the construction of the given decorated function until all the
    constuctors given as parameter are finished.
    """
    if not isinstance(constructors, (tuple, list)):
        msg = ('Given constructors must be either `list` or `tuple`,'
               ' type of {type!s} found instead')
        raise InvalidInput(msg.format(type=type(constructors)))

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = kwargs.get('context')
            constructed = context.constructed
            all_constructors = context.cons_siblings

            actual_cons = set(constructors).intersection(all_constructors)
            if not all(c in constructed for c in actual_cons):
                raise DeferConstructor
            return func(*args, **kwargs)
        return wrapper
    return decorator


def last(func):
    """
    Defer the construction of the decorated function, until the rest
    constructors of the node are finished.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        context = kwargs.get('context')
        all_constructors = context.cons_siblings
        constructed = context.constructed
        if len(constructed) < len(all_constructors) - 1:
            raise DeferConstructor
        return func(*args, **kwargs)
    return wrapper
