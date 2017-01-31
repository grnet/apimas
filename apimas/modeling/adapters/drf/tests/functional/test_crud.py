from apimas.modeling.adapters.drf.testing import (
    apimas_context, ApimasTestCase)
from apimas.modeling.adapters.drf.tests.utils import SpecGenerator


TEST_MODELS = [
    'apimas.modeling.adapters.drf.tests.models.MyModel',
    'apimas.modeling.adapters.drf.tests.models.ModelFile',
    'apimas.modeling.adapters.drf.tests.models.RefModel',
    'apimas.modeling.adapters.drf.tests.models.ManyToManyModel',
    'apimas.modeling.adapters.drf.tests.models.RefRefModel',
    'apimas.modeling.adapters.drf.tests.models.OneToOneModel',
]


generator = SpecGenerator()
SPEC = generator.generate(TEST_MODELS)


@apimas_context(__name__, SPEC)
class TestCRUDOperations(ApimasTestCase):
    pass
