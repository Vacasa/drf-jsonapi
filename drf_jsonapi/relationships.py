import importlib

from django.core.paginator import Paginator, EmptyPage
from django.urls import resolve, reverse, NoReverseMatch

from rest_framework.exceptions import ParseError


class RelationshipHandler:
    """
    Validates relationship requests, and builds response dictionaries.  This class
    is meant to be overridden by inheritance.  Some methods are not implemented here.
    """

    # These attributes are meant to be overridden by sub-classes
    many = False
    serializer_class = None
    related_field = None
    default_page_size = None
    url_segment = None

    def __init__(
        self,
        serializer_class,
        read_only=False,
        many=False,
        url_segment=None,
        related_field=None,
    ):
        """
        :param [str, ResourceModelSerializer] serializer_class: a serializer class or a dotted string used to locate one
        :param str related_field: The field used to lookup the relationship
        :param bool many: Whether the relationship represents a "to-many" relationship
        :param str url_segment: A url segement to use for the relationship in relationship URLs. Will default to relationship name if left unset
        :param bool read_only: Whether to create write endpoints for this relationship
        """

        if isinstance(serializer_class, str):
            serializer_class_name = serializer_class.split(".").pop()
            module_path = ".".join(serializer_class.split(".")[:-1])
            serializer_module = importlib.import_module(module_path)
            serializer_class = getattr(serializer_module, serializer_class_name)

        self.serializer_class = serializer_class
        self.read_only = read_only
        self.many = self.many or many
        self.url_segment = self.url_segment or url_segment
        self.related_field = self.related_field or related_field

    def validate(self, data):
        """
        Validate relationship requests, ensuring top-level data "data" element is
        a list in a to-many relationship, or a single element in a to-one relationship.

        :param RelationshipHandler self: This object
        :param list data: Request data
        :return: A list of data objects or a single data object
        :rtype: list
        :raises ParseError: when the top-level "data" element(s) is/are malformed
        """

        if self.many and not isinstance(data, list):
            raise ParseError(
                'The top-level "data" element must be an array of resource identifiers or an empty array.'
            )

        if not self.many and not (isinstance(data, dict) or data is None):
            raise ParseError(
                'The top-level "data" element must be a single resource object or null'
            )

        return data

    def build_relationship_links(self, base_serializer, relation, resource, request):
        """
        Builds relationship links for a JSON-API response

        :param RelationshipHandler self: This object
        :param serializer base_serializer: A model serializer
        :param string relation: The name of a relationship
        :param model resource: The model for the relationship "parent"
        :param django.http.HttpRequest request: The request being processed. May hold information
                about pagination and/or User object useful for permissions.
        :return: A links dictionary
        :rtype: dict
        """

        links = {}

        basename = getattr(base_serializer.Meta, "basename", base_serializer.Meta.type)
        app_name = resolve(request.path).app_name

        if request:
            try:
                path = reverse(
                    "{}:{}-relationships-{}".format(app_name, basename, relation),
                    kwargs={"pk": base_serializer.get_id(resource)},
                )
                links["self"] = request.build_absolute_uri(path)
            except NoReverseMatch:
                pass

        # Allow overrides
        links = self.get_links(resource, links, request)

        return links

    def get_links(self, resource, links, request):
        """
        Retrieve links from given links attribute.

        :param RelationshipsHandler self: This object
        :param QuerySet resource: A model resource
        :param dict links:
        :return links:
        :rtype: dict
        """

        return links

    def get_related(self, resource, request):
        """
        Retrieve related resources

        :param RelationshipsHandler self: This object
        :return related:
        :param django.http.HttpRequest request: The request being processed. May hold information
                about pagination and/or User object useful for permissions.
        :rtype: object
        :raises NotImplementedError: As this method requires an override in the extending class
        """
        if self.related_field:
            related = getattr(resource, self.related_field)
            if self.many:
                return related.all()
            return related
        raise NotImplementedError(
            "`related_field` is missing or `get_related` is not implemented in {}".format(
                self.__class__
            )
        )

    def apply_pagination(self, related, page_size=None, page_number=1):
        """
        Builds a pagination metadata for a JSON-API response

        :param RelationshipsHandler self: This object
        :param django.db.models.query.QuerySet related: A collection of related
        objects from the database
        :param int page_size: The number of resources to display in view
        :return: A list containing a queryset and dictionary of metadata
        :rtype: list
        """

        page_size = page_size or self.default_page_size
        page_number = int(page_number)

        paginator = Paginator(related, page_size)

        try:
            page = paginator.page(page_number)
            meta = {
                "count": paginator.count,
                "has_next": page.has_next(),
                "has_previous": page.has_previous(),
                "page_size": paginator.per_page,
                "page": page.number,
                "num_pages": paginator.num_pages,
            }
            return page.object_list, meta
        except EmptyPage:
            meta = {
                "count": paginator.count,
                "has_next": False,
                "has_previous": page_number == paginator.num_pages + 1,
                "page_size": paginator.per_page,
                "page": int(page_number),
                "num_pages": paginator.num_pages,
            }
            return [], meta

    def add_related(self, resource, related, request):
        """
        Add a related resource.
        NOTE: This currently only supports Many-to-Many relationships

        :param RelationshipsHandler self: This object
        :param model resource: The model for the relationship "parent"
        :param related: A collection of models to add
        :param django.http.HttpRequest request: The request being processed. May hold information
                about pagination and/or User object useful for permissions.
        :raises NotImplementedError:
        :raises TypeError:
        """
        assert self.many
        if not self.related_field:
            raise NotImplementedError(
                "`related_field` is missing or `add_related` is not implemented in {}".format(
                    self.__class__
                )
            )
        try:
            getattr(resource, self.related_field).add(*related)
        except (TypeError):
            getattr(resource, self.related_field).add(related)

    def set_related(self, resource, related, request):
        """
        Set a related resource.

        :param RelationshipsHandler self: This object
        :param model resource: The model for the relationship "parent"
        :param django.db.models.query.QuerySet related: A collection of related
        objects from the database
        :param django.http.HttpRequest request: The request being processed. May hold information
                about pagination and/or User object useful for permissions.
        :raises NotImplementedError: As this method requires an override in the extending class
        """
        if not self.related_field:
            raise NotImplementedError(
                "`set_related` is not implemented in {}".format(self.__class__)
            )
        if self.many:
            getattr(resource, self.related_field).set(related)
        else:
            setattr(resource, self.related_field, related)

    def remove_related(self, resource, related, request):
        """
        Remove a related resource.

        :param RelationshipsHandler self: This object
        :param model resource: The model for the relationship "parent"
        :param django.db.models.query.QuerySet related: A collection of related
        objects from the database
        :param django.http.HttpRequest request: The request being processed. May hold information
                about pagination and/or User object useful for permissions.
        :raises NotImplementedError: As this method requires an override in the extending class
        """
        assert self.many
        if not self.related_field:
            raise NotImplementedError(
                "`remove_related` is not implemented in {}".format(self.__class__)
            )
        try:
            getattr(resource, self.related_field).remove(*related)
        except (TypeError):
            getattr(resource, self.related_field).remove(related)
