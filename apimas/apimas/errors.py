
class GenericException(Exception):
    """Superclass for all exceptions in this module."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        args = ', '.join(repr(x) for x in self.args)
        kwargs = ', '.join(('%s=%s' % (str(k), repr(v)))
                           for k, v in self.kwargs.iteritems())
        arglist = []
        if args:
            arglist.append(args)
        if kwargs:
            arglist.append(kwargs)

        arglist = ', '.join(arglist)
        s = "{name}({arglist})"
        s = s.format(name=self.__class__.__name__, arglist=arglist)
        return s

    def __str__(self):
        if 'message' in self.kwargs:
            return str(self.kwargs['message'])

        if self.args:
            return str(self.args[0])

        return repr(self)


class GenericInputError(GenericException):
    """Runtime error while handling application input."""
    pass


class GenericProgrammingError(GenericException):
    """Runtime error due to incorrect programming."""
    pass


class GenericFault(GenericException):
    """Runtime error due to data corruption or failed assertion."""
    pass


class NotFound(GenericInputError):
    """A runtime lookup has failed to locate a name or path."""
    pass


class ValidationError(GenericInputError):
    """A runtime user input validation check has failed."""
    pass


class FormatError(GenericInputError):
    """A runtime encoded input cannot be decoded."""
    pass


class ConflictError(GenericInputError):
    """A runtime request cannot be fulfilled because of conflicting state."""
    pass


class LimitError(GenericInputError):
    """A runtime request exceeds resources limits."""
    pass


class InvalidInput(GenericProgrammingError):
    """Code was called with invalid arguments."""
    pass


class IntegrityError(GenericFault):
    """A runtime assertion for application data integrity failed."""
    pass


class FaultError(GenericFault):
    """A runtime I/O operation failed unexpectedle."""
    pass


class ProtocolError(GenericFault):
    """A runtime communication protocol was violated by a remote peer."""
    pass


class TimeoutError(GenericFault):
    """A runtime communication has timed out."""
    pass
