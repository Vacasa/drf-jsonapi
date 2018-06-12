import itertools
import re
from collections import OrderedDict

from django.conf import settings

from drf_yasg.inspectors.view import SwaggerAutoSchema
from drf_yasg import openapi
from drf_yasg.utils import is_list_view, guess_response_status

path_pattern = re.compile(r"{\w+}")


class EntitySwaggerAutoSchema(SwaggerAutoSchema):
    """
    Build an OpenAPI schema for an entity using serializers for resource objects, responses,
    query parameters, and metadata
    """

    def serializer_to_schema(self, serializer):
        """
        Generate an OpenAPI schema from an event serializer

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :param api.resources.events.serializers.EventSerializer serializer: An event serializer
        :return: An OpenAPI schema
        :rtype: drf_yasg.openapi.Schema
        """

        schema = openapi.Schema(
            title="Resource",
            type="object",
            properties={
                'type': {'type': 'string', 'enum': [serializer.Meta.type], 'required': True}
            },
            required=['type']
        )

        if self.method in ('GET', 'PATCH', 'UPDATE'):
            schema.properties['id'] = {'type': ['integer', 'string']}
            schema.required.append('id')

        schema.properties['attributes'] = super().serializer_to_schema(serializer)

        return schema

    def get_request_body_schema(self, serializer):
        """
        Build a request body schema from an API resource serializer

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :param serializer: An API resource serializer
        :return: An OpenAPI schema
        :rtype: drf_yasg.openapi.Schema
        """

        schema = super().get_request_body_schema(serializer)

        return openapi.Schema(
            title="Document",
            type="object",
            properties={
                'data': schema
            }
        )

    def get_response_schemas(self, response_serializers):
        """
        Create an OpenAPI response schema from a response serializer

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :param collections.OrderedDict response_serializers: A response serializer
        :return: An OpenAPI response schema
        :rtype: collections.OrderedDict
        """

        responses = super().get_response_schemas(response_serializers)

        for rc, response in responses.items():
            if 'schema' not in response:
                continue
            response['schema'] = openapi.Schema(
                title="Document",
                type="object",
                properties={
                    'data': response['schema']
                }
            )

        return responses

    def get_default_responses(self):
        """
        Get the default responses determined for this view from the request serializer and request method.

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :type: dict[str, openapi.Schema]
        :return: A default OpenAPI response
        :rtype: collections.OrderedDict
        """

        method = self.method.lower()

        default_status = guess_response_status(method)
        default_schema = ''
        if method in ('get', 'post', 'put', 'patch'):
            default_schema = self.get_request_serializer() or self.get_view_serializer()

        default_schema = default_schema or ''
        if default_schema and not isinstance(default_schema, openapi.Schema):
            default_schema = self.serializer_to_schema(default_schema) or ''

        if default_schema:
            if self.is_list():
                default_schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=default_schema)
            if self.should_page():
                default_schema = self.get_paginated_response(default_schema) or default_schema

        return OrderedDict({str(default_status): default_schema})

    def get_query_parameters(self):
        """
        Retrieve a list of query parameters

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: A list of query parameters
        :rtype: list
        """

        parameters = super().get_query_parameters()
        parameters = parameters + self.get_sort_parameters()

        return list(itertools.chain(
            super().get_query_parameters(),
            self.get_sort_parameters(),
            self.get_sparse_fieldset_parameters(),
            self.get_include_parameters()
        ))

    def is_list(self):
        """
        Determines if this is a GET list view, and returns a boolean

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :returns: true if this is a list
        :rtype: boolean
        """

        if self.method.lower() != 'get':
            return False

        return is_list_view(self.path, self.method, self.view)

    def should_page(self):
        """
        Determine if pagination should apply to this schema

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: A boolean indicating if this schema should include pagination
        :rtype: boolean
        """

        return self.is_list()

    def get_sort_parameters(self):
        """
        Get sort fields added to the view

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: A list of OpenAPI parameters
        :rtype: list[openapi.Parameter]
        """

        if not self.is_list():
            return []

        serializer_class = self.view.get_serializer_class()
        sort_fields = getattr(serializer_class.Meta, 'sort_fields', serializer_class.Meta.fields)
        return [openapi.Parameter(
            name="sort",
            in_="query",
            type="string",
            enum=[val for pair in zip(sort_fields, ['-' + x for x in sort_fields]) for val in pair],
            description="Multiple values may be separated by commas."
        )]

    def get_sparse_fieldset_parameters(self):
        """
        Get sparse fieldset parameters added to the view

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: JSON-API "fields" parameter
        :rtype: list[openapi.Parameter]
        """

        if self.method.lower() == 'delete':
            return []

        serializer_class = self.view.get_serializer_class()
        parameters = [openapi.Parameter(
            name="fields[{}]".format(serializer_class.Meta.type),
            in_="query",
            type="string",
            enum=serializer_class.Meta.fields,
            description="Multiple values may be separated by commas."
        )]

        if not self.is_list():
            return parameters

        relationships = getattr(serializer_class.Meta, 'relationships', {})
        for serializer_class in [r.get_serializer_class() for r in relationships.values()]:
            parameters.append(openapi.Parameter(
                name="fields[{}]".format(serializer_class.Meta.type),
                in_="query",
                type="string",
                enum=serializer_class.Meta.fields,
                description="Multiple values may be separated by commas."
            ))

        return parameters

    def get_include_parameters(self):
        """
        Get include parameters added to the view

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: JSON-API "include" parameter
        :rtype: list[openapi.Parameter]
        """

        if not self.is_list():
            return []

        serializer_class = self.view.get_serializer_class()

        return [openapi.Parameter(
            name="include",
            in_="query",
            type="string",
            enum=list(getattr(serializer_class.Meta, 'relationships', {}).keys()),
            description="Multiple values may be separated by commas."
        )]

    def get_pagination_parameters(self):
        """
        Return the parameters added to the view by its paginator.

        :param jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: Pagination parameters
        :rtype: list[openapi.Parameter]
        """

        if not self.should_page():
            return []

        return [
            openapi.Parameter(
                name="page[size]",
                in_="query",
                type="integer",
                default=settings.DEFAULT_PAGE_SIZE,
                description="Default page size: {}".format(settings.DEFAULT_PAGE_SIZE),
            ),
            openapi.Parameter(
                name="page[number]",
                in_="query",
                type="integer",
                default=1
            ),
        ]


class RelationshipSwaggerAutoSchema(EntitySwaggerAutoSchema):
    '''
        """
    Build an OpenAPI schema for a relationship using serializers for resource objects, responses,
    query parameters, and metadata
    """

    '''
    implicit_body_methods = ('POST', 'PATCH', 'DELETE')

    def get_operation_id(self, operation_keys):
        """
        Remove relationship and list elements from the operation keys to reduce
        the length of the operation IDs for relationship endpoints

        TODO: Improve this. I'm not crazy about these string replacements
        but it's an effort to reduce the length of the operation IDs for
        relationship endpoints.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :param list operation_keys: operation ID
        :return: shorted operation ID string
        :rtype: string
        """

        id = super().get_operation_id(operation_keys)
        id = id.replace('_relationships', '')
        id = id.replace('_list', '')
        id = id.replace('partial_update', 'patch')

        return id

    def serializer_to_schema(self, serializer):
        """
        Retrieve a resource object schema from a resource identifier serializer.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :param jsonapi.serializers.utils.resource_identifier.<locals>.ResourceIdentifier serializer:
        A resource identifier serializer
        :return: Adjusted schema
        :rtype: drf_yasg.openapi.Schema
        """
        schema = openapi.Schema(
            title="Resource",
            type="object",
            properties={
                'type': {'type': 'string', 'enum': [serializer.Meta.type], 'required': True}
            },
            required=['type']
        )
        if self.method in ('GET', 'PATCH', 'POST', 'DELETE'):
            schema.properties['id'] = {'type': ['integer', 'string']}
            schema.required.append('id')

        return schema

    def get_default_responses(self):
        """
        Create an ordered dictionary describing default success responses.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :return: Ordered dictionary describing default response
        :rtype: Ordered dictionary
        """

        if self.method == 'GET':
            status = '200'
            serializer = self.get_request_serializer() or self.get_view_serializer()
            schema = self.serializer_to_schema(serializer) or ''
        else:
            status = '204'
            schema = ''

        if schema:
            if self.is_list():
                schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=schema)
            if self.should_page():
                schema = self.get_paginated_response(schema) or schema

        return OrderedDict({str(status): schema})

    def get_request_body_schema(self, serializer):
        """
        Add an array of data objects to data node in schema - if relationship
        handler has many objects.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :param jsonapi.serializers.utils.resource_identifier.<locals>.ResourceIdentifier serializer:
        A resource identifier serializer
        :return: Adjusted schema
        :rtype: drf_yasg.openapi.Schema
        """

        schema = super().get_request_body_schema(serializer)

        handler = self.view.get_relationship_handler(self.view.relationship)
        if handler.many:
            schema.properties['data'] = openapi.Schema(type=openapi.TYPE_ARRAY, items=schema.properties['data'])

        return schema

    def get_sort_parameters(self):
        """
        Retrieve a list of sort parameters - or an empty list if the method is
        not GET or not a list.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :return: List of sort parameters
        :rtype: list
        """

        handler = self.view.get_relationship_handler(self.view.relationship)
        if self.method != 'GET' or not handler.many:
            return []
        return super().get_sort_parameters()

    def should_page(self):
        """
        Determine if results should paginate - false if method not GET and not a list.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :return: Boolean indicating if results should paginate
        :rtype: boolean
        """

        handler = self.view.get_relationship_handler(self.view.relationship)
        return self.method == 'GET' and handler.many

    def is_list(self):
        """
        Determine if response body is a list.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :return: Boolean indicating if results are a list
        :rtype: boolean
        """
        handler = self.view.get_relationship_handler(self.view.relationship)
        return handler.many

    def get_sparse_fieldset_parameters(self):
        """
        Retrieve list of sparse fieldset parameters.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :return: list of fieldset parameters
        :rtype: list
        """

        return []

    def get_include_parameters(self):
        """
        Retrieve list of include parameters.

        :param jsonapi.inspectors.RelationshipSwaggerAutoSchema self: This object
        :return: list of include parameters
        :rtype: list
        """

        return []
