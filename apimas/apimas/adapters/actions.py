from apimas.errors import (AccessDeniedError, NotFound,
                           ValidationError, UnauthorizedError)
from docular import doc_get
from apimas.components import Context


EXC_CODES = {
    ValidationError: 400,
    UnauthorizedError: 401,
    AccessDeniedError: 403,
    NotFound: 404,
}


class ApimasAction(object):
    def __init__(self, collection, url, action_name, status_code, content_type,
                 handler, request_proc=None, response_proc=None):
        self.collection = collection
        self.action_name = action_name
        self.url = url
        self.status_code = status_code
        self.content_type = content_type
        self.handler = handler
        self.request_proc = request_proc or []
        self.response_proc = response_proc or []

    def handle_error(self, func, context):
        try:
            return func(context)
        except Exception as exc:
            exc_type = type(exc)
            status = EXC_CODES.get(exc_type, 500)
            if status == 500:
                import traceback
                print traceback.format_exc()

            headers = context.extract('response/meta/headers') or {}
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
        response = {
            'meta': {
                'content_type': self.content_type,
                'status_code': self.status_code,
            },
        }

        context = Context({
            'request': request,
            'response': response,
        })
        return self.handle_error(self.process_context, context)

    def process_context(self, context):
        for processor in self.request_proc:
            processor.process(context)

        self.handler.process(context)

        for processor in self.response_proc:
            processor.process(context)

        return context.extract('response')


# def extract_from_action(action_spec):
#     handler = action_spec.get('handler')
#     if handler is None:
#         raise InvalidInput('Handler cannot be None')

#     action_url = action_spec.get('url')
#     if action_url is None:
#         raise InvalidInput('URL not found for action')

#     handler = utils.import_object(handler)
#     pre = [utils.import_object(x) for x in action_spec.get('pre', [])]
#     post = [utils.import_object(x) for x in action_spec.get('post', [])]
#     return action_url, handler, pre, post
