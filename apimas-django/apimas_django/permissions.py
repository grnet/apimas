from django.db import models
from django.db.models.query import QuerySet
from apimas_django.handlers import \
    get_model_instance, _django_base_construction
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas.errors import NotFound
import docular


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
        'unfiltered': 'backend/raw_response',
        'kwargs': 'request/meta/kwargs',
        'read_filter': 'permissions/read/filter',
    }

    WRITE_KEYS = (
        'backend/filtered_response',
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
            filtered_response = unfiltered_response
        else:
            assert isinstance(unfiltered_response, models.Model)
            pk = unfiltered_response.pk
            filtered_response = filter_resource(
                self.spec, pk, kwargs, read_filter, context, self.strict)

        self.write((filtered_response,), context)


FilterResourceResponse = _django_base_construction(
    FilterResourceResponseProcessor)


class ObjectRetrievalForUpdateProcessor(BaseProcessor):
    READ_KEYS = {
        'kwargs': 'request/meta/kwargs',
        'pk': 'request/meta/kwargs/pk',
        'write_filter': 'permissions/write/filter',
    }

    WRITE_KEYS = (
        'backend/instance',
    )

    def __init__(self, collection_loc, action_name, spec):
        self.spec = spec

    def process(self, context):
        context_data = self.read(context)
        pk = context_data['pk']
        kwargs = context_data['kwargs']
        write_filter = context_data['write_filter']
        filters = []
        if write_filter is not None:
            filters.append(write_filter(context))

        instance = get_model_instance(self.spec, pk, kwargs, filters,
                                      for_update=True)
        self.write((instance,), context)


ObjectRetrievalForUpdate = _django_base_construction(
    ObjectRetrievalForUpdateProcessor)


class FilterCollectionResponseProcessor(BaseProcessor):
    READ_KEYS = {
        'unfiltered': 'backend/raw_response',
        'read_filter': 'permissions/read/filter',
    }

    WRITE_KEYS = (
        'backend/filtered_response',
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
            filtered_response = unfiltered_response
        else:
            assert isinstance(unfiltered_response, QuerySet)
            filtered_response = filter_collection(
                unfiltered_response, read_filter, context)

        self.write((filtered_response,), context)


FilterCollectionResponse = _django_base_construction(
    FilterCollectionResponseProcessor)


class WritePermissionCheckProcessor(BaseProcessor):
    READ_KEYS = {
        'input': 'backend/input',
        'instance': 'backend/instance',
        'write_check': 'permissions/write/check',
    }

    def process(self, context):
        context_data = self.read(context)
        backend_input = context_data['input']
        instance = context_data['instance']
        write_check = context_data['write_check']

        if write_check is None:
            return

        write_check(backend_input, instance, context)


def no_constructor(instance):
    pass


NO_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    {}, default=no_constructor)


WritePermissionCheck = ProcessorConstruction(
    NO_CONSTRUCTORS, WritePermissionCheckProcessor)


class ReadPermissionCheckProcessor(BaseProcessor):
    READ_KEYS = {
        'unchecked': 'backend/filtered_response',
        'read_check': 'permissions/read/check',
    }

    WRITE_KEYS = (
        'backend/checked_response',
    )

    def __init__(self, collection_loc, action_name, read_check_strict):
        self.collection_loc = collection_loc
        self.action_name = action_name
        self.strict = bool(read_check_strict)

    def process(self, context):
        context_data = self.read(context)
        unchecked_response = context_data['unchecked']
        read_check = context_data['read_check']

        if read_check is None or unchecked_response is None:
            checked_response = unchecked_response
            self.write((checked_response,), context)
            return

        checked_response = read_check(unchecked_response, context)
        if checked_response is None and self.strict:
            raise NotFound("Resource not found")

        self.write((checked_response,), context)


ReadPermissionCheck = ProcessorConstruction(
    NO_CONSTRUCTORS, ReadPermissionCheckProcessor)
