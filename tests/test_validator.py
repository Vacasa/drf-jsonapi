import unittest

from django.test import tag
from drf_jsonapi.validator import JsonApiValidator
from drf_jsonapi.response import Response as JsonApiResponse


class Response(JsonApiResponse):
    def json(self):
        return self.data


class TestJsonApiValidator(unittest.TestCase):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.validator = JsonApiValidator()
        self.valid_url = "http://dead.net"
        self.valid_test_data_entry = {"type": "test_type", "id": "test_id"}
        self.valid_link_object = {"self": self.valid_url}
        self.valid_relationships_entry = {"related_type": self.valid_link_object}
        self.valid_content_type = "application/vnd.api+json"

    @tag("is_valid")
    def test_is_valid_passes(self):
        response = Response(
            content_type=self.valid_content_type,
            data={"data": self.valid_test_data_entry},
        )
        response["Content-Type"] = self.valid_content_type
        self.assertTrue(self.validator.is_valid(response=response))
        self.assertEqual([], self.validator.errors)

    @tag("is_valid")
    def test_is_valid_fails_with_non_response(self):
        self.assertFalse(self.validator.is_valid(response="foo"))
        self.assertEqual(["Response must be of type Response"], self.validator.errors)

    @tag("is_valid")
    def test_is_valid_fails_with_no_headers(self):
        response = Response(data={"data": self.valid_test_data_entry})
        del (response["Content-Type"])
        self.assertFalse(self.validator.is_valid(response))
        self.assertEqual(
            ["Non-empty Response MUST have 'Content-Type' header"],
            self.validator.errors,
        )

    @tag("is_valid")
    def test_is_valid_fails_with_wrong_headers(self):
        response = Response(
            headers={"Bunk-Header": ""}, data={"data": self.valid_test_data_entry}
        )
        del (response["Content-Type"])
        self.assertFalse(self.validator.is_valid(response))
        self.assertEqual(
            ["Non-empty Response MUST have 'Content-Type' header"],
            self.validator.errors,
        )

    @tag("is_valid")
    def test_is_valid_fails_with_wrong_content_type_header(self):
        self.assertFalse(
            self.validator.is_valid(
                Response(
                    headers={"Content-Type": ""},
                    data={"data": self.valid_test_data_entry},
                )
            )
        )
        self.assertEqual(
            ["'Content-Type' header MUST be equal to 'application/vnd.api+json'"],
            self.validator.errors,
        )

    @tag("is_valid")
    def test_is_valid_passes_with_empty_top_level(self):
        response = Response(data={"data": []})
        response["Content-Type"] = self.valid_content_type
        self.assertTrue(self.validator.is_valid(response))

    @tag("is_valid")
    def test_is_valid_fails_with_bad_character(self):
        response = Response(data={"data": {"b@d": "stuff"}})
        response["Content-Type"] = self.valid_content_type
        self.assertFalse(self.validator.is_valid(response=response))
        self.assertIn(
            "'@' is not a valid character in a Member Name", self.validator.errors
        )

    @tag("is_valid")
    def test_is_valid_passes_with_empty_data_with_204_response_code(self):
        response = Response(status=204)
        response["Content-Type"] = self.valid_content_type
        self.assertTrue(self.validator.is_valid(response=response))

    @tag("is_valid")
    def test_is_valid_fails_with_empty_data_without_204_response_code(self):
        response = Response()
        response["Content-Type"] = self.valid_content_type
        self.assertFalse(self.validator.is_valid(response=response))

    @tag("headers")
    def test_validate_headers_fails_without_content_type_header(self):
        response = Response(data="stuff")
        del (response["Content-Type"])
        self.assertEqual(
            ["Non-empty Response MUST have 'Content-Type' header"],
            self.validator._validate_headers(response=response),
        )

    @tag("headers")
    def test_validate_headers_passes_without_content_type_header_with_204(self):
        response = Response(data="stuff", status=204)
        del (response["Content-Type"])
        self.assertEqual([], self.validator._validate_headers(response=response))

    @tag("headers")
    def test_validate_headers_fails_with_wrong_content_type_header(self):
        response = Response(data="stuff")
        self.assertEqual(
            ["'Content-Type' header MUST be equal to 'application/vnd.api+json'"],
            self.validator._validate_headers(response=response),
        )

    @tag("headers")
    def test_validate_headers_passes_with_correct_content_type_header(self):
        response = Response(data="stuff")
        response["Content-Type"] = "application/vnd.api+json"
        self.assertEqual([], self.validator._validate_headers(response=response))

    """
    A JSON object MUST be at the root of every JSON API request and response containing data. This object defines a document’s “top level”.

    A document MUST contain at least one of the following top-level members:

    data: the document’s “primary data”
    errors: an array of error objects
    meta: a meta object that contains non-standard meta-information.
    The members data and errors MUST NOT coexist in the same document.
    """

    @tag("top_level")
    def test_top_level_with_data_true(self):
        test_dict = {"data": self.valid_test_data_entry}
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("top_level")
    def test_top_level_with_data_empty_list_true(self):
        test_dict = {"data": []}
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("top_level")
    def test_top_level_with_meta_true(self):
        test_dict = {"meta": []}
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("top_level")
    def test_top_level_with_meta_as_dict_fails(self):
        test_dict = {"meta": {}}
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("top_level")
    def test_top_level_with_errors_true(self):
        test_dict = {"errors": []}
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("top_level")
    def test_top_level_errors_as_dict_fails(self):
        test_dict = {"errors": {}}
        self.assertEqual(
            ["'Errors' object MUST be an array"],
            self.validator._validate_top_level(test_dict),
        )

    @tag("top_level")
    def test_top_level_with_data_and_errors_false(self):
        test_dict = {"data": self.valid_test_data_entry, "errors": []}
        self.assertEqual(
            [
                "Object of type 'Top-Level Object' MUST NOT contain both of ('data', 'errors')"
            ],
            self.validator._validate_top_level(test_dict),
        )

    # '''
    # A document MAY contain any of these top-level members:
    #
    # jsonapi: an object describing the server’s implementation
    # links: a links object related to the primary data.
    # included: an array of resource objects that are related to the primary data and/or each other (“included resources”).
    # If a document does not contain a top-level data key, the included member MUST NOT be present either.
    # '''

    @tag("top_level")
    def test_top_level_with_other_valid_keys(self):
        test_dict = {
            "data": self.valid_test_data_entry,
            "jsonapi": {},
            "links": {},
            "included": [],
        }
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("top_level")
    def test_top_level_with_invalid_keys(self):
        test_dict = {"data": self.valid_test_data_entry, "jsonvapi": {}}
        self.assertEqual(
            [
                "Object of type 'Top-Level Object' MUST NOT contain element of type 'jsonvapi'"
            ],
            self.validator._validate_top_level(test_dict),
        )

    @tag("top_level")
    def test_top_level_included_as_dict_fails_keys(self):
        test_dict = {"data": self.valid_test_data_entry, "included": {}}
        self.assertEqual(
            [
                "Object of type 'Resource Object' MUST contain element of type 'id'",
                "Object of type 'Resource Object' MUST contain element of type 'type'",
            ],
            self.validator._validate_top_level(test_dict),
        )

    @tag("top_level")
    def test_top_level_included_without_data_fails(self):
        test_dict = {"included": []}
        self.assertEqual(
            [
                "Object of type 'Top-Level Object' MUST contain one of ('data', 'errors', 'meta')"
            ],
            self.validator._validate_top_level(test_dict),
        )

    @tag("top_level")
    def test_top_level_included_must_contain_resource_objects(self):
        test_dict = {"data": self.valid_test_data_entry, "included": [{}]}
        self.assertEqual(
            [
                "Object of type 'Resource Object' MUST contain element of type 'id'",
                "Object of type 'Resource Object' MUST contain element of type 'type'",
            ],
            self.validator._validate_top_level(test_dict),
        )

    """
    The top-level links object MAY contain the following members:

    self: the link that generated the current response document.
    related: a related resource link when the primary data represents a resource relationship.
    pagination links for the primary data.
    """

    @tag("top_level", "links")
    def test_top_level_links_valid_keys(self):
        test_dict = {
            "data": self.valid_test_data_entry,
            "links": {
                "self": "http://stuff.com",
                "related": {"self": "http://stuff.com"},
                "first": "http://stuff.com",
                "last": "http://stuff.com",
                "prev": "http://stuff.com",
                "next": "http://stuff.com",
            },
        }
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("top_level", "links")
    def test_top_level_links_invalid_keys(self):
        self.maxDiff = None
        test_dict = {
            "data": self.valid_test_data_entry,
            "links": {
                "blurgh": "",
                "related": {"self": "http://stuff.com"},
                "first": "http://stuff.com",
                "last": "http://stuff.com",
                "prev": "http://stuff.com",
                "next": "http://stuff.com",
            },
        }
        self.assertEqual(
            [
                "Object of type 'Top-Level Links Object' MUST NOT contain element of type 'blurgh'"
            ],
            self.validator._validate_top_level(test_dict),
        )

    @tag("links")
    def test_self_link_is_valid_link(self):
        test_dict = {
            "data": self.valid_test_data_entry,
            "links": {"self": "http://stuffandthings.com"},
        }
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("links")
    def test_top_level_links_invalid_keys_2(self):
        test_dict = {"data": self.valid_test_data_entry, "links": {"bunk": ""}}
        self.assertEqual(
            [
                "Object of type 'Top-Level Links Object' MUST NOT contain element of type 'bunk'"
            ],
            self.validator._validate_top_level(test_dict),
        )

    @tag("primary_data_element")
    def test_validate_primary_data_element_fails_with_empty_dict(self):
        self.assertEqual(
            [
                "Primary data MUST be either: a single resource object, "
                "a single resource identifier object, or null, "
                "for requests that target single resources, "
                "an array of resource objects, "
                "an array of resource identifier objects, "
                "or an empty array ([]), "
                "for requests that target resource collections"
            ],
            self.validator._validate_primary_data_element({}),
        )

    @tag("resource_object")
    def test_validate_resource_object(self):
        """
        http://jsonapi.org/format/#document-resource-objects

        Resource Objects
        “Resource objects” appear in a JSON API document to represent resources.

        A resource object MUST contain at least the following top-level members:

        id
        type
        Exception: The id member is not required when the resource object originates at the client and represents a new resource to be created on the server.

        In addition, a resource object MAY contain any of these top-level members:

        attributes: an attributes object representing some of the resource’s data.
        relationships: a relationships object describing relationships between the resource and other JSON API resources.
        links: a links object containing links related to the resource.
        meta: a meta object containing non-standard meta-information about a resource that can not be represented as an attribute or relationship.
        :param data_dict:
        :return:
        """
        test_resource = {
            "type": "test_type",
            "id": "test_id",
            "attributes": {"test_attribute_type": "test_attribute_value"},
            "relationships": self.valid_relationships_entry,
            "links": {"self": "http://dead.net"},
            "meta": "test_meta",
        }
        self.assertEqual([], self.validator._validate_resource_object(test_resource))

    @tag("resource_object")
    def test_validate_resource_object_fails_without_id(self):
        test_resource = {
            "type": "test_type",
            "attributes": {"test_attribute_type": "test_attribute_value"},
            "relationships": self.valid_relationships_entry,
            "links": {"self": "http://dead.net"},
            "meta": "test_meta",
        }
        self.assertEqual(
            ["Object of type 'Resource Object' MUST contain element of type 'id'"],
            self.validator._validate_resource_object(test_resource),
        )

    @tag("resource_object")
    def test_validate_resource_object_fails_without_type(self):
        test_resource = {
            "id": "test_id",
            "attributes": {"test_attribute_type": "test_attribute_value"},
            "relationships": self.valid_relationships_entry,
            "links": {"self": "http://dead.net"},
            "meta": "test_meta",
        }
        self.assertEqual(
            ["Object of type 'Resource Object' MUST contain element of type 'type'"],
            self.validator._validate_resource_object(test_resource),
        )

    @tag("resource_object")
    def test_validate_resource_object_fails_with_bad_attributes(self):
        test_resource = {
            "type": "test_type",
            "id": "test_id",
            "attributes": {},
            "relationships": self.valid_relationships_entry,
            "links": {"self": "http://dead.net"},
            "meta": "test_meta",
        }
        self.assertEqual(
            ["Object of type 'Attributes Object' must not be empty"],
            self.validator._validate_resource_object(test_resource),
        )

    @tag("resource_object")
    def test_validate_resource_object_fails_with_bad_relationships(self):
        test_resource = {
            "type": "test_type",
            "id": "test_id",
            "attributes": {"test_attribute_type": "test_attribute_value"},
            "relationships": {"related_type": {"something": "silly"}},
            "links": {"self": "http://dead.net"},
            "meta": "test_meta",
        }
        self.assertEqual(
            [
                "Object of type 'Resource Object Relationship' MUST contain one of ('links', 'self', 'related', 'data', 'meta')"
            ],
            self.validator._validate_resource_object(test_resource),
        )

    @tag("resource_identifier_object")
    def test_validate_resource_identifier_objects(self):
        test_resource_identifier = [
            {"type": "test_type", "id": "test_id", "meta": "test_meta"}
        ]
        self.assertEqual(
            [],
            self.validator._validate_resource_identifier_objects(
                test_resource_identifier
            ),
        )

    @tag("resource_identifier_object")
    def test_validate_resource_identifier_object(self):
        """
        http://jsonapi.org/format/#document-resource-identifier-objects

        Resource Identifier Objects
        A “resource identifier object” is an object that identifies an individual resource.

        A “resource identifier object” MUST contain type and id members.

        A “resource identifier object” MAY also include a meta member, whose value is a meta object that contains
        non-standard meta-information.
        :param data_dict:
        :return:
        """
        test_resource_identifier = {
            "type": "test_type",
            "id": "test_id",
            "meta": "test_meta",
        }
        self.assertEqual(
            [],
            self.validator._validate_resource_identifier_object(
                test_resource_identifier
            ),
        )

    @tag("resource_identifier_object")
    def test_validate_resource_identifier_object_without_type_fails(self):
        test_resource_identifier = {"id": "test_id", "meta": "test_meta"}
        self.assertEqual(
            [
                "Object of type 'Resource Identifier Object' MUST contain element of type 'type'"
            ],
            self.validator._validate_resource_identifier_object(
                test_resource_identifier
            ),
        )

    @tag("resource_identifier_object")
    def test_validate_resource_identifier_object_without_id_fails(self):
        test_resource_identifier = {"type": "test_type", "meta": "test_meta"}
        self.assertEqual(
            [
                "Object of type 'Resource Identifier Object' MUST contain element of type 'id'"
            ],
            self.validator._validate_resource_identifier_object(
                test_resource_identifier
            ),
        )

    @tag("resource_identifier_object")
    def test_validate_resource_identifier_object_without_meta_passes(self):
        test_resource_identifier = {"type": "test_type", "id": "test_id"}
        self.assertEqual(
            [],
            self.validator._validate_resource_identifier_object(
                test_resource_identifier
            ),
        )

    @tag("resource_identifier_object")
    def test_validate_resource_identifier_object_with_random_key_fails(self):
        test_resource_identifier = {
            "type": "test_type",
            "id": "test_id",
            "meta": "test_meta",
            "junk": "junk",
        }
        self.assertEqual(
            [
                "Object of type 'Resource Identifier Object' MUST NOT contain element of type 'junk'"
            ],
            self.validator._validate_resource_identifier_object(
                test_resource_identifier
            ),
        )

    @tag("resource_object_attributes")
    def test_validate_resource_object_attributes(self):
        """
        http://jsonapi.org/format/#document-resource-object-attributes

        Attributes
        The value of the attributes key MUST be an object (an “attributes object”). Members of the attributes object (“attributes”)
        represent information about the resource object in which it’s defined.

        Attributes may contain any valid JSON value.

        Complex data structures involving JSON objects and arrays are allowed as attribute values. However, any object
        that constitutes or is contained in an attribute MUST NOT contain a relationships or links member, as those
        members are reserved by this specification for future use.

        Although has-one foreign keys (e.g. author_id) are often stored internally alongside other information to be
        represented in a resource object, these keys SHOULD NOT appear as attributes.

        :param data_dict:
        :return:
        """
        test_attributes = {"stuff": ["things", "more things"], "things": "stuff"}
        self.assertEqual(
            [], self.validator._validate_resource_object_attributes(test_attributes)
        )

    @tag("resource_object_attributes")
    def test_validate_resource_object_attributes_with_relationships_fails(self):
        test_attributes = {"relationships": "stuff"}
        self.assertEqual(
            [
                "Object of type 'Attributes Object' MUST NOT contain element of type 'relationships'"
            ],
            self.validator._validate_resource_object_attributes(test_attributes),
        )

    @tag("resource_object_attributes")
    def test_validate_resource_object_attributes_with_links_fails(self):
        test_attributes = {"links": "stuff"}
        self.assertEqual(
            [
                "Object of type 'Attributes Object' MUST NOT contain element of type 'links'"
            ],
            self.validator._validate_resource_object_attributes(test_attributes),
        )

    """
    http://jsonapi.org/format/#document-resource-object-relationships
    Relationships
    The value of the relationships key MUST be an object (a “relationships object”). Members of the relationships object (“relationships”) represent
    references from the resource object in which it’s defined to other resource objects.

    Relationships may be to-one or to-many.

    A “relationship object” MUST contain at least one of the following:

    links: a links object containing at least one of the following:
        self: a link for the relationship itself (a “relationship link”). This link allows the client to directly manipulate the relationship. For example,
            removing an author through an article’s relationship URL would disconnect the person from the article without deleting the people resource itself.
            When fetched successfully, this link returns the linkage for the related resources as its primary data. (See Fetching Relationships.)
        related: a related resource link
    data: resource linkage
    meta: a meta object that contains non-standard meta-information about the relationship.

    A relationship object that represents a to-many relationship MAY also contain pagination links under the links member, as described below. Any
    pagination links in a relationship object MUST paginate the relationship data, not the related resources.

    Note: See fields and member names for more restrictions on this container.
    :param data_dict:
    :return:
    """

    @tag("resource_object_relationships")
    def test_validate_resource_object_relationships_valid(self):
        test_relationships = {
            "relationship_type_one": {"links": {"self": "http://dead.net"}},
            "relationship_type_two": {"links": {"self": "http://dead.net"}},
        }
        self.assertEqual(
            [],
            self.validator._validate_resource_object_relationships(test_relationships),
        )

    @tag("resource_object_relationships")
    def test_validate_resource_object_relationships_no_valid_keys(self):
        test_relationships = {
            "relationship_type_one": {"links": {"self": "http://dead.net"}},
            "relationship_type_two": {"links": {"boo": "http://dead.net"}},
        }
        self.assertEqual(
            ["Object of type 'Links Object' MUST contain one of ('self', 'related')"],
            self.validator._validate_resource_object_relationships(test_relationships),
        )

    @tag("resource_object_relationships")
    def test_validate_relationship_object_passes_with_single_relationship_object(self):
        test_relationships = {
            "relationship_type_one": {"links": {"self": "http://dead.net"}}
        }
        self.assertEqual(
            [],
            self.validator._validate_resource_object_relationships(test_relationships),
        )

    @tag("resource_object_relationships")
    def test_validate_relationship_object_passes_with_list_of_relationship_objects(
        self
    ):
        test_relationships = {
            "relationship_type_one": [
                {"links": {"self": "http://dead.net"}},
                {"links": {"self": "http://dead.net"}},
            ]
        }
        self.assertEqual(
            [],
            self.validator._validate_resource_object_relationships(test_relationships),
        )

    @tag("resource_object_relationship")
    def test_validate_relationship_object_passes_with_only_links(self):
        test_relationship_object = {"links": self.valid_link_object}
        self.assertEqual(
            [],
            self.validator._validate_resource_object_relationship(
                test_relationship_object
            ),
        )

    @tag("resource_object_relationship")
    def test_validate_relationship_object_passes_with_only_data(self):
        test_relationship_object = {"data": []}
        self.assertEqual(
            [],
            self.validator._validate_resource_object_relationship(
                test_relationship_object
            ),
        )

    @tag("resource_object_relationship")
    def test_validate_relationship_object_passes_with_only_meta(self):
        test_relationship_object = {"meta": {}}
        self.assertEqual(
            [],
            self.validator._validate_resource_object_relationship(
                test_relationship_object
            ),
        )

    @tag("resource_object_relationship")
    def test_validate_relationship_object_fails_without_links_or_data_or_meta(self):
        test_relationship_object = {"blah": {}}
        self.assertEqual(
            [
                "Object of type 'Resource Object Relationship' MUST contain one of ('links', 'self', 'related', 'data', 'meta')"
            ],
            self.validator._validate_resource_object_relationship(
                test_relationship_object
            ),
        )

    @tag("resource_linkage")
    def test_validate_resource_linkage(self):
        errors = self.validator._validate_resource_linkage({"foo": "bar"})
        self.assertTrue(len(errors))

    @tag("resource_linkage")
    def test_validate_resource_linkage_passes_with_none(self):
        self.assertEqual([], self.validator._validate_resource_linkage(None))

    @tag("resource_linkage")
    def test_validate_resource_linkage_passes_with_empty_list(self):
        self.assertEqual([], self.validator._validate_resource_linkage([]))

    @tag("link_object")
    def test_validate_link_object_with_dict(self):
        link_dict = {"href": self.valid_url, "meta": "meta"}
        self.assertEqual([], self.validator._validate_link_object(link_dict))

    @tag("url")
    def test_validate_url_passes_with_good_url(self):
        self.assertEqual([], self.validator._validate_url("http://testserver"))

    @tag("url")
    def test_validate_url_None(self):
        self.assertEqual([], self.validator._validate_url(None))

    @tag("url")
    def test_validate_url_fails_with_bad_url(self):
        self.assertEqual(
            ["stuff is not a valid URL"], self.validator._validate_url("stuff")
        )

    @tag("errors_object")
    def test_validate_errors_object(self):
        self.assertEqual(
            [],
            self.validator._validate_errors_object(
                [{"id": "error_id"}, {"id": "error_id"}]
            ),
        )

    @tag("big")
    def test_one(self):
        test_dict = {
            "data": [
                {
                    "type": "user",
                    "id": None,
                    "attributes": {
                        "first_name": "string",
                        "last_name": "string",
                        "email": "user@example.com",
                        "is_active": True,
                        "is_superuser": True,
                        "created_at": "2018-05-01T23:37:19Z",
                        "modified_at": "2018-05-01T23:37:19Z",
                        "last_seen": "2018-05-01",
                    },
                }
            ]
        }
        self.assertEqual([], self.validator._validate_top_level(test_dict))

    @tag("member_names")
    def test_validate_member_names(self):
        """
        http://jsonapi.org/format/#document-member-names

        Member Names
        All member names used in a JSON API document MUST be treated as case sensitive by clients and servers, and they MUST meet all of the following
        conditions:

        Member names MUST contain at least one character.
        Member names MUST contain only the allowed characters listed below.
        Member names MUST start and end with a “globally allowed character”, as defined below.
        To enable an easy mapping of member names to URLs, it is RECOMMENDED that member names use only non-reserved, URL safe characters specified in RFC 3986.

        ========================================================================================================================================================
        ========================================================================================================================================================

        Allowed Characters
        The following “globally allowed characters” MAY be used anywhere in a member name:

        U+0061 to U+007A, “a-z”
        U+0041 to U+005A, “A-Z”
        U+0030 to U+0039, “0-9”
        U+0080 and above (non-ASCII Unicode characters; not recommended, not URL safe)

        Additionally, the following characters are allowed in member names, except as the first or last character:

        U+002D HYPHEN-MINUS, “-“
        U+005F LOW LINE, “_”
        U+0020 SPACE, “ “ (not recommended, not URL safe)

        ========================================================================================================================================================
        ========================================================================================================================================================

        Reserved Characters
        The following characters MUST NOT be used in member names:

        U+002B PLUS SIGN, “+” (used for ordering)
        U+002C COMMA, “,” (used as a separator between relationship paths)
        U+002E PERIOD, “.” (used as a separator within relationship paths)
        U+005B LEFT SQUARE BRACKET, “[” (used in sparse fieldsets)
        U+005D RIGHT SQUARE BRACKET, “]” (used in sparse fieldsets)
        U+0021 EXCLAMATION MARK, “!”
        U+0022 QUOTATION MARK, ‘”’
        U+0023 NUMBER SIGN, “#”
        U+0024 DOLLAR SIGN, “$”
        U+0025 PERCENT SIGN, “%”
        U+0026 AMPERSAND, “&”
        U+0027 APOSTROPHE, “’”
        U+0028 LEFT PARENTHESIS, “(“
        U+0029 RIGHT PARENTHESIS, “)”
        U+002A ASTERISK, “*”
        U+002F SOLIDUS, “/”
        U+003A COLON, “:”
        U+003B SEMICOLON, “;”
        U+003C LESS-THAN SIGN, “<”
        U+003D EQUALS SIGN, “=”
        U+003E GREATER-THAN SIGN, “>”
        U+003F QUESTION MARK, “?”
        U+0040 COMMERCIAL AT, “@”
        U+005C REVERSE SOLIDUS, “\”
        U+005E CIRCUMFLEX ACCENT, “^”
        U+0060 GRAVE ACCENT, “`”
        U+007B LEFT CURLY BRACKET, “{“
        U+007C VERTICAL LINE, “|”
        U+007D RIGHT CURLY BRACKET, “}”
        U+007E TILDE, “~”
        U+007F DELETE
        U+0000 to U+001F (C0 Controls)

        """
        self.assertEqual([], self.validator._validate_member_names({"stuff": "things"}))

    @tag("member_names")
    def test_validate_member_names_fails_with_sub_element(self):
        self.assertEqual(
            ["<empty_string> is not a valid Member Name"],
            self.validator._validate_member_names({"stuff": {"": "things"}}),
        )

    @tag("member_names")
    def test_validate_member_names_fails_with_empty_string(self):
        self.assertEqual(
            ["<empty_string> is not a valid Member Name"],
            self.validator._validate_member_names({"": "things"}),
        )

    @tag("member_names")
    def test_validate_member_names_fails_with_disallowed_first_character(self):
        self.assertEqual(
            ["'_' is not a valid boundary character in a Member Name"],
            self.validator._validate_member_names({"_stuff": "things"}),
        )

    @tag("member_names")
    def test_validate_member_names_fails_with_disallowed_last_character(self):
        self.assertEqual(
            ["'-' is not a valid boundary character in a Member Name"],
            self.validator._validate_member_names({"stuff-": "things"}),
        )

    @tag("member_names")
    def test_validate_member_names_fails_with_disallowed_boundary_character(self):
        self.assertEqual(
            ["' ' is not a valid boundary character in a Member Name"],
            self.validator._validate_member_names({"stuff ": "things"}),
        )

    @tag("member_names")
    def test_validate_member_names_fails_with_plus_sign(self):
        self.assertEqual(
            ["'+' is not a valid character in a Member Name"],
            self.validator._validate_member_names({"stuff+": "things"}),
        )

    @tag("member_names")
    def test_invalid_chars(self):
        invalid_chars = [
            "\u002b",  # PLUS SIGN, “+” (used for ordering)
            "\u002c",  # COMMA, “,” (used as a separator between relationship paths)
            "\u002e",  # PERIOD, “.” (used as a separator within relationship paths)
            "\u005b",  # LEFT SQUARE BRACKET, “[” (used in sparse fieldsets)
            "\u005d",  # RIGHT SQUARE BRACKET, “]” (used in sparse fieldsets)
            "\u0021",  # EXCLAMATION MARK, “!”
            "\u0022",  # QUOTATION MARK, ‘”’
            "\u0023",  # NUMBER SIGN, “#”
            "\u0024",  # DOLLAR SIGN, “$”
            "\u0025",  # PERCENT SIGN, “%”
            "\u0026",  # AMPERSAND, “&”
            "\u0027",  # APOSTROPHE, “’”
            "\u0028",  # LEFT PARENTHESIS, “(“
            "\u0029",  # RIGHT PARENTHESIS, “)”
            "\u002a",  # ASTERISK, “*”
            "\u002f",  # SOLIDUS, “/”
            "\u003a",  # COLON, “:”
            "\u003b",  # SEMICOLON, “;”
            "\u003c",  # LESS-THAN SIGN, “<”
            "\u003d",  # EQUALS SIGN, “=”
            "\u003e",  # GREATER-THAN SIGN, “>”
            "\u003f",  # QUESTION MARK, “?”
            "\u0040",  # COMMERCIAL AT, “@”
            "\u005c",  # REVERSE SOLIDUS, “\”
            "\u005e",  # CIRCUMFLEX ACCENT, “^”
            "\u0060",  # GRAVE ACCENT, “`”
            "\u007b",  # LEFT CURLY BRACKET, “{“
            "\u007c",  # VERTICAL LINE, “|”
            "\u007d",  # RIGHT CURLY BRACKET, “}”
            "\u007e",  # TILDE, “~”
            "\u007f",  # DELETE
            "\u0000",  # C0 control
            "\u0001",  # C0 control
            "\u0002",  # C0 control
            "\u0003",  # C0 control
            "\u0004",  # C0 control
            "\u0005",  # C0 control
            "\u0006",  # C0 control
            "\u0007",  # C0 control
            "\u0008",  # C0 control
            "\u0009",  # C0 control
            "\u000a",  # C0 control
            "\u000b",  # C0 control
            "\u000c",  # C0 control
            "\u000d",  # C0 control
            "\u000e",  # C0 control
            "\u000f",  # C0 control
            "\u0010",  # C0 control
            "\u0011",  # C0 control
            "\u0012",  # C0 control
            "\u0013",  # C0 control
            "\u0014",  # C0 control
            "\u0015",  # C0 control
            "\u0016",  # C0 control
            "\u0017",  # C0 control
            "\u0018",  # C0 control
            "\u0019",  # C0 control
            "\u001a",  # C0 control
            "\u001b",  # C0 control
            "\u001c",  # C0 control
            "\u001d",  # C0 control
            "\u001e",  # C0 control
            "\u001f",  # C0 control
        ]
        for char in invalid_chars:
            self.assertEqual(
                ["'{}' is not a valid character in a Member Name".format(char)],
                self.validator._validate_member_names(
                    {"stuff{}".format(char): "things"}
                ),
            )
