from pydoc import locate
import collections

from django.core.exceptions import FieldError
from django.urls import resolve, Resolver404
from django.conf import settings

from rest_framework import serializers
from rest_framework.serializers import LIST_SERIALIZER_KWARGS
from rest_framework.exceptions import ParseError

from .utils import resource_identifier

from ..objects import Error
from ..utils import listify


class ResourceListSerializer(serializers.ListSerializer):
    """
    Handles the serialization of included resources
    See: http://jsonapi.org/format/#document-compound-documents
    """

    @property
    def included(self):
        """
        De-duplicate 'included' resources via dictionary comprehension

        :param serializer self: This object instance
        :return: A de-duplicated list of included resources
        :rtype: dict_values
        """

        return {(x['type'], x['id']): x for x in self.child.included}.values()


class ResourceSerializer(serializers.Serializer):
    """
    Handles the serialization/deserialization of JSON API resource objects
    See: http://jsonapi.org/format/#document-resource-objects
    """

    def __init__(self, *args, **kwargs):
        """
        Populate this object with include, fields, and pagination
        properties.  Limit fields returned by applying sparse fieldset.

        :param serializer self: This object instance
        :param list include: List of relationships to include in response
        :param dict only_fields: Dictionary of fields to include in response
        :param int page_size: The number of resources to include on page
        """

        self.included = []

        # Validate Includes
        self.include = list(filter(None, kwargs.pop('include', [])))
        available_relationships = getattr(self.Meta, 'relationships', {}).keys()
        invalid_includes = list(set(self.include) - set(available_relationships))
        if invalid_includes:
            raise Error(
                detail="Invalid relationship(s): {}".format(", ".join(invalid_includes)),
                source={'parameter': 'include'}
            )

        self.only_fields = kwargs.pop('only_fields', None)
        self.page_size = kwargs.pop('page_size', settings.DEFAULT_PAGE_SIZE)
        super().__init__(*args, **kwargs)

        # We have to this AFTER super().__init__ so that self.fields is populated
        if self.only_fields is not None and self.Meta.type in self.only_fields:
            self.apply_sparse_fieldset(self.only_fields[self.Meta.type])

    def apply_sparse_fieldset(self, fields=None):
        """
        Limit JSON-API object properties returned by "fields" parameter.
        See: http://jsonapi.org/format/#fetching-sparse-fieldsets

        :param serializer self: This object instance
        :param list fields: A list of fields that object properties will be limited to.
        """

        # Validate the field list against Meta.fields
        if hasattr(self.Meta, 'fields'):
            invalid_fields = set(fields).difference(self.Meta.fields)
            if invalid_fields:
                raise ParseError("Invalid field(s) for fields[{}]: {}".format(
                    self.Meta.type,
                    ",".join(invalid_fields)
                ))

        # Drop any fields that are not specified in the `fields` argument.
        allowed = set(fields)
        existing = set(self.fields)
        for field_name in existing - allowed:
            self.fields.pop(field_name)

    def run_validation(self, data):
        """
        Validates the resource object according to JSON API spec.

        :param serializer self: This object instance
        :param data: resource object to validate
        :raises ParseError: if missing 'attributes' node
        :return: An error dictionary containing issues found
        :rtype: dict
        """

        self.validate_resource_type(data)

        # Extract just to attributes since this is what
        # the superclass is expecting
        try:
            attributes = data['attributes']
        except KeyError:
            raise ParseError("Missing `attributes` in resource object")
        return super().run_validation(attributes)

    def to_representation(self, instance):
        """
        Wraps output according to the JSON-API Resource Object Spec.

        :param serializer self: This object instance
        :param model instance: The object needing representation
        :return: A dictionary representing a JSON-API resource object
        :rtype: dict
        """

        resource = {
            'type': self.Meta.type,
            'id': self.get_id(instance)
        }

        # Add Attributes
        data = super().to_representation(instance)
        resource['attributes'] = data

        # Add Relationships
        relationships = self.get_relationships(instance)
        if relationships:
            resource['relationships'] = relationships

        # Add Meta
        meta = self.get_meta(instance)
        if meta:
            resource['meta'] = meta

        # Add Links
        links = self.get_links(instance)
        if links:
            resource['links'] = links

        return resource

    @property
    def relationships(self):
        """
        Retrieve relationships from the Meta property of this object

        :param serializer self: This object instance
        :return: relationships node of this object's Meta property
        :rtype: dict
        """

        return getattr(self.Meta, 'relationships', {})

    def get_relationships(self, instance):
        """
        Retrieve a relationships dictionary from this object's relationships items

        :param serializer self: This object instance
        :param model instance: The object needing serialized relationships
        :return: A dictionary of relationships
        :rtype: dict
        """

        relationships = {}

        for relation, handler in self.relationships.items():
            data = self.get_relationship_data(relation, handler, instance)
            if data:
                relationships[relation] = data

        return relationships

    def get_relationship_data(self, relation, handler, instance):
        """
        Retrieve a data dictionary for a relation

        :param serializer self: This object instance
        :param str relation: A string representation of the relationship
        :param relationship handler handler: A relationship handler object
        :param model instance: An object requiring serialization
        :return: A dictionary of relationship data
        :rtype: dict
        """

        data = {}

        # Build Links
        links = handler.build_relationship_links(self, relation, instance)
        if not links:
            return data

        data['links'] = links

        if relation not in self.include:
            return data

        # Add Resource Identifiers for linkage
        serializer_class = handler.get_serializer_class()
        related = handler.get_related(instance)

        if handler.many:
            related, data['meta'] = handler.apply_pagination(related, self.page_size)

        data['data'] = resource_identifier(serializer_class)(
            related,
            many=handler.many
        ).data

        self.included += listify(serializer_class(
            related,
            many=handler.many,
            only_fields=self.only_fields
        ).data)

        return data

    def get_id(self, instance):
        """
        Retrieve the primary key for this instance

        :param serializer self: This object instance
        :param model instance: The object whose primary key we seek
        :return: A primary key string
        :rtype: string
        """

        attr = getattr(self.Meta, 'id_field', 'pk')
        return getattr(instance, attr)

    def get_meta(self, instance):
        """
        Retrieve an empty meta dictionary

        :param serializer self: This object instance
        :param model instance: The object whose metadata we seek
        :return: An empty dictionary
        :rtype: dict
        """

        return {}

    def get_links(self, instance):
        """
        Retrieve a dictionary of links

        :param serializer self: This object instance
        :param model instance: The object whose links we seek
        :return: A links dictionary
        :rtype: dict
        """

        links = {}

        # self
        try:
            resolve("{}/{}".format(
                self.Meta.base_path,
                self.get_id(instance),
            ))
            links['self'] = "{}{}/{}".format(
                settings.BASE_URL,
                self.Meta.base_path,
                self.get_id(instance)
            )
        except Resolver404:
            pass

        return links

    @classmethod
    def sort(cls, sort_param, collection):
        """
        Support sorting simple lists by a query
        param that looks like `sort=foo,-bar`

        :param drf_jsonapi.serializers.utils.resource_identifier.<locals>.ResourceIdentifier cls: A class object
        :param str sort_param: A comma-separated list of properties to sort by
        :param collection: The collection of items to sort
        :return: The sorted collection
        """

        if not sort_param:
            return collection

        sort_fields = filter(None, sort_param.split(','))

        for field in list(sort_fields)[::-1]:
            reverse = False
            if field[0] == '-':
                field = field[1:]
                reverse = True
            collection = sorted(collection, key=lambda x: getattr(x, field), reverse=reverse)

        return collection

    @classmethod
    def from_identity(cls, data, many=False):
        """
        Retrieve an object or list of objects from an ID

        :param drf_jsonapi.serializers.utils.resource_identifier.<locals>.ResourceIdentifier cls: A class object
        :param data: A list of resource IDs or a single resource ID
        :param many: If data is a list
        :return: A model object
        """

        if many:
            objects = []
            for resource in data:
                objects.append(cls.get_object_from_identity(resource))
            return objects
        else:
            return cls.get_object_from_identity(data)

    @classmethod
    def validate_resource_type(cls, data):
        """
        Validate if a JSON-API resource has a type

        :param drf_jsonapi.serializers.utils.resource_identifier.<locals>.ResourceIdentifier cls: A class object
        :param data: A JSON-API data object
        :raises ParseError: if type not found or not specified
        """

        if 'type' not in data:
            raise ParseError("Missing `type` in resource object")
        if 'type' in data and hasattr(cls, 'Meta') and hasattr(cls.Meta, 'type') and data['type'] != cls.Meta.type:
            raise ParseError("Invalid `type`: '{}' (Did you mean '{}'?)".format(data['type'], cls.Meta.type))

    @classmethod
    def get_object_from_identity(cls, data):
        """
        Retrieve a single object from an ID

        :param drf_jsonapi.serializers.utils.resource_identifier.<locals>.ResourceIdentifier cls: A class object
        :param data: A single JSON-API data object
        :return: An object, retrieved by ID
        """

        cls.validate_resource_type(data)
        return cls.get_object_by_id(data['id'])

    @classmethod
    def get_object_by_id(cls, id):
        """
        Retrieve an object by ID

        :param drf_jsonapi.serializers.utils.resource_identifier.<locals>.ResourceIdentifier cls: A class object
        :param id: An ID string
        :raises NotImplementedError: This method is not implemented
        """

        raise NotImplementedError("`get_object_by_id` is not implemented in {}".format(cls))

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        Retrieve a Resource Identifier representing a requested relationship
        :param drf_jsonapi.serializers.utils.resource_identifier.<locals>.ResourceIdentifier cls: A Resource Identifier object
        :return: A ResourceIdentifer object
        :rtype: ResourceIdentifier
        """

        child_serializer = cls(*args, **kwargs)
        list_kwargs = {
            'child': child_serializer,
        }
        list_kwargs.update({
            key: value for key, value in kwargs.items()
            if key in LIST_SERIALIZER_KWARGS
        })
        meta = getattr(cls, 'Meta', None)
        list_serializer_class = getattr(meta, 'list_serializer_class', ResourceListSerializer)

        return list_serializer_class(*args, **list_kwargs)


class ResourceModelSerializer(ResourceSerializer, serializers.ModelSerializer):

    @classmethod
    def get_object_by_id(cls, id):
        """
        Retrive a model object by its primary key

        :param rest_framework.serializers.SerializerMetaclass cls: A class object
        :param str id: A primary key string
        :throws Error: If an object cannot be found by the primary key
        :return: A model object
        """

        try:
            return cls.Meta.model.objects.get(pk=id)
        except (cls.Meta.model.DoesNotExist) as e:
            raise Error(
                detail=str(e),
                status_code=400,
                meta={'id': id}
            )

    @classmethod
    def sort(cls, sort_param=None, queryset=None):
        """
        Retrieve a sorted queryset

        :param rest_framework.serializers.SerializerMetaclass cls: A class object
        :param str sort_param: A comma-separated list of properties to sort by
        :param django.db.models.query.QuerySet queryset: A collection of model objects
        :return: A sorted queryset
        :rtype: django.db.models.query.QuerySet queryset
        """

        # Assuming collection is a QuerySet

        if not sort_param:
            return queryset

        sort_fields = list(filter(None, sort_param.split(',')))

        # validate the sort fields actually exist in the model
        field_names = [field.name for field in queryset.model._meta.get_fields()]
        test_fields = [field[1:] if field[0] in ('-', '+') else field for field in sort_fields]
        invalid_fields = set(test_fields).difference(field_names)

        if invalid_fields:
            raise ParseError("Invalid field(s) for sort: {}".format(
                ",".join(invalid_fields)
            ))

        return queryset.order_by(*sort_fields)
