from apimas.errors import (AccessDeniedError, NotFound, InvalidInput,
                           ValidationError, UnauthorizedError)
from docular import doc_get
from apimas.components import Context
from django.db import transaction


EXC_CODES = {
    ValidationError: 400,
    UnauthorizedError: 401,
    AccessDeniedError: 403,
    NotFound: 404,
}


def get_indices(processors, begin_before, end_after):
    begin_before_idx, end_after_idx = None, None
    for idx, (key, processor) in enumerate(processors):
        if begin_before == key:
            begin_before_idx = idx
        if end_after == key:
            end_after_idx = idx
    if begin_before_idx is None or end_after_idx is None:
        raise InvalidInput('Failed to configure transaction')
    return begin_before_idx, end_after_idx


def seconds(tuple_list):
    if not tuple_list:
        return []
    return zip(*tuple_list)[1]


def run_processors(processors, context):
    for processor in processors:
        processor.process(context)


class ApimasAction(object):
    def __init__(self, collection, url, action_name, status_code, content_type,
                 transaction_begin_before, transaction_end_after, processors):
        self.collection = collection
        self.action_name = action_name
        self.url = url
        self.status_code = status_code
        self.content_type = content_type

        if transaction_begin_before is not None and \
           transaction_end_after is not None:
            begin_before_idx, end_after_idx = get_indices(
                processors, transaction_begin_before, transaction_end_after)
            self.before_transaction = seconds(processors[0:begin_before_idx])
            self.in_transaction = seconds(
                processors[begin_before_idx:end_after_idx + 1])
            self.after_transaction = seconds(
                processors[end_after_idx + 1:])
        else:
            self.before_transaction = seconds(processors)
            self.in_transaction = []
            self.after_transaction = []

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
        run_processors(self.before_transaction, context)

        if self.in_transaction:
            with transaction.atomic():
                run_processors(self.in_transaction, context)

        run_processors(self.after_transaction, context)

        return context.extract('response')
