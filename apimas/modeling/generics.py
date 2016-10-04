from rest_framework.generics import GenericAPIView
from apimas.modeling.hooks import BaseHook


class APIMASGenericView(GenericAPIView):

    def get_hook(self, *args, **kwargs):
        hook_class = getattr(self, 'hook_class', BaseHook)
        return hook_class(**kwargs)
