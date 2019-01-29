import re
from collections import defaultdict

from django.conf import settings
from django.db.models.query import QuerySet
from django.core.paginator import Paginator

from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ParseError
from rest_framework.generics import get_object_or_404

from . import defaults
from .response import Response
from .objects import Document
from .serializers import DocumentSerializer, ErrorSerializer, resource_identifier
from . import mixins
from . import inspectors
from .objects import Error

FIELD_PATTERN = re.compile("fields\[(.+)\]")


class ViewSet(GenericViewSet):
    """
    Subclass base Django Rest Framework's GenericViewSet, adding JSON-API specific functionality

    Attributes
    ----------
    view_name_prefix = 'Privilege'
    lookup_field = "name"
    lookup_value_regex = "[^\/]+"
    collection = Users.objects.all()
    serializer_class = UserSerializer
    """

    swagger_schema = inspectors.EntitySwaggerAutoSchema
    lookup_field = "pk"
    filter_class = None
    validate_http_methods = ["POST", "PUT", "PATCH"]

    @property
    def view_name_prefix(self):
        if hasattr(self, "serializer_class") and self.serializer_class:
            return self.serializer_class.Meta.type.title()
        return ""

    def get_queryset(self):
        """
        Return the queryset that will be used to retrieve the object that this
        view will display.

        :param ViewSet self: This object
        :return: A collection of model objects
        """

        return self.get_collection(self.request)

    def get_collection(self, request):
        """
        Re-evaluate a collection on each request

        :param ViewSet self: This object
        :param rest_framework.request.Request request: A client request
        :return list collection: A list of model objects
        """

        collection = self.collection
        if isinstance(collection, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            collection = collection.all()

        return collection

    def get_resource(self, request, pk):
        """
        Retrieve a resource by primary identifier

        :param ViewSet self: This object
        :param rest_framework.request.Request request: A client request
        :param pk: The ID of the resource
        :return list collection: A filtered list of model objects
        """
        return get_object_or_404(
            self.get_collection(request).model,
            **{self.serializer_class.get_id_field(): pk}
        )

    def get_view_name(self):
        """
        Build a view name from the view name prefix and suffix.

        :param ViewSet self: This object
        :return: A view name
        :rtype: string
        """

        name = self.view_name_prefix
        if self.suffix:
            name += " " + self.suffix
        return name

    def initial(self, *args, **kwargs):
        """
        Initialize this Viewset, validating the request body and populating
        sparse fieldsets and includes.

        :param ViewSet self: This object
        """

        super(ViewSet, self).initial(*args, **kwargs)

        # Validate request bodies
        if self.request.method in self.validate_http_methods:
            self.validate_request_body(self.request.data)

        # Parse Query Params
        # Sparse Fieldsets
        self.parse_sparse_fieldset(self.request)
        # Includes
        self.parse_include(self.request)

        # Initialize document
        # This is just a convenience so you can
        # build up the document as you process
        # the request.
        self.document = DocumentSerializer(Document())

        # Initialize empty error list
        # This is just a convenience so you can
        # add to this list as your process the
        # the request.
        self.errors = []

    def get_allowed_includes(self):
        return getattr(
            self,
            "allowed_includes",
            self.serializer_class.define_relationships().keys(),
        )

    def parse_include(self, request):
        """
        Populate include node, converting from a comma-separated string list to
        a Python list

        :param ViewSet self: This object
        :param rest_framework.request.Request request: The client request
        """

        if "include" not in request.GET:
            request.include = []
            return

        request.include = request.GET["include"].split(",")

        invalid_includes = list(set(request.include) - set(self.get_allowed_includes()))
        if invalid_includes:
            raise Error(
                detail="The following are not valid includes: {}".format(
                    ", ".join(invalid_includes)
                ),
                source={"parameter": "include"},
            )

    def parse_sparse_fieldset(self, request):
        """
        Populate request fields, converting from a request query array to a dictionary.

        :param ViewSet self: This object
        :param rest_framework.request.Request request: The client request
        """

        request.fields = {}
        for param, value in request.GET.items():
            match = FIELD_PATTERN.search(param)
            if match:
                fields = filter(None, value.split(","))
                request.fields[match.group(1)] = list(set(fields))

    def validate_request_body(self, request_data):
        """
        Validate the body of a client request, ensuring that the single top-level
        attributes is "data", and is an array or object.

        :param ViewSet self: This object
        :param dict request_data: The top-level data element from request
        :raises ParseError: if validation fails
        """

        if "data" not in request_data:
            raise ParseError(
                'The top level object of all request bodies must include a "data" node.'
            )
        if (
            not isinstance(request_data["data"], list)
            and not isinstance(request_data["data"], dict)
            and request_data["data"] is not None
        ):
            raise ParseError('The top-level "data" element must be an array or object.')
        if len(request_data) != 1:
            raise ParseError(
                'There must be one and only one element at the top level of the json object: "data."'
            )

    def error_response(self, errors, status=400):
        """
        Build an error response from a list of errors and a status code.

        :param ViewSet self: This object
        :param list errors: A list of errors
        :param int status: HTTP status code
        :return Response response: A json response
        """

        return Response(
            DocumentSerializer(
                Document(errors=ErrorSerializer(errors, many=True).data)
            ).data,
            status=status,
        )

    def apply_pagination(self, collection):
        """
        Create a list of pagination links for response.

        :param ViewSet self: This object
        :param QuerySet collection: A list of model objects
        :return: A list of model objects
        :rtype: QuerySet
        """

        page_size = self.request.GET.get(
            "page[size]",
            getattr(settings, "DEFAULT_PAGE_SIZE", defaults.DEFAULT_PAGE_SIZE),
        )
        paginator = Paginator(collection, page_size)
        page = paginator.page(self.request.GET.get("page[number]", 1))

        self.document.instance.meta.update(
            {
                "count": paginator.count,
                "has_next": page.has_next(),
                "has_previous": page.has_previous(),
                "page_size": paginator.per_page,
                "page": page.number,
                "num_pages": paginator.num_pages,
            }
        )

        # Build links
        current_path = self.request.build_absolute_uri().split("?")[0]
        query = self.request.GET.copy()

        # first link
        query["page[number]"] = 1
        self.document.instance.links["first"] = (
            current_path + "?" + query.urlencode(safe="[]")
        )

        # next link
        self.document.instance.links["next"] = None
        if page.has_next():
            query["page[number]"] = page.next_page_number()
            self.document.instance.links["next"] = (
                current_path + "?" + query.urlencode(safe="[]")
            )

        # prev link
        self.document.instance.links["prev"] = None
        if page.has_previous():
            query["page[number]"] = page.previous_page_number()
            self.document.instance.links["prev"] = (
                current_path + "?" + query.urlencode(safe="[]")
            )

        # last link
        query["page[number]"] = paginator.num_pages
        self.document.instance.links["last"] = (
            current_path + "?" + query.urlencode(safe="[]")
        )

        return page.object_list

    def get_relationships(self):
        """
        Retrieve a dictionary of relationship handlers.

        :param ViewSet self: This object
        :return: A dictionary of relationships and handlers
        :rtype: dict
        """
        return self.serializer_class.define_relationships()

    def get_relationship_handler(self, relation):
        """
        Validate the requested relationship and retrieves handlers for
        available relationships.

        :param string relation: The name of a relationship
        :return: A dictionary of available relationships
        :rtype: dict
        :raises ParseError: if requested relationship is not defined
        """

        available_relationships = self.get_relationships()
        if relation not in available_relationships.keys():
            raise ParseError("Invalid relationship: {}".format(relation))
        return available_relationships[relation]


class ReadOnlyViewSet(
    mixins.ListMixin, mixins.RetrieveMixin, mixins.RelationshipRetrieveMixin, ViewSet
):
    """
    Create a ViewSet for a read-only endpoint.
    """

    pass


class ReadWriteViewSet(
    mixins.ListMixin,
    mixins.CreateMixin,
    mixins.RetrieveMixin,
    mixins.PartialUpdateMixin,
    mixins.DestroyMixin,
    mixins.RelationshipRetrieveMixin,
    mixins.RelationshipCreateMixin,
    mixins.RelationshipUpdateMixin,
    mixins.RelationshipDestroyMixin,
    ViewSet,
):
    """
    Create a viewset for a readable and writeable endpoint.
    """

    pass
