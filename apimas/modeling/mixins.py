"""
Basic building blocks for generic class based views.

We don't bind behaviour to http method handlers yet,
which allows mixin classes to be composed in interesting ways.
"""
from __future__ import unicode_literals

from rest_framework import mixins
from rest_framework import status
from rest_framework.response import Response


class CreateModelMixin(mixins.CreateModelMixin):
    """
    Create a model instance.
    """
    def create(self, request, *args, **kwargs):
        hook = self.get_hook(request_data=request.data)
        hook.on_pre_create()
        serializer = self.get_serializer(data=hook.request_data)
        serializer.is_valid(raise_exception=True)
        serializer.save(**hook.extra_data)
        hook.on_post_create(serializer.instance, serializer.data)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED,
                        headers=headers)


class ListModelMixin(object):
    """
    List a queryset.
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        hook = self.get_hook()
        hook.on_pre_list()
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            hook.on_post_list(serializer.data)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        hook.on_post_list(serializer.data)
        return Response(serializer.data)


class RetrieveModelMixin(object):
    """
    Retrieve a model instance.
    """
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        hook = self.get_hook(instance=instance)
        hook.on_pre_retrieve()
        serializer = self.get_serializer(hook.instance)
        hook.on_post_retrieve(serializer.data)
        return Response(serializer.data)


class UpdateModelMixin(object):
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        hook = self.get_hook(instance=instance, request_data=request.data)
        hook.on_pre_update()
        serializer = self.get_serializer(
            hook.instance, data=hook.request_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(**hook.extra_data)
        hook.on_post_update(serializer.instance, serializer.data)
        return Response(hook.data)


class DestroyModelMixin(object):
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        hook = self.get_hook(instance=instance)
        hook.pre_delete()
        self.perform_destroy(hook.instance)
        hook.post_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
