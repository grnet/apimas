import warnings
from functools import wraps
from apimas.errors import InvalidInput
from docular import DeferConstructor


def _check_type(constructors):
    if not isinstance(constructors, (tuple, list)):
        msg = ('Given constructors must be either `list` or `tuple`,'
               ' type of {type!s} found instead')
        raise InvalidInput(msg.format(type=type(constructors)))


def conditional(constructors):
    """
    Run constructor only if the given constructors are in the list of its
    constructors siblings.
    """
    _check_type(constructors)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = kwargs.get('context')
            missing_cons = set(constructors).difference(context['local_predicates'])
            if missing_cons:
                msg = ('Constructor ({!r}) will not run because it is '
                       'dependent on missing constructors ({!r})')
                warnings.warn(
                    msg.format(', '.join(context['loc']), ', '.join(missing_cons)),
                    UserWarning)
                return context['instance']
            return func(*args, **kwargs)
        return wrapper
    return decorator


def after(constructors, ignore_missing=True):
    """
    Defer the construction of the given decorated function until all the
    constuctors given as parameter are finished.
    """
    _check_type(constructors)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = kwargs.get('context')
            constructed = context['constructed']
            all_constructors = context['local_predicates']
            cons_set = set(constructors)
            missing_cons = cons_set.difference(all_constructors)
            if missing_cons and not ignore_missing:
                msg = ('Constructor ({!r}) cannot run because it is'
                       ' dependent on missing constructors ({!r})')
                raise InvalidInput(
                    msg.format(', '.join(context['loc']),
                        ', '.join(missing_cons)))
            if not all(c in constructed
                       for c in cons_set.intersection(all_constructors)):
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
        all_constructors = context['local_predicates']
        constructed = context['constructed']
        if len(constructed) < len(all_constructors) - 1:
            raise DeferConstructor
        return func(*args, **kwargs)
    return wrapper
