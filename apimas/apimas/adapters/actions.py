from functools import wraps
from apimas import utils
from apimas.errors import (AccessDeniedError, NotFound, InvalidInput,
                           ValidationError, UnauthorizedError)
from docular import doc_get
from apimas.utils import normalize_path


EXC_CODES = {
    ValidationError: 400,
    UnauthorizedError: 401,
    AccessDeniedError: 403,
    NotFound: 404,
}


def extract(context, path):
    path = normalize_path(path)
    return doc_get(context, path)


class ApimasAction(object):
    def __init__(self, collection, url, action_name, status_code, content_type,
                 handler, request_proc=None, response_proc=None,
                 orm_model=None, orm_type=None):
        assert bool(orm_model) == bool(orm_type)
        self.collection = collection
        self.action_name = action_name
        self.url = url
        self.status_code = status_code
        self.content_type = content_type
        self.handler = handler
        self.request_proc = request_proc or []
        self.response_proc = response_proc or []
        self.orm_model = orm_model
        self.orm_type = orm_type

    def _create_context(self):
        return {
            'orm_model': self.orm_model,
            'orm_type': self.orm_type,
        }

    def get_post_processors(self):
        return self.response_proc

    def handle_error(self, func, context):
        try:
            return func(context)
        except Exception as exc:
            exc_type = type(exc)
            status = EXC_CODES.get(exc_type, 500)
            if status == 500:
                import traceback
                print traceback.format_exc()

            headers = extract(context, 'response/meta/headers') or {}
            details = getattr(exc, 'kwargs', {}).get('details')
            content = details if details else {'details': exc.message}
            return {
                'content': content,
                'meta': {
                    'content_type': self.content_type,
                    'status_code': status,
                    'headers': headers,
                }
            }

    def process(self, request):
        context = {
            'store': self._create_context()
        }
        context['request'] = request
        return self.handle_error(self.process_context, context)

    def process_context(self, context):
        args = (self.collection, self.url, self.action_name, context)

        for processor in self.request_proc:
            processor.process(*args)

        response_content = self.handler.process(*args)
        response = {
            'content': response_content,
            'meta': {
                'content_type': self.content_type,
                'status_code': self.status_code,
            },
        }
        context['response'] = response

        for processor in self.response_proc:
            processor.process(*args)

        return context['response']


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
