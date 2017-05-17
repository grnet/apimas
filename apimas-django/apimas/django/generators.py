import random
from urlparse import urljoin
from django.core.files.uploadedfile import SimpleUploadedFile
from apimas.utils import generators as gen
from apimas.decorators import after


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
    mock_file = gen.generate_fake_file(size=size, file_name=file_name,
                                       archived=archived)
    uploaded = SimpleUploadedFile(
        file_name, mock_file.getvalue(), content_type=gen.fake.mime_type())
    mock_file.close()
    return uploaded


def generate_ref(to, instances=None):
    """
    Generates a ref URL based on the given endpoint which points to one of
    the existing model instances.

    Args:
        to (str): Collection path from which URL is constructed, e.g. api/foo.
        instances (dict): A dictionary of lists which containts the existing
            model instances per collection path.

    Returns:
        URL pointing to a specific instance of a collection, e.g. api/foo/1/.
    """
    instances = instances or {}
    ref_instances = instances.get(to)
    random_instance = random.choice(ref_instances)
    if random_instance is None:
        return None
    ref = to.strip('/') + '/'
    return urljoin(ref, str(random_instance.pk) + '/')


class DjangoRequestGenerator(gen.RequestGenerator):
    """
    A generator used to create random data in order to make mock requests
    with Django client.
    """
    # Override generator for files.
    gen.RequestGenerator.RANDOM_GENERATORS['.file'] = generate_file

    def __init__(self, spec, instances):
        self.instances = instances
        super(DjangoRequestGenerator, self).__init__(spec)

    def _common_constructor(self, field_type):
        @after(['.readonly'])
        def generate(instance, loc, spec, context):
            if instance is self._SKIP:
                return None
            if field_type == '.ref':
                return generate_ref(
                    **dict(spec, **{'instances': self.instances}))
            return self.RANDOM_GENERATORS[field_type](**spec)
        return generate
