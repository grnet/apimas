"""
Basic building blocks for generic class based views.

We don't bind behaviour to http method handlers yet,
which allows mixin classes to be composed in interesting ways.
"""
from __future__ import unicode_literals

from collections import namedtuple
from rest_framework import mixins
from rest_framework import status
from rest_framework.response import Response

StashedObj = namedtuple(
    'StashedObj', ['instance', 'data', 'extra', 'response', 'validated_data'])


class HookMixin(object):
    """
    This class is intended to encaptulate the business logic of the
    API's resources.

    It provides hooks for the preparation of data before
    any CRUD operations, as well as the data's final processing after db
    commit of resource.
    """

    def mock(self):
        pass

    def preprocess(self, action):
        """
        A hook method being executed before any CRUD operation performed
        on a specific resource.
        """
        func = getattr(self, 'preprocess_' + action, self.mock)
        func()

    def wrap_response(self, action, response):
        self.stash(response=response)
        self.finalize(action)
        response = self.unstash().response
        return response

    def finalize(self, action):
        """
        A hook method being executed after any CRUD operation performed
        on a specific resource.
        """
        func = getattr(self, 'finalize_' + action, self.mock)
        func()

    def stash(self, instance=None, data=None, extra=None, response=None,
              validated_data=None):
        """
        Method to stash data for later use.

        :param instance: Model instance of the resource.
        :param data: Request data; data exposed to the API.
        :param extra: Extra data being used for the business logic of the
        resource.
        :param response: Response object of the corresponding endpoint.
        """
        if instance:
            self.request.parser_context['instance'] = instance
        if data:
            self.request.parser_context['data'] = data
        if extra:
            self.request.parser_context['extra'] = extra
        if response:
            self.request.parser_context['response'] = response
        if validated_data:
            self.request.parser_context['validated_data'] = validated_data

    def unstash(self):
        """
        Method to unstash data.

        :returns: A namedtuple object which contains all required
        information to proceed with the business logic of the resource.
        """
        instance = self.request.parser_context.get('instance', None)
        data = self.request.parser_context.get('data', self.request.data)
        extra = self.request.parser_context.get('extra', {})
        response = self.request.parser_context.get('response', None)
        validated_data = self.request.parser_context.get('validated_data',
                                                         None)
        return StashedObj(instance=instance, data=data, extra=extra,
                          response=response, validated_data=validated_data)


class CreateModelMixin(mixins.CreateModelMixin):
    """
    Create a model instance.
    """
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.stash(validated_data=serializer.validated_data)
        self.preprocess('create')
        unstashed = self.unstash()
        serializer.save(**unstashed.extra)
        self.stash(instance=serializer.instance)
        headers = self.get_success_headers(serializer.data)
        response = Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)
        return self.wrap_response('create', response)


class ListModelMixin(object):
    """
    List a queryset.
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data)
        return self.wrap_response('list', response)


class RetrieveModelMixin(object):
    """
    Retrieve a model instance.
    """
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self.stash(instance=instance)
        self.preprocess('retrieve')
        unstashed = self.unstash()
        serializer = self.get_serializer(unstashed.instance)
        response = Response(serializer.data)
        return self.wrap_response('retrieve', response)


class UpdateModelMixin(mixins.UpdateModelMixin):
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=self.request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.stash(instance=instance, validated_data=serializer.validated_data)
        self.preprocess('update')
        unstashed = self.unstash()
        serializer.save(**unstashed.extra)
        self.stash(instance=serializer.instance)
        response = Response(serializer.data)
        return self.wrap_response('update', response)


class DestroyModelMixin(mixins.DestroyModelMixin):
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.stash(instance=instance)
        self.preprocess('delete')
        unstashed = self.unstash()
        self.perform_destroy(unstashed.instance)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return self.wrap_response('delete', response)
