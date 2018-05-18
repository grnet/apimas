
class GenericException(Exception):
    """Superclass for all exceptions in this module."""
    http_code = 500

    def __init__(self, message=None, *args, **kwargs):
        self.message = message
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        args = ', '.join(repr(x) for x in self.args)
        kwargs = ', '.join(('%s=%s' % (str(k), repr(v)))
                           for k, v in self.kwargs.iteritems())
        arglist = ['%s=%s' % ('message', repr(self.message))]
        if args:
            arglist.append(args)
        if kwargs:
            arglist.append(kwargs)

        arglist = ', '.join(arglist)
        s = "{name}({arglist})"
        s = s.format(name=self.__class__.__name__, arglist=arglist)
        return s

    def __str__(self):
        if self.message:
            return str(self.message)
        return repr(self)


class ValidationError(GenericException):
    """A runtime user input validation check has failed."""
    http_code = 400


class UnauthorizedError(GenericException):
    """
    A party requests for a particular resource but it cannot be authenticated.
    """
    http_code = 401


class AccessDeniedError(GenericException):
    """ Access to a particular resource is denied. """
    http_code = 403


class NotFound(GenericException):
    """A runtime lookup has failed to locate a name or path."""
    http_code = 404


class ConflictError(GenericException):
    """A runtime request cannot be fulfilled because of conflicting state."""
    http_code = 409


class InvalidInput(GenericException):
    """Code was called with invalid arguments."""
    pass


class AdapterError(GenericException):
    """ A runtime error during construction process of adapter. """
    def __init__(self, message=None, loc=(), *args, **kwargs):
        self.loc = loc
        kwargs['loc'] = loc
        super(AdapterError, self).__init__(
            message=message, *args, **kwargs)

    def __str__(self):
        exstr = super(AdapterError, self).__str__()
        if self.loc:
            return '{msg}, on location: ({loc})'.format(
                msg=exstr, loc=', '.join(self.loc))
        return exstr

class InvalidSpec(AdapterError):
    """ Specification cannot be understood by the adapter. """
    pass
