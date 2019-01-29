import re
from django.core.validators import URLValidator as DjangoURLValidator
from django.core.validators import _lazy_re_compile, _
from django.core.exceptions import ValidationError
from rest_framework.response import Response

DISALLOWED_BOUNDARY_CHARS = {
    0x002D,  # HYPHEN - MINUS, “-“
    0x005F,  # LOW LINE, “_”
    0x0020,  # SPACE, “ “ (not recommended, not URL safe)
}

DISALLOWED_CHARS = {
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
}


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


class JsonApiValidator:
    """
    http://jsonapi.org/format/

    Latest Specification (v1.0)
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

        if response["Content-Type"] != self.VALID_HEADER:
            return [
                "'Content-Type' header MUST be equal to '{}'".format(self.VALID_HEADER)
            ]
        return []

    def _validate_section(
        self,
        entity_name,
        data_dict,
        must_contain=None,
        must_contain_one=None,
        may_contain=None,
        must_not_contain_both=None,
        must_not_contain=None,
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
        must_contain = must_contain or {}
        must_contain_one = must_contain_one or {}
        may_contain = may_contain or {}
        must_not_contain = must_not_contain or []
        must_not_contain_both = must_not_contain_both or []

        errors = []
        for key in [key for key in must_contain if key not in data_dict]:
            errors.append(
                "Object of type '{}' MUST contain element of type '{}'".format(
                    entity_name, key
                )
            )

        # verify that we have at least one of our must_contain_one
        if must_contain_one and set(must_contain_one) - set(data_dict) == set(
            must_contain_one
        ):
            errors.append(
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
                errors.append(
                    "Object of type '{}' MUST NOT contain element of type '{}'".format(
                        entity_name, key
                    )
                )

        # verify that we don't include two keys that can't appear together
        for [one, two] in must_not_contain_both:
            if one in data_dict and two in data_dict:
                errors.append(
                    "Object of type '{}' MUST NOT contain both of ('{}', '{}')".format(
                        entity_name, one, two
                    )
                )

        # verify that we don't have any strictly prohibited keys in our object
        for key in set(must_not_contain) & set(data_dict):
            errors.append(
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
                errors.extend(fxn(data_dict[key]))

        return errors

    def _validate_top_level(self, data_dict):
        """
        http://jsonapi.org/format/#document-top-level

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

        :param data_element: An empty data element, a list of elements, or a single data object
        :return: A list of validation messages
        :rtype: list
        """

        ret = []
        if data_element == [] or data_element is None:
            return ret

        if not self._validate_resource_objects(
            data_list=data_element
        ) or not self._validate_resource_identifier_objects(data_element):
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

        :param JsonApiValidator self: This object
        :param dict data_dict: The document's list of resource object relationships
        :return: A list of validation messages
        :rtype: list
        """
        errors = []
        for data_list in data_dict.values():
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

        :param JsonApiValidator self: This object
        :param dict data_dict: The document's relationships links
        :return: A list of validation messages
        :rtype: list
        """
        if data_dict is None or data_dict == []:
            return []
        return self._validate_resource_identifier_objects(data_dict)

    def _validate_resource_identifier_objects(self, data):
        """
        http://jsonapi.org/format/#document-resource-identifier-objects

        :param JsonApiValidator self: This object
        :param dict data: The document's resource identifier object(s)
        :return: A list of validation messages
        :rtype: list
        """
        errors = []
        if not isinstance(data, list):
            data = [data]
        for element in data:
            errors.extend(self._validate_resource_identifier_object(element))
        return errors

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
        """
        del data_dict
        return []

    def _validate_links_object(self, data_dict, links_exist=False):
        """
        http://jsonapi.org/format/#document-links
        """
        del links_exist
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

        if url is None:
            return []
        try:
            self.url_validator(url)
        except ValidationError:
            return ["{} is not a valid URL".format(url)]
        return []

    def _validate_jsonapi_object(self, data_dict):
        """
        http://jsonapi.org/format/#document-jsonapi-object
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
        """

        errors = []
        for key, val in data_dict.items():

            if isinstance(val, dict):
                errors.extend(self._validate_member_names(val))

            if key == "":
                errors.extend(["<empty_string> is not a valid Member Name"])
                continue

            errors.extend(self._validate_boundary_characters(key))
            errors.extend(self._validate_characters(key))

        return errors

    def _validate_boundary_characters(self, name):
        errors = []
        boundary_chars = [name[0], name[-1]]
        disallowed_boundary_chars = [
            char for char in boundary_chars if ord(char) in DISALLOWED_BOUNDARY_CHARS
        ]
        if disallowed_boundary_chars:
            errors.extend(
                [
                    "'{}' is not a valid boundary character in a Member Name".format(
                        char
                    )
                    for char in disallowed_boundary_chars
                ]
            )
        return errors

    def _validate_characters(self, name):
        errors = []
        disallowed_chars = [char for char in name if ord(char) in DISALLOWED_CHARS]
        if disallowed_chars:
            errors.extend(
                [
                    "'{}' is not a valid character in a Member Name".format(char)
                    for char in disallowed_chars
                ]
            )
        return errors
