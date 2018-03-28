from django.db import models
from django.db.models.query import QuerySet
from apimas_django.handlers import \
    get_model_instance, _django_base_construction
from apimas.components import BaseProcessor
from apimas.errors import NotFound


def filter_collection(queryset, filter_func, context):
    flt = filter_func(context)
    return queryset.filter(flt)


def filter_resource(spec, pk, kwargs, filter_func, context, strict):
    flt = filter_func(context)
    try:
        return get_model_instance(spec, pk, kwargs, filters=[flt])
    except NotFound:
        if strict:
            raise
        return None


class FilterResourceResponseProcessor(BaseProcessor):
    READ_KEYS = {
        'unfiltered': 'backend/content',
        'kwargs': 'request/meta/kwargs',
        'read_filter': 'permissions/read/filter',
    }

    WRITE_KEYS = (
        'backend/content',
    )

    def __init__(self, collection_loc, action_name, spec,
                 filter_resource_strict):
        self.collection_loc = collection_loc
        self.collection_name = collection_loc[-1]
        self.spec = spec
        self.strict = bool(filter_resource_strict)

    def process(self, context):
        context_data = self.read(context)
        unfiltered_response = context_data['unfiltered']
        kwargs = context_data['kwargs']
        read_filter = context_data['read_filter']

        if read_filter is None:
            return

        assert isinstance(unfiltered_response, models.Model)
        pk = unfiltered_response.pk
        filtered_response = filter_resource(
            self.spec, pk, kwargs, read_filter, context, self.strict)
        self.write((filtered_response,), context)


FilterResourceResponse = _django_base_construction(
    FilterResourceResponseProcessor)


class FilterCollectionResponseProcessor(BaseProcessor):
    READ_KEYS = {
        'unfiltered': 'backend/content',
        'read_filter': 'permissions/read/filter',
    }

    WRITE_KEYS = (
        'backend/content',
    )

    def __init__(self, collection_loc, action_name, spec):
        self.collection_loc = collection_loc
        self.collection_name = collection_loc[-1]
        self.spec = spec

    def process(self, context):
        context_data = self.read(context)
        unfiltered_response = context_data['unfiltered']
        read_filter = context_data['read_filter']

        if read_filter is None:
            return

        assert isinstance(unfiltered_response, QuerySet)
        filtered_response = filter_collection(
            unfiltered_response, read_filter, context)
        self.write((filtered_response,), context)


FilterCollectionResponse = _django_base_construction(
    FilterCollectionResponseProcessor)