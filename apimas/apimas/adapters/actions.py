from functools import wraps


class Response(object):
    """ TODO """
    def __init__(self, content=None, native=None, **kwargs):
        self.content = content
        self.native = native
        self.kwargs = kwargs

    def get_native(self):
        return self.native


class Request(object):
    """ TODO """
    def __init__(self, content=None, native=None, **kwargs):
        self.kwargs = kwargs
        self.native = native
        self.content = content

    def get_native(self):
        return self.native


def handle_exception(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        try:
            return func(*args, **kwargs)
        except:
            if self._error_context is not None:
                response_args = self.handler.handle_error(
                    *self._error_context)
                assert response_args is not None, (
                    'Error handler returned a `NoneType` response'
                )
                return Response(response_args)
            # An unexpectedly error occurred.
            raise
    return wrapper


class ApimasAction(object):
    def __init__(self, collection, action, url, handler, request_proc=None,
                 response_proc=None, orm_model=None, orm_type=None):
        assert bool(orm_model) == bool(orm_type)
        self.collection = collection
        self.action = action
        self.url = url
        self.handler = handler
        self.request_proc = request_proc or []
        self.response_proc = response_proc or []
        self.orm_model = orm_model
        self.orm_type = orm_type
        self.context = {
            'store': self._create_context()
        }
        self._error_context = ()

    def _create_context(self):
        return {
            'orm_model': self.orm_model,
            'orm_type': self.orm_type,
        }

    def _iter_processors(self, processors, *processor_args):
        for processor in processors:
            try:
                processor.process(*processor_args)
            except Exception as e:
                self._error_context = (processor.name, processor_args, e)
                raise

    def get_post_processors(self):
        return self.response_proc

    @handle_exception
    def process_request(self, request):
        # Args for the request processors and handler.
        self.context['request'] = request
        args = (self.collection, self.url, self.action, self.context)
        self._iter_processors(self.request_proc, *args)
        try:
            response_kwargs = self.handler.process(*args)
        except Exception as e:
            self._error_context = (self.handler.name, args, e)
            response_kwargs = self.handler.handle_error(*self._error_context)
        assert response_kwargs is not None, (
            'handler returned a `None` object')
        return Response(**response_kwargs)

    @handle_exception
    def process_response(self, response):
        self.context['response'] = response
        if self._error_context:
            # Error was already handled.
            # Reset error context back to `None`.
            self._error_context = None
            return response
        # Args for the response processors.
        args = (self.collection, self.url, self.action, self.context)
        self._iter_processors(self.response_proc, *args)
        return response
