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


def censor_one(instance, context):
    auth_user = context.extract(u'auth/user')
    username = auth_user.username

    if username in instance.body:
        return None
    return instance


def censor_all(unchecked_response, context):
    response = []
    for instance in unchecked_response:
        instance = censor_one(instance, context)
        if instance is not None:
            response.append(instance)
    return response


def is_posted(context):
    return Q(status='posted')


def is_pending(context):
    return Q(status='pending')


def is_hidden(context):
    return Q(status='hidden')


def non_hidden(context):
    return ~Q(status='hidden')
