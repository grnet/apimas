import random
from django.db import models
from django.core.files.uploadedfile import SimpleUploadedFile
from apimas import documents as doc
from apimas.errors import InvalidInput
from apimas.decorators import after
from apimas.utils import generators as gen, import_object, urljoin


def generate_file(file_name=None, size=8, archived=True):
    """
    Generate a mock file used to represent an uploaded file for a django
    request.

    Args:
        file_name (str): (optional) Name of the mock file. If `None` a
            random name is generated.
        size (int):  (optional) Size of the generated file in bytes.
        archived (bool): `True` if generated file should be archived.
    """
    file_name = file_name or gen.fake.file_name()
    mock_file = gen.generate_fake_file(size=size, archived=archived)
    uploaded = SimpleUploadedFile(
        file_name, mock_file.getvalue(), content_type=gen.fake.mime_type())
    mock_file.close()
    return uploaded


def generate_ref(to, instances=None, root_url=None):
    """
    Generates a ref URL based on the given endpoint which points to one of
    the existing model instances.

    Args:
        to (str): Collection path from which URL is constructed, e.g. api/foo.
        instances (dict): A dictionary of lists which containts the existing
            model instances per collection path.
        root_url (str): Root of URL, e.g. http://localhost.

    Returns:
        URL pointing to a specific instance of a collection, e.g. api/foo/1/.
    """
    instances = instances or {}
    ref_instances = instances.get(to)
    random_instance = random.choice(ref_instances)
    if random_instance is None:
        return None
    ref = to.strip('/') + '/'
    if root_url:
        return urljoin(root_url, ref, str(random_instance.pk))
    else:
        return urljoin(ref, str(random_instance.pk))


class DjangoRequestGenerator(gen.RequestGenerator):
    """
    A generator used to create random data in order to make mock requests
    with Django client.
    """
    # Override generator for files.
    gen.RequestGenerator.RANDOM_GENERATORS['.file'] = generate_file

    def __init__(self, spec, instances, **meta):
        self.instances = instances
        super(DjangoRequestGenerator, self).__init__(spec, **meta)

    def _common_constructor(self, field_type):
        @after(['.readonly'])
        def generate(context):
            if context.instance is self._SKIP:
                return None
            if field_type == '.ref':
                kwargs = dict(context.spec, **{'instances': self.instances})
                kwargs.update({'root_url': self.meta.get('root_url')})
                return generate_ref(**kwargs)
            return self.RANDOM_GENERATORS[field_type](**context.spec)
        return generate


def to_dict(keys):
    if not len(keys):
        return {}
    return {keys[0]: to_dict(keys[1:])}


class SpecGenerator(object):
    """
    Generates an APIMAS specification based on a list of django models.

    Generated specification has the following constraints:
        * All the model attributes being instances of `models.Field` are used
          to construct spec fields.
        * For related fields, `.ref` predicate is used instead of `.struct`.
        * Actions are randomly selected from automated actions understood by
          the `DjangoAdapter`, i.e. `.list`, `.retrieve`, `.create`,
          `.update`, `.delete`.
        * Only one endpoint is constructed.

    Args:
        endpoint (str): (optional) The name of endpoint. If `None` a random
            name is generated.

    Example:
        >>> from django.db import models
        >>> from apimas.django.generators import SpecGenerator
        >>> class MyModel(models.Model):
        ...     foo = models.CharField(max_length=255)
        ...     bar = models.IntegerField()
        >>> gen = SpecGenerator(endpoint='foo')
        >>> gen.generate(test_models=['myapp.mymodule.MyModel'])
        ... {
        ...     '.endpoint': {},
        ...     'foo': {
        ...         'mymodel_collection': {
        ...             '*': {
        ...                 '.actions=': {
        ...                     '.retrieve': {},
        ...                     '.update': {},
        ...                     '.delete': {}
        ...                 },
        ...                 'bar': {
        ...                     '.integer': {}
        ...                 },
        ...                 'foo': {
        ...                     '.string': {}
        ...                 },
        ...                 'id': {
        ...                     '.readonly': {},
        ...                     '.serial': {}
        ...                 }
        ...             },
        ...             '.actions=': {
        ...                 '.create': {},
        ...                 '.list': {}
        ...             },
        ...             '.collection': {'model': 'myapp.mymodule.MyModel'}
        ...         }
        ...     }
        ... }
    """

    MODEL_FIELD_TYPES = {
        models.AutoField: '.serial',
        models.TextField: '.string',
        models.CharField: '.string',
        models.EmailField: '.email',
        models.IntegerField: '.integer',
        models.BigIntegerField: '.integer',
        models.FloatField: '.float',
        models.DateTimeField: '.datetime',
        models.DateField: '.date',
        models.BooleanField: '.boolean',
        models.FileField: '.file',
        models.ForeignKey: '.ref',
        models.OneToOneField: '.ref',
        models.ManyToManyField: '.array of=/.ref',
    }

    RESOURCE_ACTIONS = {
        '.retrieve',
        '.update',
        '.delete',
    }

    COLLECTION_ACTIONS = {
        '.create',
        '.list',
    }

    def __init__(self, endpoint=None):
        self.endpoint = endpoint or gen.generate_random_string(
            max_length=10)

    def generate(self, django_models):
        """
        Generates a random spec given the the django models given as
        parameter.
        """
        if not isinstance(django_models, (list, tuple)):
            msg = ('A list|tuple with the module path of django models is'
                   ' expected. {!s} found.')
            raise InvalidInput(msg.format(str(type(django_models))))
        spec = {self.endpoint: {}, '.endpoint': {}}
        for model in django_models:
            model_cls = import_object(model)
            collection_name = model_cls.__name__.lower() + '_collection'
            model_fields = filter(lambda x: isinstance(x, models.Field),
                                  model_cls._meta.get_fields())
            field_schema = self._generate_field_spec(model_fields)
            collection_spec = {
                '.collection': {'model': model},
                '*': field_schema,
                '.actions=': self._get_actions(isresource=False),
            }
            spec[self.endpoint][collection_name] = collection_spec
        return spec

    def _ref(self, model_field):
        ref = model_field.related_model.__name__.lower() + '_collection'
        return {'to': self.endpoint + '/' + ref}

    def _struct(self, model_field):
        ref_model = model_field.related_model
        model_fields = filter((lambda x: isinstance(x, models.Field)),
                              ref_model._meta.get_fields())
        field_schema = self._generate_field_spec(
            model_fields, iscollection=False)
        return field_schema

    def _get_properties(self, field_type):
        if field_type in ['.serial', '.struct=', '.identity']:
            return {'.readonly': {}}
        return {}

    def _get_actions(self, isresource):
        actions = self.COLLECTION_ACTIONS if not isresource\
                else self.RESOURCE_ACTIONS
        nactions = gen.generate_integer(upper=len(actions), lower=1)
        selected = random.sample(actions, nactions)
        return {k: {} for k in selected}

    def _generate_field_spec(self, model_fields, isfield=False):
        extra = {
            '.ref': self._ref,
            '.struct=': self._struct
        }
        spec = {}
        for model_field in model_fields:
            predicate_type = self.MODEL_FIELD_TYPES[type(model_field)]
            if isinstance(predicate_type, list):
                predicate_type = random.choice(predicate_type)
            path = predicate_type.split('/')
            node = to_dict(path)
            # The last element of path denotes the predicate type of
            # the field.
            if path[-1] in extra:
                kwargs = extra[path[-1]](model_field)
                doc.doc_set(node, path, kwargs, multival=False)
            node.update(self._get_properties(path[-1]))
            spec[model_field.name] = node
        if not isfield:
            # If we construct the field schema of a resource then
            # we add some actions.
            spec['.actions='] = self._get_actions(isresource=True)
        return spec
