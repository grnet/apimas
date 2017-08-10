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

# Permission rules: Free for all for testing reasons.
def _get_rules():
    return [
        ('*', '*', '*', '*', '*')
    ]


generator = SpecGenerator(endpoint='foo')
SPEC = generator.generate(TEST_MODELS)
# Add permission rules
SPEC.update(
    {
        '.meta': {
            'get_rules': 'tests.test_crud._get_rules'
        }
    }
)

# Override settings so that the ROOT_URLCONF is the current module.
settings.ROOT_URLCONF = __name__

adapter = DjangoAdapter()
adapter.construct(SPEC)
urlpatterns = adapter.get_urlpatterns()

patterns = {
    '*/*/*': {},
}
TestAPI = adapter.get_testcase(patterns=patterns)
