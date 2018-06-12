from pydoc import locate
from collections import OrderedDict

from rest_framework import serializers
from rest_framework.exceptions import ParseError

from ..utils import listify
from ..objects import Error


class DocumentSerializer(serializers.Serializer):
    """
    A Django Rest Framework Serializer that represents the root document object
    of a JSON API response.

    This is just a simple pass-through for now but could be extended
    in the future.
    """

    def to_representation(self, instance):
        """
        Create an ordered dictionary from a top-level JSON-API object,
        removing data node if errors exist.

        :param jsonapi.serializers.objects.DocumentSerializer self: This object instance
        :param jsonapi.objects.Document instance: An object containing top-level JSON-API nodes
        :return: An ordered dictionary created from instance data
        :rtype: collections.OrderedDict
        """

        data = OrderedDict()
        data['data'] = instance.data

        if instance.errors:
            # If errors exist we need to get rid of `data` key
            # See: http://jsonapi.org/format/#document-top-level
            del(data['data'])
            data['errors'] = instance.errors
        if instance.jsonapi:
            data['jsonapi'] = instance.jsonapi
        if instance.links:
            data['links'] = instance.links
        if instance.included:
            data['included'] = instance.included
        if instance.meta:
            data['meta'] = instance.meta

        return data


class ErrorSerializer(serializers.Serializer):
    """
    A simple serializer for Errors

    This is just a simple pass-through for now but could be extended
    in the future.
    """

    def to_representation(self, instance):
        """
        Create an ordered dictionary from a JSON-API error object.

        :param jsonapi.serializers.objects.ErrorSerializer self: This object instance
        :param jsonapi.objects.Document instance: An object containing JSON-API error nodes
        :return: An ordered dictionary created from the instance data
        :rtype: OrderedDict
        """

        data = OrderedDict()

        if instance.id:
            data['id'] = instance.id
        if instance.links:
            data['links'] = instance.links
        if instance.status_code:
            # status should be a string
            # See: http://jsonapi.org/format/#error-objects
            data['status'] = str(instance.status_code)
        if instance.code:
            data['code'] = instance.code
        if instance.title:
            data['title'] = instance.title
        if instance.detail:
            data['detail'] = instance.detail
        if instance.source:
            data['source'] = instance.source
        if instance.meta:
            data['meta'] = instance.meta

        return data
