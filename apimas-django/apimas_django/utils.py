from django.core.exceptions import ObjectDoesNotExist
from apimas.errors import NotFound


def get_instance(objects, resource_id):
    """
    Get model instance based on the given resource id.
    """
    try:
        return objects.get(pk=resource_id)
    except (ObjectDoesNotExist, ValueError, TypeError):
        msg = 'Resource with ID {pk!r} not found'
        raise NotFound(msg.format(pk=str(resource_id)))
