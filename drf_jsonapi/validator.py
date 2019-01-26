import re
from django.core.validators import URLValidator as DjangoURLValidator
from django.core.validators import _lazy_re_compile, _
from django.core.exceptions import ValidationError
from rest_framework.response import Response


class URLValidator(DjangoURLValidator):
    """
    Set validation regex rules for URLs.
    """

    ul = "\u00a1-\uffff"  # unicode letters range (must not be a raw string)

    # IP patterns
    ipv4_re = (
        r"(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}"
    )
    ipv6_re = r"\[[0-9a-f:\.]+\]"  # (simple regex, validated later)

    # Host patterns
    hostname_re = (
        r"[a-z" + ul + r"0-9](?:[a-z" + ul + r"0-9-]{0,61}[a-z" + ul + r"0-9])?"
    )
    # Max length for domain name labels is 63 characters per RFC 1034 sec. 3.1
    domain_re = r"(?:\.(?!-)[a-z" + ul + r"0-9-]{1,63}(?<!-))*"
    tld_re = (
        r"\."  # dot
        r"(?!-)"  # can't start with a dash
        r"(?:[a-z" + ul + "-]{2,63}"  # domain label
        r"|xn--[a-z0-9]{1,59})"  # or punycode label
        r"(?<!-)"  # can't end with a dash
        r"\.?"  # may have a trailing dot
    )
    host_re = "(" + hostname_re + domain_re + tld_re + "|localhost|testserver)"

    regex = _lazy_re_compile(
        r"^(?:[a-z0-9\.\-\+]*)://"  # scheme is validated separately
        r"(?:\S+(?::\S*)?@)?"  # user:pass authentication
        r"(?:" + ipv4_re + "|" + ipv6_re + "|" + host_re + ")"
        r"(?::\d{2,5})?"  # port
        r"(?:[/?#][^\s]*)?"  # resource path
        r"\Z",
        re.IGNORECASE,
    )
    message = _("Enter a valid URL.")
    schemes = ["http", "https", "ftp", "ftps"]


class JsonApiValidator(object):
    """
    http://jsonapi.org/format/

    Latest Specification (v1.0)
    Status
    This page represents the latest published version of JSON API, which is currently version 1.0. New versions of JSON API will always be backwards compatible
    using a never remove, only add strategy. Additions can be proposed in our discussion forum.

    If you catch an error in the specification’s text, or if you write an implementation, please let us know by opening an issue or pull request at our GitHub
    repository.

    Introduction
    JSON API is a specification for how a client should request that resources be fetched or modified, and how a server should respond to those requests.

    JSON API is designed to minimize both the number of requests and the amount of data transmitted between clients and servers. This efficiency is achieved
    without compromising readability, flexibility, or discoverability.

    JSON API requires use of the JSON API media type (application/vnd.api+json) for exchanging data.

    Conventions
    The key words “MUST”, “MUST NOT”, “REQUIRED”, “SHALL”, “SHALL NOT”, “SHOULD”, “SHOULD NOT”, “RECOMMENDED”, “MAY”, and “OPTIONAL” in this document are to
    be interpreted as described in RFC 2119 [RFC2119].

    Content Negotiation
    Client Responsibilities
    Clients MUST send all JSON API data in request documents with the header Content-Type: application/vnd.api+json without any media type parameters.

    Clients that include the JSON API media type in their Accept header MUST specify the media type there at least once without any media type parameters.

    Clients MUST ignore any parameters for the application/vnd.api+json media type received in the Content-Type header of response documents.

    """

    VALID_HEADER = "application/vnd.api+json"

    def __init__(self):
        self.errors = []
        self.url_validator = URLValidator()

    def is_valid(self, response):
        self.errors = self._validate(response)
        return len(self.errors) == 0

    def _validate(self, response):
        """
        http://jsonapi.org/format/#content-negotiation-servers
        Server Responsibilities
        Servers MUST send all JSON API data in response documents with the header Content-Type: application/vnd.api+json without any media type parameters.

        Servers MUST respond with a 415 Unsupported Media Type status code if a request specifies the header Content-Type: application/vnd.api+json with any
        media type parameters.

        Servers MUST respond with a 406 Not Acceptable status code if a request’s Accept header contains the JSON API media type and all instances of that
        media type are modified with media type parameters.

        Note: The content negotiation requirements exist to allow future versions of this specification to use media type parameters for extension
        negotiation and versioning.
        ===============================================================================================================================
        http://jsonapi.org/format/#document-structure

        Document Structure
        This section describes the structure of a JSON API document, which is identified by the media type application/vnd.api+json. JSON API documents are
        defined in JavaScript Object Notation (JSON) [RFC7159].

        Although the same media type is used for both request and response documents, certain aspects are only applicable to one or the other. These
        differences are called out below.

        Unless otherwise noted, objects defined by this specification MUST NOT contain any additional members. Client and server implementations MUST
        ignore members not recognized by this specification.

        Note: These conditions allow this specification to evolve through additive changes.
        """

        errors = []

        if not isinstance(response, Response):
            errors.append("Response must be of type Response")
            return errors

        if not response.data and response.status_code != 204:
            errors.append(
                "A server MUST return 204 No Content status code when there is no response document"
            )
            return errors

        if not response.data:
            return errors

        errors.extend(self._validate_headers(response))
        errors.extend(self._validate_member_names(response.data))
        errors.extend(self._validate_top_level(response.json()))

        return errors

    def _validate_headers(self, response):
        """
        Servers MUST send all JSON API data in response documents with the header Content-Type: application/vnd.api+json without any media type parameters.

        :param JsonApiValidator self: This object
        :param rest_framework.response response:
        :return: An array of validation errors associated with incorrect headers
        :rtype: list
        """

        if response.status_code == 204:
            return []
        response.has_header("Content-Type")
        if not response.has_header("Content-Type"):
            return ["Non-empty Response MUST have 'Content-Type' header"]
        elif response["Content-Type"] != self.VALID_HEADER:
            return [
                "'Content-Type' header MUST be equal to '{}'".format(self.VALID_HEADER)
            ]
        return []

    def _validate_section(
        self,  # NOSONAR
        entity_name,
        data_dict,
        must_contain={},
        must_contain_one={},
        may_contain={},
        must_not_contain_both=[],
        must_not_contain=[],
    ):
        """
        Servers must send all JSON-API data with a correctly formatted structure.

        :param JsonApiValidator self: This object
        :param string entity_name:
        :param dict data_dict:
        :param list must_contain:
        :param list must_contain_one:
        :return: A list of validation messages
        :rtype: list
        """

        ret = []
        for key in [key for key in must_contain if key not in data_dict]:
            ret.append(
                "Object of type '{}' MUST contain element of type '{}'".format(
                    entity_name, key
                )
            )

        # verify that we have at least one of our must_contain_one
        if must_contain_one and set(must_contain_one) - set(data_dict) == set(
            must_contain_one
        ):
            ret.append(
                "Object of type '{}' MUST contain one of ({})".format(
                    entity_name,
                    ", ".join(["'{}'".format(key) for key in must_contain_one]),
                )
            )

        # verify that we have nothing that is not in may_contain
        if may_contain:
            for key in set(data_dict) - (
                set(may_contain) | set(must_contain) | set(must_contain_one)
            ):
                ret.append(
                    "Object of type '{}' MUST NOT contain element of type '{}'".format(
                        entity_name, key
                    )
                )

        # verify that we don't include two keys that can't appear together
        for [one, two] in must_not_contain_both:
            if one in data_dict and two in data_dict:
                ret.append(
                    "Object of type '{}' MUST NOT contain both of ('{}', '{}')".format(
                        entity_name, one, two
                    )
                )

        # verify that we don't have any strictly prohibited keys in our object
        for key in set(must_not_contain) & set(data_dict):
            ret.append(
                "Object of type '{}' MUST NOT contain element of type '{}'".format(
                    entity_name, key
                )
            )

        for key, validator in {
            **must_contain,
            **must_contain_one,
            **may_contain,
        }.items():
            if validator and key in data_dict:
                fxn = getattr(self, "_validate_{}".format(validator))
                ret.extend(fxn(data_dict[key]))

        return ret

    def _validate_top_level(self, data_dict):
        """
        http://jsonapi.org/format/#document-top-level

        Top Level
        A JSON object MUST be at the root of every JSON API request and response containing data. This object defines a document’s “top level”.

        A document MUST contain at least one of the following top-level members:

        data: the document’s “primary data”
        errors: an array of error objects
        meta: a meta object that contains non-standard meta-information.
        The members data and errors MUST NOT coexist in the same document.

        A document MAY contain any of these top-level members:

        jsonapi: an object describing the server’s implementation
        links: a links object related to the primary data.
        included: an array of resource objects that are related to the primary data and/or each other (“included resources”).
        If a document does not contain a top-level data key, the included member MUST NOT be present either.

        The top-level links object MAY contain the following members:

        self: the link that generated the current response document.
        related: a related resource link when the primary data represents a resource relationship.
        pagination links for the primary data.


        The document’s “primary data” is a representation of the resource or collection of resources targeted by a request.

        Primary data MUST be either:

        a single resource object, a single resource identifier object, or null, for requests that target single resources
        an array of resource objects, an array of resource identifier objects, or an empty array ([]), for requests that target resource collections
        For example, the following primary data is a single resource object:

        {
          "data": {
            "type": "articles",
            "id": "1",
            "attributes": {
              // ... this article's attributes
            },
            "relationships": {
              // ... this article's relationships
            }
          }
        }
        The following primary data is a single resource identifier object that references the same resource:

        {
          "data": {
            "type": "articles",
            "id": "1"
          }
        }
        A logical collection of resources MUST be represented as an array, even if it only contains one item or is empty.

        :param JsonApiValidator self: This object
        :param dict data_dict: The docuement's primary data
        :return: A list of validation messages
        :rtype: list
        """
        return self._validate_section(
            "Top-Level Object",
            data_dict,
            must_contain_one={
                "data": "primary_data_element",
                "errors": "errors_object",
                "meta": None,
            },
            may_contain={
                "jsonapi": "jsonapi_object",
                "links": "top_level_links_object",
                "included": "resource_objects",
            },
            must_not_contain_both=[["data", "errors"]],
        )

    def _validate_primary_data_element(self, data_element):
        """
        Primary data MUST be either:

            a single resource object, a single resource identifier object, or null, for requests that target single resources
            an array of resource objects, an array of resource identifier objects, or an empty array ([]), for requests that target resource collections

        For example, the following primary data is a single resource object:

        {
          "data": {
            "type": "articles",
            "id": "1",
            "attributes": {
              // ... this article's attributes
            },
            "relationships": {
              // ... this article's relationships
            }
          }
        }
        The following primary data is a single resource identifier object that references the same resource:

        {
          "data": {
            "type": "articles",
            "id": "1"
          }
        }
        A logical collection of resources MUST be represented as an array, even if it only contains one item or is empty.

        :param data_element: An empty data element, a list of elements, or a single data object
        :return: A list of validation messages
        :rtype: list
        """

        ret = []
        if data_element == [] or data_element is None:
            return ret

        if not self._validate_resource_objects(
            data_list=data_element
        ) or not self._validate_resource_identifier_objects(data_list=data_element):
            # If we get back [] from _validate_resource_objects OR from _validate_resource_identifier_objects,
            # we know that we have a list of resource_objects or a list of resource_identifier_objects,
            # which means we have a valid primary_data_element
            return ret
        # Otherwise we just return the general erro, because we don't know which one they were trying for
        ret.extend(
            [
                "Primary data MUST be either: "
                "a single resource object, "
                "a single resource identifier object, "
                "or null, for requests that target single "
                "resources, "
                "an array of resource objects, "
                "an array of resource identifier objects, "
                "or an empty array ([]), for requests that target resource collections"
            ]
        )
        return ret

    def _validate_top_level_links_object(self, data_dict):
        """
        Validate top level links object, ensuring it only contains valid keys and link objects.

        :param JsonApiValidator self: This object
        :param dict data_dict: The docuement's primary data
        :return: A list of validation messages
        :rtype: list
        """

        return self._validate_section(
            entity_name="Top-Level Links Object",
            data_dict=data_dict,
            may_contain={
                "self": "link_object",
                "related": "links_object",
                "first": "link_object",
                "next": "link_object",
                "prev": "link_object",
                "last": "link_object",
            },
        )

    def _validate_resource_objects(self, data_list):
        """
        Validate that this is a list of resource objects.

        :param JsonApiValidator self: This object
        :param dict data_list: The docuement's primary data
        :return: A list of validation messages
        :rtype: list
        """

        if not isinstance(data_list, list):
            data_list = [data_list]
        ret = []
        for object_dict in data_list:
            ret.extend(self._validate_resource_object(data_dict=object_dict))
        return ret

    def _validate_resource_object(self, data_dict):
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
        Here’s how an article (i.e. a resource of type “articles”) might appear in a document:

        // ...
        {
          "type": "articles",
          "id": "1",
          "attributes": {
            "title": "Rails is Omakase"
          },
          "relationships": {
            "author": {
              "links": {
                "self": "/articles/1/relationships/author",
                "related": "/articles/1/author"
              },
              "data": { "type": "people", "id": "9" }
            }
          }
        }
        // ...

        Identification
        Every resource object MUST contain an id member and a type member. The values of the id and type members MUST be strings.

        Within a given API, each resource object’s type and id pair MUST identify a single, unique resource. (The set of URIs controlled by a server,
        or multiple servers acting as one, constitute an API.)

        The type member is used to describe resource objects that share common attributes and relationships.

        The values of type members MUST adhere to the same constraints as member names.

        Note: This spec is agnostic about inflection rules, so the value of type can be either plural or singular. However, the same value should be used
        consistently throughout an implementation.

        Fields
        A resource object’s attributes and its relationships are collectively called its “fields”.

        Fields for a resource object MUST share a common namespace with each other and with type and id. In other words, a resource can not have an attribute
        and relationship with the same name, nor can it have an attribute or relationship named type or id.

        :param JsonApiValidator self: This object
        :param dict data_dict: A dictionary representing a JSON-API data resource object
        :return: A list of validation messages
        :rtype: list
        """

        return self._validate_section(
            entity_name="Resource Object",
            data_dict=data_dict,
            must_contain={"id": None, "type": None},
            may_contain={
                "attributes": "resource_object_attributes",
                "relationships": "resource_object_relationships",
                "links": "links_object",
                "meta": "meta",
            },
        )

    def _validate_resource_object_attributes(self, data_dict):
        """
        http://jsonapi.org/format/#document-resource-object-attributes

        Attributes
        The value of the attributes key MUST be an object (an “attributes object”). Members of the attributes object (“attributes”) represent information
        about the resource object in which it’s defined.

        Attributes may contain any valid JSON value.

        Complex data structures involving JSON objects and arrays are allowed as attribute values. However, any object that constitutes or is contained in
        an attribute MUST NOT contain a relationships or links member, as those members are reserved by this specification for future use.

        Although has-one foreign keys (e.g. author_id) are often stored internally alongside other information to be represented in a resource object, these
        keys SHOULD NOT appear as attributes.

        Note: See fields and member names for more restrictions on this container.

        :param JsonApiValidator self: This object
        :param dict data_dict: The docuement's attribute data
        :return: A list of validation messages
        :rtype: list
        """

        if not isinstance(data_dict, dict) or data_dict == {}:
            return ["Object of type 'Attributes Object' must not be empty"]
        return self._validate_section(
            entity_name="Attributes Object",
            data_dict=data_dict,
            must_not_contain=["relationships", "links"],
        )

    def _validate_resource_object_relationships(self, data_dict):
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

        :param JsonApiValidator self: This object
        :param dict data_dict: The document's list of resource object relationships
        :return: A list of validation messages
        :rtype: list
        """
        errors = []
        for key, data_list in data_dict.items():
            if not isinstance(data_list, list):
                data_list = [data_list]
            for element in data_list:
                errors.extend(self._validate_resource_object_relationship(element))
        return errors

    def _validate_resource_object_relationship(self, data_dict):
        """
        Validate a single Resource Object Relationship
        (as opposed to a list of them, which is handled in
        _validate_resource_object_relationships())

        :param dict data_dict: The document's attribute data
        :return: A list of validation messages
        :rtype: list
        """
        return self._validate_section(
            entity_name="Resource Object Relationship",
            data_dict=data_dict,
            must_contain_one={
                "links": "links_object",
                "self": "link_object",
                "related": "url",
                "data": "resource_linkage",
                "meta": "meta",
            },
        )

    def _validate_resource_linkage(self, data_dict):
        """
        http://jsonapi.org/format/#document-resource-object-linkage

        Resource Linkage
        Resource linkage in a compound document allows a client to link together all of the included resource objects without having to GET any URLs via links.

        Resource linkage MUST be represented as one of the following:

            null for empty to-one relationships.
            an empty array ([]) for empty to-many relationships.
            a single resource identifier object for non-empty to-one relationships.
            an array of resource identifier objects for non-empty to-many relationships.
            Note: The spec does not impart meaning to order of resource identifier objects in linkage arrays of to-many relationships, although
            implementations may do that. Arrays of resource identifier objects may represent ordered or unordered relationships, and both types can be
            mixed in one response object.

        For example, the following article is associated with an author:

        // ...
        {
          "type": "articles",
          "id": "1",
          "attributes": {
            "title": "Rails is Omakase"
          },
          "relationships": {
            "author": {
              "links": {
                "self": "http://example.com/articles/1/relationships/author",
                "related": "http://example.com/articles/1/author"
              },
              "data": { "type": "people", "id": "9" }
            }
          },
          "links": {
            "self": "http://example.com/articles/1"
          }
        }
        // ...
        The author relationship includes a link for the relationship itself (which allows the client to change the related author directly), a related
        resource link to fetch the resource objects, and linkage information.

        :param JsonApiValidator self: This object
        :param dict data_dict: The document's relationships links
        :return: A list of validation messages
        :rtype: list
        """
        if data_dict is None or data_dict == []:
            return []
        return self._validate_resource_identifier_objects(data_dict)

    def _validate_resource_identifier_objects(self, data_list):
        """
        http://jsonapi.org/format/#document-resource-identifier-objects

        Resource Identifier Objects
        A “resource identifier object” is an object that identifies an individual resource.

        A “resource identifier object” MUST contain type and id members.

        A “resource identifier object” MAY also include a meta member, whose value is a meta object that contains non-standard meta-information.

        :param JsonApiValidator self: This object
        :param dict data_list: The document's list of resource identifier objects
        :return: A list of validation messages
        :rtype: list
        """
        if not isinstance(data_list, list):
            data_list = [data_list]
        for element in data_list:
            ret = self._validate_resource_identifier_object(element)
            if ret:
                return ret
        return []

    def _validate_resource_identifier_object(self, data_dict):
        """
        Validate a single Resource Identifier Relationship
        (as opposed to a list of them, which is handled in
        _validate_resource_identifier_objects())

        :param dict data_dict: The document's attribute data
        :return: A list of validation messages
        :rtype: list
        """
        return self._validate_section(
            entity_name="Resource Identifier Object",
            data_dict=data_dict,
            must_contain={"type": None, "id": None},
            may_contain={"meta": "meta"},
        )

    def _validate_meta(self, data_dict):
        """
        http://jsonapi.org/format/#document-meta

        Meta Information
        Where specified, a meta member can be used to include non-standard meta-information. The value of each meta member MUST be an object (a “meta object”).

        Any members MAY be specified within meta objects.

        For example:

        {
          "meta": {
            "copyright": "Copyright 2015 Example Corp.",
            "authors": [
              "Yehuda Katz",
              "Steve Klabnik",
              "Dan Gebhardt",
              "Tyler Kellen"
            ]
          },
          "data": {
            // ...
          }
        }

        :param JsonApiValidator self: This object
        :param dict data_dict: The document's meta object
        :return: A list of validation messages
        :rtype: list
        """

        return []

    def _validate_links_object(self, data_dict, links_exist=False):
        """
        http://jsonapi.org/format/#document-links

        Links
        Where specified, a links member can be used to represent links. The value of each links member MUST be an object (a “links object”).

        Each member of a links object is a “link”. A link MUST be represented as either:

        a string containing the link’s URL.
        an object (“link object”) which can contain the following members:
            href: a string containing the link’s URL.
            meta: a meta object containing non-standard meta-information about the link.
        The following self link is simply a URL:

        "links": {
          "self": "http://example.com/posts"
        }
        The following related link includes a URL as well as meta-information about a related resource collection:

        "links": {
          "related": {
            "href": "http://example.com/articles/1/comments",
            "meta": {
              "count": 10
            }
          }
        }
        Note: Additional members may be specified for links objects and link objects in the future. It is also possible that the allowed values of additional
        members will be expanded (e.g. a collection link may support an array of values, whereas a self link does not).


        :param JsonApiValidator self: This object
        :param dict data_dict: The document's links object
        :return: A list of validation messages
        :rtype: list
        """

        return self._validate_section(
            entity_name="Links Object",
            data_dict=data_dict,
            must_contain_one={"self": "url", "related": "link_object"},
        )

    def _validate_link_object(self, data):
        """
        Validate a links object.

        :param JsonApiValidator self: This object
        :param dict data: The links object
        :return: A list of validation messages
        :rtype: list
        """

        if isinstance(data, dict):
            return self._validate_section(
                entity_name="Link Object",
                data_dict=data,
                may_contain={"href": "url", "meta": "meta"},
            )
        return self._validate_url(data)

    def _validate_url(self, url):
        """
        Validate a URL strubg.

        :param JsonApiValidator self: This object
        :param string url: The URL to validate
        :return: A list of validation messages
        :rtype: list
        """

        if url is None or url == "None":
            return []
        try:
            self.url_validator(url)
        except ValidationError as e:
            return ["{} is not a valid URL".format(url)]
        return []

    def _validate_jsonapi_object(self, data_dict):
        """
        http://jsonapi.org/format/#document-jsonapi-object

        JSON API Object
        A JSON API document MAY include information about its implementation under a top level jsonapi member. If present, the value of the jsonapi member
        MUST be an object (a “jsonapi object”). The jsonapi object MAY contain a version member whose value is a string indicating the
        highest JSON API version supported. This object MAY also contain a meta member, whose value is a meta object that contains
        non-standard meta-information.

        {
          "jsonapi": {
            "version": "1.0"
          }
        }
        If the version member is not present, clients should assume the server implements at least version 1.0 of the specification.

        Note: Because JSON API is committed to making additive changes only, the version string primarily indicates which new features a server may support.

        :param JsonApiValidator self: This object
        :param dict url: The document's jsonapi object
        :return: A list of validation messages
        :rtype: list
        """

        return self._validate_section(
            entity_name="Error Object",
            data_dict=data_dict,
            may_contain={"version": None},
        )

    def _validate_errors_object(self, data_list):
        """
        Validate that this is an list of error_objects.

        :param JsonApiValidator self: This object
        :param list data_list: The document's errors object
        :return: A list of validation messages
        :rtype: list
        """

        if not isinstance(data_list, list):
            return ["'Errors' object MUST be an array"]
        ret = []
        for error_dict in data_list:
            ret.extend(self._validate_error_object(error_dict))
        return ret

    def _validate_error_object(self, data_dict):
        """
        http://jsonapi.org/format/#error-objects

        Errors
        Processing Errors
        A server MAY choose to stop processing as soon as a problem is encountered, or it MAY continue processing and encounter multiple problems. For
        instance, a server might process multiple attributes and then return multiple validation problems in a single response.

        When a server encounters multiple problems for a single request, the most generally applicable HTTP error code SHOULD be used in the response. For
        instance, 400 Bad Request might be appropriate for multiple 4xx errors or 500 Internal Server Error might be appropriate for multiple 5xx errors.

        Error Objects
        Error objects provide additional information about problems encountered while performing an operation. Error objects MUST be returned as an array
        keyed by 'errors' in the top level of a JSON API document.

        An error object MAY have the following members:

            id: a unique identifier for this particular occurrence of the problem.
            links: a links object containing the following members:
            about: a link that leads to further details about this particular occurrence of the problem.
            status: the HTTP status code applicable to this problem, expressed as a string value.
            code: an application-specific error code, expressed as a string value.
            title: a short, human-readable summary of the problem that SHOULD NOT change from occurrence to occurrence of the problem, except for purposes of
                localization.
            detail: a human-readable explanation specific to this occurrence of the problem. Like title, this field’s value can be localized.
            source: an object containing references to the source of the error, optionally including any of the following members:
            pointer: a JSON Pointer [RFC6901] to the associated entity in the request document [e.g. "/data" for a primary data object, or
                "/data/attributes/title" for a specific attribute].
            parameter: a string indicating which URI query parameter caused the error.
            meta: a meta object containing non-standard meta-information about the error.

        :param JsonApiValidator self: This object
        :param list data_doct: An errors dictionary
        :return: A list of validation messages
        :rtype: list
        """

        return self._validate_section(
            entity_name="Error Object",
            data_dict=data_dict,
            may_contain={
                "id": None,
                "links": "links_object",
                "about": None,
                "status": None,
                "code": None,
                "title": None,
                "detail": None,
                "source": None,
                "pointer": None,
                "parameter": None,
                "meta": None,
            },
        )

    def _validate_member_names(self, data_dict):
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

        :param JsonApiValidator self: This object
        :param list data_doct: An errors dictionary
        :return: A list of validation messages
        :rtype: list
        """

        disallowed_boundary_chars = [
            0x002D,  # HYPHEN - MINUS, “-“
            0x005F,  # LOW LINE, “_”
            0x0020,  # SPACE, “ “ (not recommended, not URL safe)
        ]

        disallowed_chars = [
            0x002B,  # PLUS SIGN, “+” (used for ordering)
            0x002C,  # COMMA, “,” (used as a separator between relationship paths)
            0x002E,  # PERIOD, “.” (used as a separator within relationship paths)
            0x005B,  # LEFT SQUARE BRACKET, “[” (used in sparse fieldsets)
            0x005D,  # RIGHT SQUARE BRACKET, “]” (used in sparse fieldsets)
            0x0021,  # EXCLAMATION MARK, “!”
            0x0022,  # QUOTATION MARK, ‘”’
            0x0023,  # NUMBER SIGN, “#”
            0x0024,  # DOLLAR SIGN, “$”
            0x0025,  # PERCENT SIGN, “%”
            0x0026,  # AMPERSAND, “&”
            0x0027,  # APOSTROPHE, “’”
            0x0028,  # LEFT PARENTHESIS, “(“
            0x0029,  # RIGHT PARENTHESIS, “)”
            0x002A,  # ASTERISK, “*”
            0x002F,  # SOLIDUS, “/”
            0x003A,  # COLON, “:”
            0x003B,  # SEMICOLON, “;”
            0x003C,  # LESS-THAN SIGN, “<”
            0x003D,  # EQUALS SIGN, “=”
            0x003E,  # GREATER-THAN SIGN, “>”
            0x003F,  # QUESTION MARK, “?”
            0x0040,  # COMMERCIAL AT, “@”
            0x005C,  # REVERSE SOLIDUS, “\”
            0x005E,  # CIRCUMFLEX ACCENT, “^”
            0x0060,  # GRAVE ACCENT, “`”
            0x007B,  # LEFT CURLY BRACKET, “{“
            0x007C,  # VERTICAL LINE, “|”
            0x007D,  # RIGHT CURLY BRACKET, “}”
            0x007E,  # TILDE, “~”
            0x007F,  # DELETE
            0x0000,  # to U+001F (C0 Controls)
            0x0001,  # (C0 Controls)
            0x0002,  # (C0 Controls)
            0x0003,  # (C0 Controls)
            0x0004,  # (C0 Controls)
            0x0005,  # (C0 Controls)
            0x0006,  # (C0 Controls)
            0x0007,  # (C0 Controls)
            0x0008,  # (C0 Controls)
            0x0009,  # (C0 Controls)
            0x000A,  # (C0 Controls)
            0x000B,  # (C0 Controls)
            0x000C,  # (C0 Controls)
            0x000D,  # (C0 Controls)
            0x000E,  # (C0 Controls)
            0x000F,  # (C0 Controls)
            0x0010,  # (C0 Controls)
            0x0011,  # (C0 Controls)
            0x0012,  # (C0 Controls)
            0x0013,  # (C0 Controls)
            0x0014,  # (C0 Controls)
            0x0015,  # (C0 Controls)
            0x0016,  # (C0 Controls)
            0x0017,  # (C0 Controls)
            0x0018,  # (C0 Controls)
            0x0019,  # (C0 Controls)
            0x001A,  # (C0 Controls)
            0x001B,  # (C0 Controls)
            0x001C,  # (C0 Controls)
            0x001D,  # (C0 Controls)
            0x001E,  # (C0 Controls)
            0x001F,  # (C0 Controls)
        ]

        ret = []
        for key, val in data_dict.items():
            if key == "":
                ret.extend(["<empty_string> is not a valid Member Name"])
            else:
                disallowed_boundary_chars = [
                    char
                    for char in [key[0], key[-1]]
                    if ord(char) in disallowed_boundary_chars
                ]
                if disallowed_boundary_chars:
                    ret.extend(
                        [
                            "'{}' is not a valid boundary character in a Member Name".format(
                                char
                            )
                            for char in disallowed_boundary_chars
                        ]
                    )
                disallowed_chars = [
                    char for char in key if ord(char) in disallowed_chars
                ]
                if disallowed_chars:
                    ret.extend(
                        [
                            "'{}' is not a valid character in a Member Name".format(
                                char
                            )
                            for char in disallowed_chars
                        ]
                    )
            if isinstance(val, dict):
                ret.extend(self._validate_member_names(val))
        return ret
