from django.core.exceptions import ObjectDoesNotExist
from apimas.errors import NotFound


def get_instance(orm_model, resource_id):
    """
    Get model instance based on the given resource id.

    Args:
        orm_model: ORM model which corresponds to the resource we want
            to retrieve.
        resource_id: ID of resource to be retrieved.

    Raises:
        NotFound: A model instance with the given id cannot be found.
    """
    try:
        return orm_model.objects.get(pk=resource_id)
    except (ObjectDoesNotExist, ValueError, TypeError):
        msg = 'Resource with ID {pk!r} not found'
        raise NotFound(msg.format(pk=str(resource_id)))
