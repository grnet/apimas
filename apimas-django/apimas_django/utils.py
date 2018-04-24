from django.core.exceptions import ObjectDoesNotExist
from apimas.errors import NotFound


def get_instance(objects, resource_id, pk_name='pk', strict=True):
    """
    Get model instance based on the given resource id.
    """
    try:
        return objects.get(**{pk_name: resource_id})
    except (ObjectDoesNotExist, ValueError, TypeError):
        if strict:
            msg = 'Resource with ID {pk!r} not found'
            raise NotFound(msg.format(pk=str(resource_id)))
        else:
            return None
