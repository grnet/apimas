from pprint import pformat
import traceback


class Error(Exception):
    """Superclass for all exceptions in this module."""

    message = ''
    errs = ()
    log = ()
    codeloc = ''
    what = ''

    def __init__(self, message=None, what='', loc=(), errs=(), **kwargs):
        self.message = message
        self.errs = errs
        self.what = what
        self.loc = loc
        self.codeloc = ':'.join(str(x) for x in traceback.extract_stack()[-2])
        self.kwargs = kwargs

    def to_dict(self):
        args = {}
        args.update(self.kwargs)
        args['Class'] = self.__class__.__name__
        args['Code'] = self.codeloc
        args['Errors'] = [x.to_dict() for x in self.errs]
        args['Location'] = self.loc
        args['Message'] = self.message
        args['What'] = self.what
        return args

    def to_string(self, depth=1):
        return pformat(self.to_dict(), indent=2, width=120)
        #return error_repr(args, depth=depth, header=header, footer=footer)

    def __repr__(self):
        return self.to_string()

    __str__ = __repr__


def error_repr(exc, depth=1, header='[', footer=']'):

    white = '  ' * depth

    if isinstance(exc, Error):
        return exc.to_string(depth=depth)

    args = []
    if isinstance(exc, list):
        args.extend((error_repr(x, depth=depth + 1))
                    for x in exc)
    elif isinstance(exc, dict):
        args.extend(
            ("%s=%s" % (k, error_repr(v, depth=depth + 1)))
            for k, v in exc.iteritems()
        )
    else:
        return repr(exc)

    iterargs = iter(args)

    s = header
    if s:
        s += '\n'
    else:
        for arg in iterargs:
            s += arg
            break

    for arg in iterargs:
        s += white
        s += arg
        s += ',\n'

    s += '  ' * (depth - 1)
    s += footer
    return s


def collect_error(errs, exc):
    if 'errs' in exc.kwargs:
        errs.extend(exc.kwargs['errs'])
    else:
        errs.append(exc)


def report_errors(errs, out=None):
    if out is None:
        import sys
        out = sys.stdout

    out.write("%s\n" % error_repr(errs))


class InvalidInput(Error):
    """Input type or value is semantically not valid."""
    pass


class NotFound(Error):
    """An input-identified resource could not be found."""
    pass


class ValidationError(Error):
    """A validator function failed to validate its input."""
    pass


class FormatError(Error):
    """Input is not well-formed and could not be parsed correcty."""
    pass


class ConflictError(Error):
    """A conflicting runtime state prevents the requested operation."""
    pass


class LimitError(Error):
    """A runtime request exceeds resources limits."""
    pass


class IntegrityError(Error):
    """A runtime assertion for data integrity failed."""
    pass


class FaultError(Error):
    """A runtime I/O operation failed unexpectedly."""
    pass


class ProtocolError(Error):
    """A runtime communication protocol was violated by a remote peer."""
    pass


class TimeoutError(Error):
    """A runtime communication has timed out."""
    pass
