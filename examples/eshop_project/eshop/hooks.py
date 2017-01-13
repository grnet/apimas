from apimas.modeling.adapters.drf import mixins
from eshop.models import Order


class CreateOrder(mixins.HookMixin):
    def preprocess_create(self):
        # Initial status
        self.stash(extra={'status': Order.RECEIVED})
