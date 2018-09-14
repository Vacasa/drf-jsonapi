from django.conf import settings

from rest_framework.exceptions import NotFound, MethodNotAllowed, ParseError
from rest_framework.decorators import list_route
from rest_framework import status

from .response import Response
from .serializers.utils import resource_identifier
from .utils import listify
from .objects import Error


class ListMixin(object):
    """
    Override base view behavior: build a response for a list endpoint
    """

    def list(self, request, *args, **kwargs):
        """
        Create a response for a list, including sorting, filtering, and paging

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        collection = kwargs.pop('collection', None)
        if collection is None:
            collection = self.get_collection(request, *args, **kwargs)

        # Sorting
        collection = self.serializer_class.sort(request.GET.get('sort'), collection)

        # Filtering
        if self.filter_class:
            filter = self.filter_class(request.GET, collection)
            collection = filter.collection

        # Paging
        page = self.apply_pagination(collection)

        serializer = self.serializer_class(
            page,
            many=True,
            only_fields=request.fields,
            include=request.include,
            page_size=self.request.GET.get('page[size]', settings.DEFAULT_PAGE_SIZE)
        )

        self.document.instance.data = serializer.data
        self.document.instance.included = serializer.included

        return Response(self.document.data)


class ProcessRelationshipsMixin(object):

    def process_to_one_relationships(self, relationship_data, resource):
        """
        Validate and populate related To-One relationship resources

        :param viewset self: This object
        :param dict relationship_data: A dictionary of relationships
        :param resource:
        """

        to_one_relationship_data = {}

        for relation, data in relationship_data.items():

            handler = self.get_relationship_handler(relation)
            if not handler.many:
                to_one_relationship_data[relation] = data

        if to_one_relationship_data:
            resource = self.process_relationships(to_one_relationship_data, resource)

        return(resource)

    def process_to_many_relationships(self, relationship_data, resource):
        """
        Validate and populate related To-Many relationship resources

        :param viewset self: This object
        :param dict relationship_data: A dictionary of relationships
        :param resource:
        """

        to_one_relationship_data = {}

        for relation, data in relationship_data.items():

            handler = self.get_relationship_handler(relation)
            if handler.many:
                to_one_relationship_data[relation] = data

        if to_one_relationship_data:
            resource = self.process_relationships(to_one_relationship_data, resource)

        return(resource)

    def process_relationships(self, relationship_data, resource):
        """
        Validate and populate related resources

        :param viewset self: This object
        :param dict relationship_data: A dictionary of relationships
        :param resource:
        """

        for relation, data in relationship_data.items():

            handler = self.get_relationship_handler(relation)

            data = handler.validate(data['data'])
            related_resources = handler.get_serializer_class().from_identity(
                data, many=handler.many
            )

            handler.set_related(resource, related_resources)

        return(resource)


class CreateMixin(ProcessRelationshipsMixin):
    """
    Override base view behavior for a create endpoint
    """

    def create(self, request):
        """
        Build a response for a create endpoint

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        serializer = self.serializer_class(
            data=request.data['data'],
            only_fields=request.fields,
            include=request.include,
            page_size=self.request.GET.get('page[size]', settings.DEFAULT_PAGE_SIZE)
        )

        if not serializer.is_valid():
            return self.error_response(
                Error.parse_validation_errors(serializer.errors)
            )

        resource = serializer.Meta.model(**serializer.validated_data)

        # Check for relationships and process them
        if 'relationships' in request.data['data']:
            resource = self.process_to_one_relationships(request.data['data']['relationships'], resource)

        resource.save()

        if 'relationships' in request.data['data']:
            resource = self.process_to_many_relationships(request.data['data']['relationships'], resource)

        serializer.instance = resource
        self.document.instance.data = serializer.data

        return Response(self.document.data)


class RetrieveMixin(object):
    """
    Override base view behavior for retrieve endpoints
    """

    def retrieve(self, request, *args, **kwargs):
        """
        Build a response for a retrieve endpoint

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        resource = kwargs.pop('resource', self.get_resource(request, *args, **kwargs))

        serializer = self.serializer_class(
            resource,
            only_fields=request.fields,
            include=request.include,
            page_size=self.request.GET.get('page[size]', settings.DEFAULT_PAGE_SIZE)
        )

        self.document.instance.data = serializer.data
        self.document.instance.included = serializer.included

        return Response(self.document.data)


class PartialUpdateMixin(ProcessRelationshipsMixin):
    """
    Override base view behavior for partial update endpoints
    """

    def partial_update(self, request, *args, **kwargs):
        """
        Build a response for a partial update endpoint

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        resource = kwargs.pop('resource', self.get_resource(request, *args, **kwargs))

        serializer = self.serializer_class(
            resource,
            data=request.data['data'],
            only_fields=request.fields,
            partial=True,
            include=request.include,
            page_size=self.request.GET.get('page[size]', settings.DEFAULT_PAGE_SIZE)
        )

        if not serializer.is_valid():
            return self.error_response(
                Error.parse_validation_errors(serializer.errors)
            )

        resource = serializer.save()

        # Check for relationships and process them
        if 'relationships' in request.data['data']:
            self.process_relationships(request.data['data']['relationships'], resource)

        resource.save()

        self.document.instance.data = serializer.data

        return Response(self.document.data)


class DestroyMixin(object):
    """
    Override base view behavior for delete endpoints
    """

    def destroy(self, request, *args, **kwargs):
        """
        Build a response for a delete endpoint

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        resource = kwargs.pop('resource', self.get_resource(request, *args, **kwargs))
        resource.delete()

        return Response(status=204)


class RelationshipListMixin(object):
    """
    Override base view behavior for relationship list endpoints
    """

    def list(self, request, *args, **kwargs):
        """
        Build a response for a relationship list endpoint

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        resource = kwargs.pop('resource', self.get_resource(request, *args, **kwargs))

        # get the relationship handler
        handler = self.get_relationship_handler(self.relationship)
        serializer_class = handler.get_serializer_class()

        related = kwargs.pop('related', None)
        if related is None:
            related = handler.get_related(resource)

        if related:
            # Sorting
            if handler.many:
                related = self.serializer_class.sort(request.GET.get('sort'), related)
                related = self.apply_pagination(related)

            serializer = resource_identifier(serializer_class)(
                related,
                many=handler.many
            )

            self.document.instance.data = serializer.data
        else:
            self.document.instance.data = [] if handler.many else None

        return Response(self.document.data)


class RelationshipCreateMixin(object):
    """
    Override base view behavior for relationship get endpoints
    """

    def create(self, request, *args, **kwargs):
        """
        Build a response for a relationship create endpoint

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        # get the relationship handler
        handler = self.get_relationship_handler(self.relationship)
        serializer_class = handler.get_serializer_class()

        if not handler.many:
            # to-one relationships do not have a detail route
            raise MethodNotAllowed('POST')

        resource = kwargs.pop('resource', self.get_resource(request, *args, **kwargs))
        data = request.data['data']

        # data could be a single Resource Identifier or an array of Resource
        # Identifiers. Let's convert single items to a single-item list.
        if isinstance(data, dict):
            data = listify(data)
        data = handler.validate(data)

        related = serializer_class.from_identity(
            data,
            many=handler.many
        )

        handler.add_related(resource, related)

        return Response(status=status.HTTP_204_NO_CONTENT)


class RelationshipPatchMixin(object):
    """
    Override base view behavior for relationship patch endpoints
    """

    def patch(self, request, *args, **kwargs):
        """
        Build a response for a relationship patch endpoint

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        resource = kwargs.pop('resource', self.get_resource(request, *args, **kwargs))

        # get the relationship handler
        handler = self.get_relationship_handler(self.relationship)
        serializer_class = handler.get_serializer_class()

        data = request.data['data']
        data = handler.validate(data)

        related = serializer_class.from_identity(
            request.data['data'],
            many=handler.many
        )

        handler.set_related(resource, related)
        resource.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class RelationshipDeleteMixin(object):
    """
    Override base view behavior for relationship delete endpoints
    """

    def delete(self, request, *args, **kwargs):
        """
        Build a response for a relationship delete endpoint

        :param viewset self: This object
        :param rest_framework.request.Request request: A request object
        :return: A json response
        :rtype: Response
        """

        # get the relationship handler
        handler = self.get_relationship_handler(self.relationship)
        serializer_class = handler.get_serializer_class()

        if not handler.many:
            # to-one relationships do not support DELETE
            raise NotFound()

        resource = self.get_resource(request, *args, **kwargs)
        data = request.data['data']

        # data could be a single Resource Identifier or an array of Resource
        # Identifiers. Let's convert single items to a single-item list.
        if isinstance(data, dict):
            data = listify(data)
        data = handler.validate(data)

        related = serializer_class.from_identity(
            data,
            many=handler.many
        )

        handler.remove_related(resource, related)

        return Response(status=status.HTTP_204_NO_CONTENT)
