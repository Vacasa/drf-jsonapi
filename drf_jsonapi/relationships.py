from pydoc import locate

from django.conf import settings
from django.urls import resolve, Resolver404
from django.core.paginator import Paginator

from rest_framework.exceptions import ParseError


class RelationshipHandler(object):
    """
    Validates relationship requests, and builds response dictionaries.  This class
    is meant to be overridden by inheritance.  Some methods are not implemented here.
    """

    # These attributes are meant to be overridden by sub-classes
    many = False
    serializer_class = None
    related_field = None

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
            raise ParseError('The top-level "data" element must be an array of resource identifiers or an empty array.')

        if not self.many and not (isinstance(data, dict) or data is None):
            raise ParseError('The top-level "data" element must be a single resource object or null')

        return data

    def build_relationship_links(self, base_serializer, relation, resource, request=None):
        """
        Builds relationship links for a JSON-API response

        :param RelationshipHandler self: This object
        :param serializer base_serializer: A model serlializer
        :param string relation: The name of a relationship
        :param model resource: The model for the relationship "parent"
        :return: A links dictionary
        :rtype: dict
        """

        links = {}

        args = (
            settings.BASE_URL,
            base_serializer.Meta.base_path,
            base_serializer.get_id(resource),
            relation
        )

        # self
        try:
            resolve("{}/{}/relationships/{}".format(*args[1:]))
            links['self'] = "{}{}/{}/relationships/{}".format(*args)
        except Resolver404:
            pass

        # related
        try:
            resolve("{}/{}/{}".format(*args[1:]))
            links['related'] = "{}{}/{}/{}".format(*args)
        except Resolver404:
            pass

        # Allow overrides
        links = self.get_links(resource, links)

        return links

    def get_serializer_class(self):
        """
        Retrieve a serializer class

        :param RelationshipsHandler self: This object
        :return serializer_class:
        :rtype: type
        :raises NotImplementedError
        :raises ImportError
        """
        if isinstance(self.serializer_class, str):
            serializer_class = locate(self.serializer_class)
            if not serializer_class:
                raise ImportError("Unable to import serializer class: {}".format(self.serializer_class))
            return serializer_class
        elif self.serializer_class:
            return self.serializer_class
        raise NotImplementedError("`serializer_class` is missing or `get_serializer_class()` is not implemented in {}".format(self.__class__))

    def get_links(self, resource, links, request=None):
        """
        Retrieve links from given links attribute.

        :param RelationshipsHandler self: This object
        :param QuerySet resource: A model resource
        :param dict links:
        :return links:
        :rtype: dict
        """

        return links

    def get_related(self, resource, request=None):
        """
        Retrieve related resources

        :param RelationshipsHandler self: This object
        :return related:
        :rtype: object
        :raises NotImplementedError: As this method requires an override in the extending class
        """
        if self.related_field:
            related = getattr(resource, self.related_field)
            if self.many:
                return related.all()
            return related
        raise NotImplementedError("`related_field` is missing or `get_related` is not implemented in {}".format(self.__class__))

    def apply_pagination(self, related, page_size):
        """
        Builds a pagination metadata for a JSON-API response

        :param RelationshipsHandler self: This object
        :param django.db.models.query.QuerySet related: A collection of related
        objects from the database
        :param int page_size: The number of resources to display in view
        :return: A list containing a queryset and dictionary of metadata
        :rtype: list
        """

        paginator = Paginator(related, page_size)
        page = paginator.page(1)

        meta = {
            'count': paginator.count,
            'has_next': page.has_next(),
            'has_previous': page.has_previous(),
            'page_size': paginator.per_page,
            'page': page.number,
            'num_pages': paginator.num_pages
        }

        return page.object_list, meta

    def add_related(self, resource, related, request=None):
        """
        Add a related resource.
        NOTE: This currently only supports Many-to-Many relationships

        :param RelationshipsHandler self: This object
        :param model resource: The model for the relationship "parent"
        :param related: A collection of models to add
        :raises NotImplementedError:
        :raises TypeError:
        """
        assert(self.many)
        if not self.related_field:
            raise NotImplementedError("`related_field` is missing or `add_related` is not implemented in {}".format(self.__class__))
        try:
            getattr(resource, self.related_field).add(*related)
        except(TypeError):
            getattr(resource, self.related_field).add(related)

    def set_related(self, resource, related, request=None):
        """
        Set a related resource.

        :param RelationshipsHandler self: This object
        :param model resource: The model for the relationship "parent"
        :param django.db.models.query.QuerySet related: A collection of related
        objects from the database
        :raises NotImplementedError: As this method requires an override in the extending class
        """
        if not self.related_field:
            raise NotImplementedError("`set_related` is not implemented in {}".format(self.__class__))
        if self.many:
            getattr(resource, self.related_field).set(related)
        else:
            setattr(resource, self.related_field, related)

    def remove_related(self, resource, related, request=None):
        """
        Remove a related resource.

        :param RelationshipsHandler self: This object
        :param model resource: The model for the relationship "parent"
        :param django.db.models.query.QuerySet related: A collection of related
        objects from the database
        :raises NotImplementedError: As this method requires an override in the extending class
        """
        assert(self.many)
        if not self.related_field:
            raise NotImplementedError("`remove_related` is not implemented in {}".format(self.__class__))
        try:
            getattr(resource, self.related_field).remove(*related)
        except(TypeError):
            getattr(resource, self.related_field).remove(related)
