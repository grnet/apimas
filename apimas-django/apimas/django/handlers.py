from django.db.models import Model
from django.db.models.query import QuerySet
from apimas import utils
from apimas.django import utils as django_utils
from apimas.errors import (AccessDeniedError, NotFound, InvalidInput,
                           ValidationError, UnauthorizedError)
from apimas.components import BaseHandler
from apimas.components.processors import DeSerialization


REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='


class DjangoBaseHandler(BaseHandler):
    """
    Base handler for django specific actions.

    This handler requires a django model to either read or write data. This
    handler assumes that there is an interaction with django models, e.g.
    a query, an insertion, etc.

    This handler extracts the following data from context:
        * `model`: Django model with which handler interacts.
        * `data`: A dictionary representing data of request (if any).
        * `pk`: Primary key of the resource if handler operates on a specific
                model instance, e.g. update.

    The final response of the handler is a dictionary of kwargs needed by
    APIMAS in order response can be constructed later. This includes:
        * `content`: A `django.db.models.Model` or
            `django.db.models.query.QuerySet` instance.
        * `content_type`: Content type of response, e.g. `application/json`.
        * `status_code`: Status code of response, e.g. 201.


    Django base handler also offers a hook (i.e. method `execute()`) where
    other handlers can execute arbitrary code. It is the actual
    interaction with the django models, where a model instance or a QuerySet
    is expected as the output of this hook.

    Attributes:
        name (str): The identifier of this handler.
        READ_KEYS (dict): Human readable keys which are mapped to the actual
            keys of context from which processor reads.
        REQUIRED_KEYS (set): Required keys for the adapter.

    Examples:
        A very simple handler that uses Django BaseHandler is the following
        which operates on resources. It takes the django model and pk as
        specified by the request and the corresponding model instance.

        >>> from apimas.errors import InvalidInput
        >>> from apimas.django.handlers import BaseHandler
        >>> class MyHandler(BaseHandler):
        ...     name = 'myapp.mymodule.MyHandler'
        ...     def execute(self, collection, url, action, context_data):
        ...        model = context_data['model']
        ...        pk = context_data.get('pk')
        ...        if pk is None:
        ...            raise InvalidInput('Handler operates on resources.')
        ...        return model.objects.get(pk=pk)
    """
    name = 'apimas.django.handlers.DjangoBaseHandler'

    READ_KEYS = {
        'model': 'store/orm_model',
        'pk': 'request/meta/pk',
    }
    READ_KEYS.update(DeSerialization.WRITE_KEYS)

    REQUIRED_KEYS = {
        'model',
    }

    def _parse_ref(self, orm_model, data):
        """
        A function used to handle the case of related fields (either one
        or many).

        * In case of one to one or many to one relations, we use the
          `<field_name>_id` as key.

        * In case of many to many or one to many relations, we isolate
          the data used for the many relations and we extract the actual
          model instances corresponding to the primary keys.
        """
        ref_keys = []
        many_ref_keys = []
        spec_properties = self.spec.get('*')
        for k, v in spec_properties.iteritems():
            if REF in v:
                ref_keys.append(k)
            if ARRAY_OF in v and REF in v[ARRAY_OF]:
                many_ref_keys.append(k)
        for k in ref_keys:
            data[k + '_id'] = data.pop(k, None)
        many = {}
        for k in many_ref_keys:
            field = orm_model._meta.get_field(k)
            ids = data.pop(k, [])
            if not ids:
                continue
            many[k] = [field.related_model.objects.get(
                pk=refid) for refid in ids]
        return data, many


    def get_resource(self, orm_model, resource_id, context):
        """
        Get model instance based on the given resource id.

        Args:
            orm_model: ORM model which corresponds to the resource we want
                to retrieve.
            resource_id: ID of resource to be retrieved.

        Raises:
            NotFound: A model instance with the given id cannot be found.
        """
        instance = context.get('instance')
        if not instance:
            instance = django_utils.get_instance(orm_model, resource_id)
        return instance

    def read_context(self, context):
        """
        Reads handler-specific keys from context.

        Args:
            context (dict): Request context.

        Raises:
            InvalidInput: Given is not valid for the handler.

        Returns:
            dict: A subset of context which contains only the
            handler-specific fields.
        """
        data = {}
        for k, v in self.READ_KEYS.iteritems():
            value = self.extract(context, v)
            if value is None and k in self.REQUIRED_KEYS:
                msg = 'Key {key!r} is required for this handler'
                raise InvalidInput(msg.format(key=k))
            data[k] = value
        return data

    def execute(self, collection, url, action, context_data):
        """
        Actual hook of a django handler.

        It is expected that there would be an interaction with the django
        models, and therefore, a model instance or queryset to be returned as
        the content of the handler's response.

        Args:
            collection (str): Collection corresponding to the handler.
            url (str): Relative URL of the action.
            action (str): Action name correspond to the handler.
            context_data (dict): Handler-specific keys extracted from
                request context.
        Returns:
            A model instance or a queryset corresponding to the interaction of
            handler with the django models. Returns `None` for an empty
            response.

        """
        raise NotImplementedError('execute() must be implemented')

    def handle_error(self, component, cmp_args, ex):
        """
        Handles any error occcured in handler or processors.

        Args:
            component (str): Identifier of handler/processor in which error
                occured.
            cmp_args (tuple): Args with which handler/processors was called
                 by apimas.
            ex: Error instance raised by handler of processors.

        Returns:
            dict: Dictionary of response content along with HTTP args in order
                response can be constructed properly later (namely HTTP status
                code and and HTTP content type).
        """
        exceptions = {
            ValidationError: 400,
            UnauthorizedError: 401,
            AccessDeniedError: 403,
            NotFound: 404,
            Exception: 500,
        }
        type_ex = type(ex)
        if type_ex not in exceptions:
            status = 500
        else:
            status = exceptions[type_ex]
        context = cmp_args[-1]
        # Check if any processor has provided response headers.
        headers = self.extract(context, 'response/meta/headers') or {}
        details = getattr(ex, 'kwargs', {}).get('details')
        content = (
            details
            if details
            else {'details': ex.message}
        )
        return {
            'content': content,
            'meta': {
                'content_type': 'application/json',
                'status_code': status,
                'headers': headers,
            }
        }

    def adapt_instance(self, resource, context_data, context):
        """
        Gets a model instance or a QuerySet, converts it into a native format
        and returns it as a part of handler's response.

        Args:
            resource: Model instance or QuerySet derived from the actual
                interaction of the handler with django models.
            context_data (dict): Dict with handler-specific keys, read from
                context.
            context (dict): Request context.

        Returns:
            dict: Handler's response, which includes the python native format
                of the model instance along with HTTP args in order response
                can be constructed properly later (namely HTTP status code and
                HTTP content type).
        """
        if resource and (not isinstance(resource, Model) and not
                       isinstance(resource, QuerySet)):
            msg = 'A model instance or a queryset is expected. {!r} found.'
            raise InvalidInput(msg.format(str(type(resource))))

        return {
            'content': resource,
            'meta': {
                'content_type': self.CONTENT_TYPE,
                'status_code': self.STATUS_CODE,
            }
        }

    def process(self, collection, url, action, context):
        """
        Django adapter includes three stages:
            * Reads required keys from the request context.
            * Produces a model instance/QuerySet based on the handler-specific
              data.
            * Returns the response using the python native format
              of the output of previous step.
        """
        context_data = self.read_context(context)
        output = self.execute(collection, url, action, context_data)
        return self.adapt_instance(output, context_data, context)


class CreateHandler(DjangoBaseHandler):
    name = 'apimas.django.handlers.CreateHandler'

    STATUS_CODE = 201
    CONTENT_TYPE = 'application/json'
    REQUIRED_KEYS = {
        'model',
        'data',
    }

    def execute(self, collection, url, action, context_data):
        """ Creates a new django model instance. """
        model = context_data['model']
        data = context_data['data']
        data, many = self._parse_ref(model, data)
        instance = model.objects.create(**data)
        if many:
            for k, v in many.iteritems():
                getattr(instance, k).add(*v)
        return instance


class ListHandler(DjangoBaseHandler):
    name = 'apimas.django.handlers.ListHandler'

    STATUS_CODE = 200
    CONTENT_TYPE = 'application/json'
    REQUIRED_KEYS = {
        'model',
    }

    def execute(self, collection, url, action, context_data):
        """
        Gets all django model instances based on the orm model extracted
        from request context.
        """
        model = context_data['model']
        return model.objects.all()


class RetrieveHandler(DjangoBaseHandler):
    name = 'apimas.django.handlers.RetrieveHandler'

    STATUS_CODE = 200
    READ_KEYS = {
        'instance': 'store/instance',
    }
    READ_KEYS.update(DjangoBaseHandler.READ_KEYS)
    CONTENT_TYPE = 'application/json'
    REQUIRED_KEYS = {
        'model',
        'pk',
    }

    def execute(self, collection, url, action, context_data):
        """
        Gets a single model instance which based on the orm model and
        resource ID extracted from request context.
        """
        model = context_data['model']
        pk = context_data['pk']
        return self.get_resource(model, pk, context_data)


class UpdateHandler(CreateHandler):
    name = 'apimas.django.handlers.UpdateHandler'

    STATUS_CODE = 200
    READ_KEYS = {
        'instance': 'store/instance',
    }
    READ_KEYS.update(DjangoBaseHandler.READ_KEYS)
    CONTENT_TYPE = 'application/json'
    REQUIRED_KEYS = {
        'model',
        'pk',
        'data',
    }

    def _update_obj(self, obj, data):
        for k, v in data.iteritems():
            setattr(obj, k, v)
        obj.save()
        return obj

    def execute(self, collection, url, action, context_data):
        """
        Updates an existing model instance based on the data of request.
        """
        model = context_data['model']
        pk = context_data['pk']
        data = context_data['data']
        instance = self.get_resource(model, pk, context_data)
        data, many = self._parse_ref(model, data)
        instance = self._update_obj(instance, data)
        if many:
            for k, v in many.iteritems():
                getattr(instance, k).add(*v)
        return instance


class DeleteHandler(RetrieveHandler):
    name = 'apimas.django.handlers.DeleteHandler'

    STATUS_CODE = 204
    READ_KEYS = {
        'instance': 'store/instance',
    }
    READ_KEYS.update(DjangoBaseHandler.READ_KEYS)
    CONTENT_TYPE = None
    REQUIRED_KEYS = {
        'model',
        'pk',
    }

    def execute(self, collection, url, action, context_data):
        """ Deletes an existing model instance. """
        instance = super(DeleteHandler, self).execute(
            collection, url, action, context_data)
        instance.delete()
        return None


class TokenAuthHandler(BaseHandler):
    """
    Add handler for generating JWT tokens to authenticated parties.
    """
    READ_KEYS = {
        'headers': 'request/meta/headers',
    }

    def __init__(self, collection, spec, auth_method,
                 **meta):
        super(TokenAuthHandler, self).__init__(collection, spec, **meta)

        secret_key_extractor = meta.get('secret_key')
        if secret_key_extractor is None:
            raise InvalidInput('Secret key is missing')
        secret_key_extractor = utils.import_object(secret_key_extractor)
        assert callable(secret_key_extractor), 'Secret key must be a callable'

        self.auth_method = auth_method

        user_processor = meta.get('user_processor')
        if user_processor:
            self.user_processor = utils.import_object(user_processor)
            assert callable(self.user_processor), (
                '"user_processor" must be a callable')

        token_gen = meta.get('token_generator')
        if token_gen is None:
            raise InvalidInput('Token generator is required')
        self.token_gen = utils.import_object(token_gen)
        assert callable(self.token_gen), ('"token_gen" must be a callable')

    def process(self, collection, url, action, context):
        """
        Client is authenticated based on a specific authentication method,
        specified by `auth_method` and then generates a new JWT token.
        """
        context_data = self.read(context)
        user = self.auth_method.authenticate(context_data['headers'])
        if self.user_processor:
            user = self.user_processor(user)
        content = self.token_gen(user)
        return {
            'content': content,
            'meta': {
                'content_type': 'application/json',
                'status_code': 200,
            }
        }

    def handle_error(self, component, cmp_args, ex):
        # This handler maps only `UnauthorizedError` exceptions to status
        # codes.
        status_code = 401 if isinstance(ex, UnauthorizedError) else 500
        return {
            'content': {
                'details': ex.message,
            },
            'meta': {
                'content_type': 'application/json',
                'status_code': status_code,
                'headers': {
                    'WWW-Authenticate': getattr(
                        self.auth_method, 'AUTH_HEADERS', None)
                },
            }
        }
