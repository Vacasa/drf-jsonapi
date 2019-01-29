from django.conf import settings

from rest_framework.exceptions import NotFound, MethodNotAllowed
from rest_framework import status

from . import defaults
from .response import Response
from .serializers.utils import resource_identifier
from .utils import listify
from .objects import Error


class ListMixin:
    """
    Override base view behavior: build a response for a list endpoint
    """

    def list(self, request):
        collection = self.get_collection(request)

        # Sorting
        collection = self.serializer_class.sort(request.GET.get("sort"), collection)

        # Filtering
        if self.filter_class:
            filterset = self.filter_class(request.GET, collection)
            collection = filterset.collection

        # Paging
        page = self.apply_pagination(collection)

        serializer = self.serializer_class(
            page,
            many=True,
            only_fields=request.fields,
            include=request.include,
            page_size=request.GET.get(
                "page[size]",
                getattr(settings, "DEFAULT_PAGE_SIZE", defaults.DEFAULT_PAGE_SIZE),
            ),
            context={"request": request},
        )

        self.document.instance.data = serializer.data
        self.document.instance.included = serializer.included

        return Response(self.document.data)


class ProcessRelationshipsMixin:
    def process_relationships(self, relationship_data, resource, request, many=None):
        for relation, data in relationship_data.items():
            handler = self.get_relationship_handler(relation)

            # Skip relationships that don't match many
            if many != handler.many and many is not None:
                continue

            if handler.read_only:
                raise Error(
                    detail="{} is a read-only relationship".format(relation),
                    source={"pointer": "data/relationships/{}".format(relation)},
                )
            data = handler.validate(data["data"])
            related_resources = handler.serializer_class.from_identity(
                data, many=handler.many
            )

            handler.set_related(resource, related_resources, request)

        return resource


class CreateMixin(ProcessRelationshipsMixin):
    """
    Override base view behavior for a create endpoint
    """

    def create(self, request):
        serializer = self.serializer_class(
            data=request.data["data"],
            only_fields=request.fields,
            include=request.include,
            page_size=request.GET.get(
                "page[size]",
                getattr(settings, "DEFAULT_PAGE_SIZE", defaults.DEFAULT_PAGE_SIZE),
            ),
            context={"request": request},
        )

        if not serializer.is_valid():
            return self.error_response(Error.parse_validation_errors(serializer.errors))

        resource = serializer.Meta.model(**serializer.validated_data)

        # Check for relationships and process them
        if "relationships" in request.data["data"]:
            resource = self.process_relationships(
                request.data["data"]["relationships"], resource, request, many=False
            )
            resource.save()
            resource = self.process_relationships(
                request.data["data"]["relationships"], resource, request, many=True
            )
        else:
            resource.save()

        serializer.instance = resource
        self.document.instance.data = serializer.data

        return Response(self.document.data, status=status.HTTP_201_CREATED)


class RetrieveMixin:
    """
    Override base view behavior for retrieve endpoints
    """

    def retrieve(self, request, pk):
        resource = self.get_resource(request, pk)

        serializer = self.serializer_class(
            resource,
            only_fields=request.fields,
            include=request.include,
            page_size=request.GET.get(
                "page[size]",
                getattr(settings, "DEFAULT_PAGE_SIZE", defaults.DEFAULT_PAGE_SIZE),
            ),
            context={"request": request},
        )

        self.document.instance.data = serializer.data
        self.document.instance.included = serializer.included

        return Response(self.document.data)


class PartialUpdateMixin(ProcessRelationshipsMixin):
    """
    Override base view behavior for partial update endpoints
    """

    def partial_update(self, request, *args, **kwargs):
        resource = self.get_resource(request, *args, **kwargs)

        serializer = self.serializer_class(
            resource,
            data=request.data["data"],
            only_fields=request.fields,
            partial=True,
            include=request.include,
            page_size=request.GET.get(
                "page[size]",
                getattr(settings, "DEFAULT_PAGE_SIZE", defaults.DEFAULT_PAGE_SIZE),
            ),
            context={"request": request},
        )

        if not serializer.is_valid():
            return self.error_response(Error.parse_validation_errors(serializer.errors))

        resource = serializer.save()

        # Check for relationships and process them
        if "relationships" in request.data["data"]:
            self.process_relationships(
                request.data["data"]["relationships"], resource, request
            )

        resource.save()

        self.document.instance.data = serializer.data

        return Response(self.document.data)


class DestroyMixin:
    """
    Override base view behavior for delete endpoints
    """

    def destroy(self, request, pk):
        resource = self.get_resource(request, pk)
        resource.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class RelationshipRetrieveMixin:
    """
    Override base view behavior for relationship list endpoints
    """

    def relationship_retrieve(self, request, pk, relationship):
        resource = self.get_resource(request, pk)

        # get the relationship handler
        handler = self.get_relationship_handler(relationship)
        serializer_class = handler.serializer_class
        related = handler.get_related(resource, request)

        if not related:
            self.document.instance.data = [] if handler.many else None
            return Response(self.document.data)

        if handler.many:
            related = serializer_class.sort(request.GET.get("sort"), related)
            related = self.apply_pagination(related)

        serializer = resource_identifier(serializer_class)(related, many=handler.many)

        self.document.instance.data = serializer.data
        return Response(self.document.data)


class RelationshipCreateMixin:
    """
    Override base view behavior for relationship get endpoints
    """

    def relationship_create(self, request, pk, relationship):
        # get the relationship handler
        handler = self.get_relationship_handler(self.relationship)
        serializer_class = handler.serializer_class

        if not handler.many:
            # to-one relationships do not have a detail route
            raise MethodNotAllowed("POST")

        resource = self.get_resource(request, pk)
        data = request.data["data"]

        # data could be a single Resource Identifier or an array of Resource
        # Identifiers. Let's convert single items to a single-item list.
        if isinstance(data, dict):
            data = listify(data)
        data = handler.validate(data)

        related = serializer_class.from_identity(data, many=handler.many)

        handler.add_related(resource, related, request)

        return Response(status=status.HTTP_204_NO_CONTENT)


class RelationshipUpdateMixin:
    """
    Override base view behavior for relationship patch endpoints
    """

    def relationship_update(self, request, pk, relationship):
        resource = self.get_resource(request, pk)

        # get the relationship handler
        handler = self.get_relationship_handler(self.relationship)
        serializer_class = handler.serializer_class

        data = request.data["data"]
        data = handler.validate(data)

        related = serializer_class.from_identity(
            request.data["data"], many=handler.many
        )

        handler.set_related(resource, related, request)

        return Response(status=status.HTTP_204_NO_CONTENT)


class RelationshipDestroyMixin:
    """
    Override base view behavior for relationship delete endpoints
    """

    def relationship_destroy(self, request, pk, relationship):
        # get the relationship handler
        handler = self.get_relationship_handler(self.relationship)
        serializer_class = handler.serializer_class

        if not handler.many:
            # to-one relationships do not support DELETE
            raise NotFound()

        resource = self.get_resource(request, pk)
        data = request.data["data"]

        # data could be a single Resource Identifier or an array of Resource
        # Identifiers. Let's convert single items to a single-item list.
        if isinstance(data, dict):
            data = listify(data)
        data = handler.validate(data)

        related = serializer_class.from_identity(data, many=handler.many)

        handler.remove_related(resource, related, request)

        return Response(status=status.HTTP_204_NO_CONTENT)
