from apimas.errors import ValidationError
from django.db.models import Q

def create_check(backend_input, instance, context):
    input_status = backend_input['status']
    if input_status not in ['pending', 'hidden']:
        raise ValidationError("Cannot create in status '%s'" % input_status)


def update_check(backend_input, instance, context):
    TRANSITIONS = set([
        ('pending', 'posted'),
    ])

    current_status = instance.status
    input_status = backend_input.get('status')

    if input_status is None or input_status == current_status:
        return

    if (current_status, input_status) not in TRANSITIONS:
        raise ValidationError("Transition not allowed")


def is_posted(context):
    return Q(status='posted')


def is_pending(context):
    return Q(status='pending')


def is_hidden(context):
    return Q(status='hidden')


def non_hidden(context):
    return ~Q(status='hidden')
