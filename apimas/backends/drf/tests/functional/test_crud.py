from apimas.backends.drf.testing import (
    apimas_context, ApimasTestCase)
from apimas.backends.drf.tests.utils import SpecGenerator


TEST_MODELS = [
    'apimas.backends.drf.tests.models.MyModel',
    'apimas.backends.drf.tests.models.ModelFile',
    'apimas.backends.drf.tests.models.RefModel',
    'apimas.backends.drf.tests.models.ManyToManyModel',
    'apimas.backends.drf.tests.models.RefRefModel',
    'apimas.backends.drf.tests.models.OneToOneModel',
]


generator = SpecGenerator()
SPEC = generator.generate(TEST_MODELS)


@apimas_context(__name__, SPEC)
class TestCRUDOperations(ApimasTestCase):
    pass
