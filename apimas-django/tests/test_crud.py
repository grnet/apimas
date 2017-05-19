from django.conf import settings
from apimas.django.generators import SpecGenerator
from apimas.django.adapter import DjangoAdapter


TEST_MODELS = [
    'tests.models.MyModel',
    'tests.models.ModelFile',
    'tests.models.RefModel',
    'tests.models.ManyToManyModel',
    'tests.models.RefRefModel',
    'tests.models.OneToOneModel',
]


generator = SpecGenerator(endpoint='foo')
SPEC = generator.generate(TEST_MODELS)

# Override settings so that the ROOT_URLCONF is the current module.
settings.ROOT_URLCONF = __name__

adapter = DjangoAdapter()
adapter.construct(SPEC)
urlpatterns = adapter.get_urlpatterns()

TestAPI = adapter.get_testcase()
