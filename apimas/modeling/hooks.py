class BaseHook(object):
    """
    This class is intended to encaptulate the business logic of the
    API's resources.

    It provides hooks for the preparation of data before
    any CRUD operations, as well as the data's final processing after db
    commit of resource.
    """
    def __init__(self, instance=None, request_data=None, **kwargs):
        self.instance = instance
        self.request_data = request_data
        self.initial_data = request_data
        self.extra_data = {}

    def on_pre_list(self):
        pass

    def on_post_list(self, data):
        pass

    def on_pre_retrieve(self):
        pass

    def on_post_retrieve(self, data, *args, **kwargs):
        pass

    def on_pre_create(self):
        pass

    def on_post_create(self, instance, data):
        pass

    def on_pre_update(self):
        pass

    def on_post_update(self, instance, data):
        pass

    def on_pre_delete(self):
        pass

    def on_post_delete(self):
        pass
