from django.apps import apps
from django.conf.urls import url, include
from rest_framework import routers
from apimas import utils
from apimas.views import generate


APP_MODELS = apps.get_models()


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

    def create_view(self, resource_name, model, config):
        """
        Create a single view for the given model, configuration object and the
        resource name.

        :param resource_name: URI of the corresponding view.
        :param model: Model class based on which viewset is generated.
        :param config: Dictionary which includes all required configuration
        of this endpoint.
        """
        self.validate_view(model, config)
        self.router.register(resource_name, generate(model, config),
                             base_name=model._meta.model_name)
        return url(r'^' + self.api + '/', include(self.router.urls))

    def register_view(self, resource_name, model, config):
        """
        Creates and registers a view to the list of already created.

        :param resource_name: URI of the corresponding view.
        :param model: Model class based on which viewset is generated.
        :param config: Dictionary which includes all required configuration
        of this endpoint.
        """
        self.validate_view(model, config)
        self.router.register(resource_name, generate(model, config),
                             base_name=model._meta.model_name)

    def create_api_views(self, api_schema):
        """
        Create a multiple views according to the API Schema given as parameter.
        """
        for resource, config in api_schema.get(
                RESOURCES_LOOKUP_FIELD, {}).iteritems():
            model = utils.import_object(config.get(MODEL_LOOKUP_FIELD, ''))
            self.register_view(resource, model, config)
        return url(r'^' + self.api + '/', include(self.router.urls))

    def validate_view(self, model, config):
        # TODO perhaps we could define a validation schema for the given
        # configuration schema, like JSON schema, XSD, etc.
        if not config:
            raise utils.ApimasException()
        if model not in APP_MODELS:
            raise utils.ApimasException()
