from apimas.drf.testing import (
    apimas_context, ApimasTestCase)
from tests.utils import SpecGenerator


TEST_MODELS = [
    'tests.models.MyModel',
    'tests.models.ModelFile',
    'tests.models.RefModel',
    'tests.models.ManyToManyModel',
    'tests.models.RefRefModel',
    'tests.models.OneToOneModel',
]


generator = SpecGenerator()
SPEC = generator.generate(TEST_MODELS)


@apimas_context(__name__, SPEC)
class TestCRUDOperations(ApimasTestCase):
    pass
