import itertools
import logging
import re
from collections import OrderedDict

from django.conf import settings
from django.urls import resolve, Resolver404

from drf_yasg.inspectors.view import SwaggerAutoSchema
from drf_yasg.inspectors.base import call_view_method
from drf_yasg import openapi
from drf_yasg.utils import is_list_view, guess_response_status

from .serializers import resource_identifier
from . import defaults

path_pattern = re.compile(r"{\w+}")

ACTIONS = {
    "list": "list",
    "create": "create",
    "retrieve": "detail",
    "partial_update": "update",
    "destroy": "delete",
    "relationship_retrieve": "",
    "relationship_create": "add",
    "relationship_update": "update",
    "relationship_destroy": "remove",
}


class EntitySwaggerAutoSchema(SwaggerAutoSchema):
    """
    Build an OpenAPI schema for an entity using serializers for resource objects, responses,
    query parameters, and metadata
    """

    implicit_body_methods = ("POST", "PATCH", "DELETE")

    def __init__(self, *args):
        super().__init__(*args)
        try:
            self.match = resolve(self.path)
        except Resolver404:
            pass
        if hasattr(self, 'match') and "relationship" in self.match.kwargs:
            self.relationship = self.match.kwargs["relationship"]
            self.relationships = self.view.serializer_class.define_relationships()
        else:
            self.relationship = None

    def get_view_serializer(self):
        if self.relationship:
            serializer_class = self.relationships[self.relationship].serializer_class
            serializer = resource_identifier(serializer_class)()
        else:
            serializer = call_view_method(self.view, "get_serializer")
        return serializer

    def get_summary_and_description(self):
        summary, description = super().get_summary_and_description()
        action = self.view.action
        resource_type = self.view.serializer_class.Meta.type
        actionValue = ACTIONS.get(action, action)
        if self.relationship:
            summary = "{} {} {}".format(
                resource_type, self.relationship, actionValue
            ).title()
        else:
           summary = "{} {}".format(resource_type, actionValue).title()
        return summary, description

    def get_tags(self, operation_keys):
        tags = super().get_tags(operation_keys)
        tags = map(lambda x: x.title(), tags)
        return list(tags)

    def serializer_to_schema(self, serializer):
        """
        Generate an OpenAPI schema from a serializer

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :param drf_jsonapi.serializers.resources.ResourceSerializer serializer: A serializer Class
        :return: An OpenAPI schema
        :rtype: drf_yasg.openapi.Schema
        """

        resource_type = serializer.Meta.type

        schema = openapi.Schema(
            title="Resource",
            type="object",
            properties={
                "type": {"type": "string", "enum": [resource_type], "required": True}
            },
            required=["type"],
        )
        schema.properties["id"] = {"type": ["integer", "string"]}
        schema.required.append("id")

        if not self.relationship:
            schema.properties["attributes"] = super().serializer_to_schema(serializer)

        return schema

    def get_request_body_schema(self, serializer):
        """
        Build a request body schema from an API resource serializer

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :param serializer: An API resource serializer
        :return: An OpenAPI schema
        :rtype: drf_yasg.openapi.Schema
        """

        if self.method == "DELETE" and not self.relationship:
            return None

        schema = super().get_request_body_schema(serializer)
        schema = openapi.Schema(
            title="Document", type="object", properties={"data": schema}
        )

        if self.relationship:
            handler = self.view.get_relationship_handler(self.relationship)
            if handler.many:
                schema.properties["data"] = openapi.Schema(
                    type=openapi.TYPE_ARRAY, items=schema.properties["data"]
                )

        return schema

    def get_response_schemas(self, response_serializers):
        """
        Create an OpenAPI response schema from a response serializer

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :param collections.OrderedDict response_serializers: A response serializer
        :return: An OpenAPI response schema
        :rtype: collections.OrderedDict
        """

        responses = super().get_response_schemas(response_serializers)

        for response in responses.values():
            if "schema" not in response:
                continue
            response["schema"] = openapi.Schema(
                title="Document", type="object", properties={"data": response["schema"]}
            )

        return responses

    def get_default_responses(self):
        """
        Get the default responses determined for this view from the request serializer and request method.

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :type: dict[str, openapi.Schema]
        :return: A default OpenAPI response
        :rtype: collections.OrderedDict
        """

        method = self.method.lower()

        if self.relationship and method != "get":
            return OrderedDict({str(204): ""})

        default_status = guess_response_status(method)
        default_schema = ""
        if method in ("get", "post", "put", "patch"):
            default_schema = self.get_request_serializer() or self.get_view_serializer()

        default_schema = default_schema or ""
        if default_schema and not isinstance(default_schema, openapi.Schema):
            default_schema = self.serializer_to_schema(default_schema) or ""

        if default_schema and self.is_list():
            default_schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=default_schema)

        return OrderedDict({str(default_status): default_schema})

    def get_query_parameters(self):
        """
        Retrieve a list of query parameters

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: A list of query parameters
        :rtype: list
        """

        if self.relationship:
            return []

        return list(
            itertools.chain(
                super().get_query_parameters(),
                self.get_sort_parameters(),
                self.get_sparse_fieldset_parameters(),
                self.get_include_parameters(),
            )
        )

    def is_list(self):
        """
        Determines if this is a GET list view, and returns a boolean

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :returns: true if this is a list
        :rtype: boolean
        """

        if self.relationship:
            handler = self.view.get_relationship_handler(self.relationship)
            return handler.many

        if self.method.lower() != "get":
            return False
        return is_list_view(self.path, self.method, self.view)

    def get_sort_parameters(self):
        """
        Get sort fields added to the view

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: A list of OpenAPI parameters
        :rtype: list[openapi.Parameter]
        """

        if not self.is_list():
            return []

        serializer_class = self.view.get_serializer_class()
        sort_fields = getattr(
            serializer_class.Meta, "sort_fields", serializer_class.Meta.fields
        )

        # Replace '__' with '.' to maintain consistency with filter fields
        sort_fields = [field.replace("__", ".") for field in sort_fields]

        return [
            openapi.Parameter(
                name="sort",
                in_="query",
                type="string",
                enum=[
                    val
                    for pair in zip(sort_fields, ["-" + x for x in sort_fields])
                    for val in pair
                ],
                description="Multiple values may be separated by commas.",
            )
        ]

    def get_sparse_fieldset_parameters(self):
        """
        Get sparse fieldset parameters added to the view

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: JSON-API "fields" parameter
        :rtype: list[openapi.Parameter]
        """

        if self.method.lower() == "delete":
            return []

        serializer_class = self.view.get_serializer_class()
        parameters = {}
        parameters[serializer_class.Meta.type] = openapi.Parameter(
            name="fields[{}]".format(serializer_class.Meta.type),
            in_="query",
            type="string",
            enum=serializer_class.Meta.fields,
            description="Multiple values may be separated by commas.",
        )

        if self.is_list():
            relationships = serializer_class.define_relationships()
            for serializer_class in [
                r.serializer_class for r in relationships.values()
            ]:
                parameters[serializer_class.Meta.type] = openapi.Parameter(
                    name="fields[{}]".format(serializer_class.Meta.type),
                    in_="query",
                    type="string",
                    enum=serializer_class.Meta.fields,
                    description="Multiple values may be separated by commas.",
                )

        return list(parameters.values())

    def get_include_parameters(self):
        """
        Get include parameters added to the view

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: JSON-API "include" parameter
        :rtype: list[openapi.Parameter]
        """

        if not self.is_list():
            return []

        return [
            openapi.Parameter(
                name="include",
                in_="query",
                type="string",
                enum=list(self.view.get_allowed_includes()),
                description="Multiple values may be separated by commas.",
            )
        ]

    def get_pagination_parameters(self):
        """
        Return the parameters added to the view by its paginator.

        :param drf_jsonapi.inspectors.SwaggerAutoSchema self: This object
        :return: Pagination parameters
        :rtype: list[openapi.Parameter]
        """

        if not self.is_list():
            return []

        default_page_size = getattr(
            settings, "DEFAULT_PAGE_SIZE", defaults.DEFAULT_PAGE_SIZE
        )

        return [
            openapi.Parameter(
                name="page[size]",
                in_="query",
                type="integer",
                default=default_page_size,
                description="Default page size: {}".format(default_page_size),
            ),
            openapi.Parameter(
                name="page[number]", in_="query", type="integer", default=1
            ),
        ]
