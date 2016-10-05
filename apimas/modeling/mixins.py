"""
Basic building blocks for generic class based views.

We don't bind behaviour to http method handlers yet,
which allows mixin classes to be composed in interesting ways.
"""
from __future__ import unicode_literals

from rest_framework import mixins
from rest_framework import status
from rest_framework.response import Response


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
        func = getattr(self, 'preprocess_' + action, self.mock)
        func()

    def wrap_response(self, action, response):
        self.stash(response=response)
        self.finalize(action)
        _, _, _, response = self.unstash()
        return response

    def finalize(self, action):
        func = getattr(self, 'finalize_' + action, self.mock)
        func()

    def stash(self, instance=None, data=None, extra=None, response=None):
        if instance:
            self.request.parser_context['instance'] = instance
        if data:
            self.request.parser_context['data'] = data
        if extra:
            self.request.parser_context['extra'] = extra
        if response:
            self.request.parser_context['response'] = response

    def unstash(self):
        return (self.request.parser_context.get('instance', None),
                self.request.parser_context.get('data', self.request.data),
                self.request.parser_context.get('extra', {}),
                self.request.parser_context.get('response', None))


class CreateModelMixin(mixins.CreateModelMixin):
    """
    Create a model instance.
    """
    def create(self, request, *args, **kwargs):
        self.preprocess('create')
        _, data, extra_data, _ = self.unstash()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(**extra_data)
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
        instance, _, _, _ = self.unstash()
        serializer = self.get_serializer(instance)
        response = Response(serializer.data)
        return self.wrap_response('retrieve', response)


class UpdateModelMixin(mixins.UpdateModelMixin):
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.stash(instance=instance)
        self.preprocess('update')
        instance, data, extra_data, _ = self.unstash()
        serializer = self.get_serializer(
            instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(**extra_data)
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
        instance, _, _, _ = self.unstash()
        self.perform_destroy(instance)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return self.wrap_response('delete', response)
