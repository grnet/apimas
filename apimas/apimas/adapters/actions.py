from functools import wraps
from apimas import utils
from apimas.errors import InvalidInput


def handle_exception(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        try:
            return func(*args, **kwargs)
        except:
            if self._error_context is not None:
                clear_err = self._error_context[-1]
                response_kwargs = self.handler.handle_error(
                    *self._error_context[:-1])
                assert response_kwargs is not None, (
                    'Error handler returned a `NoneType` response'
                )
                if clear_err:
                    self._error_context = None
                return response_kwargs
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
        self._error_context = None

    def _create_context(self):
        return {
            'orm_model': self.orm_model,
            'orm_type': self.orm_type,
        }

    def _iter_processors(self, processors, *processor_args, **kwargs):
        clear_err = kwargs.get('clear_err', False)
        for processor in processors:
            try:
                processor.process(*processor_args)
            except Exception as e:
                self._error_context = (processor.name, processor_args, e,
                                       clear_err)
                raise

    def get_post_processors(self):
        return self.response_proc

    @handle_exception
    def process_request(self, request):
        # Args for the request processors and handler.
        context = {
            'store': self._create_context()
        }
        context['request'] = request
        args = (self.collection, self.url, self.action, context)
        self._iter_processors(self.request_proc, *args)
        try:
            response_kwargs = self.handler.process(*args)
        except Exception as e:
            self._error_context = (self.handler.name, args, e, False)
            response_kwargs = self.handler.handle_error(
                *self._error_context[:-1])
        assert response_kwargs is not None, (
            'handler returned a `None` object')
        context['response'] = response_kwargs
        return context

    @handle_exception
    def process_response(self, context):
        response = context['response']
        if self._error_context:
            # Error was already handled.
            # Reset error context back to `None`.
            self._error_context = None
            return response
        # Args for the response processors.
        args = (self.collection, self.url, self.action, context)
        self._iter_processors(self.response_proc, clear_err=True, *args)
        return response


def extract_from_action(action_spec):
    handler = action_spec.get('handler')
    if handler is None:
        raise InvalidInput('Handler cannot be None')

    action_url = action_spec.get('url')
    if action_url is None:
        raise InvalidInput('URL not found for action')

    handler = utils.import_object(handler)
    pre = [utils.import_object(x) for x in action_spec.get('pre', [])]
    post = [utils.import_object(x) for x in action_spec.get('post', [])]
    return action_url, handler, pre, post
