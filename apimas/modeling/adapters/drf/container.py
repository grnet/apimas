from django.conf.urls import url, include
from rest_framework import routers
from apimas.modeling.adapters.drf import utils
from apimas.modeling.adapters.drf.schemas import (
    RESOURCE_SCHEMA_VALIDATOR, API_SCHEMA_VALIDATOR)
from apimas.modeling.adapters.drf.views import generate


RESOURCES_LOOKUP_FIELD = 'resources'
MODEL_LOOKUP_FIELD = 'model'


class Container(object):
    """
    Class responsible for the creation of views according to a model and
    a configuration object.
    """
    def __init__(self, api):
        self.api = api
        self.router = routers.DefaultRouter()
        self._validated_schema = None

    def create_view(self, resource_name, model, config):
        """
        Create a single view for the given model, configuration object and the
        resource name.

        :param resource_name: URI of the corresponding view.
        :param model: Model class based on which viewset is generated.
        :param config: Dictionary which includes all required configuration
        of this endpoint.
        """
        self.register_view(resource_name, model, config)
        return url(r'^' + self.api + '/', include(self.router.urls))

    def register_view(self, resource_name, model, config, **kwargs):
        """
        Creates and registers a view to the list of already created.

        :param resource_name: URI of the corresponding view.
        :param model: Model class based on which viewset is generated.
        :param config: Dictionary which includes all required configuration
        of this endpoint.
        """
        if not self._validated_schema:
            self.validate_schema(config, RESOURCE_SCHEMA_VALIDATOR)
        self.router.register(resource_name, generate(model, config, **kwargs),
                             base_name=model._meta.model_name)

    def create_api_views(self, api_schema):
        """
        Create a multiple views according to the API Schema given as parameter.
        """
        self._validated_schema = self.validate_schema(
            api_schema, API_SCHEMA_VALIDATOR)
        global_settings = api_schema.get('global', {})
        for resource, config in api_schema.get(
                RESOURCES_LOOKUP_FIELD, {}).iteritems():
            model = utils.import_object(config.get(MODEL_LOOKUP_FIELD, ''))
            self.register_view(resource, model, config, **global_settings)
        return url(r'^' + self.api + '/', include(self.router.urls))

    def validate_schema(self, schema, validator):
        """ Validates a configuration object against a validation schema. """
        if not validator.validate(schema):
            raise utils.DRFAdapterException(API_SCHEMA_VALIDATOR.errors)
        return schema
