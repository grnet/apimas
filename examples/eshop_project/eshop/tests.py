from django.contrib.auth.models import Group
from apimas.modeling.adapters.drf.testing import (
    ApimasTestCase, apimas_context)
from eshop.api_spec import API_SPEC
from eshop.models import UserProfile


@apimas_context(__name__, API_SPEC)
class TestApplication(ApimasTestCase):
    def authenticate(self):
        user = UserProfile.objects.create(username='fdsfa', first_name='fdadaf',
                                          last_name='fdsfd', password='fdafda',
                                          email='test@example.com')
        group = Group.objects.create(name='group name')
        user.groups.add(group)
        self.client.force_authenticate(user=user)

    def authenticate_api_orders(self, collection):
        self.authenticate()

    def authenticate_api_carts(self, collection):
        self.authenticate()
