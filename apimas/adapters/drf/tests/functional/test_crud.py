from apimas.adapters.drf.testing import (
    apimas_context, ApimasTestCase)
from apimas.adapters.drf.tests.utils import SpecGenerator


TEST_MODELS = [
    'apimas.adapters.drf.tests.models.MyModel',
    'apimas.adapters.drf.tests.models.ModelFile',
    'apimas.adapters.drf.tests.models.RefModel',
    'apimas.adapters.drf.tests.models.ManyToManyModel',
    'apimas.adapters.drf.tests.models.RefRefModel',
    'apimas.adapters.drf.tests.models.OneToOneModel',
]


generator = SpecGenerator()
SPEC = generator.generate(TEST_MODELS)


@apimas_context(__name__, SPEC)
class TestCRUDOperations(ApimasTestCase):
    pass
