from rest_framework.exceptions import APIException


class Document(object):
    """
    The root document object of a JSON API response.
    See: http://jsonapi.org/format/#document-top-level

    TODO: Add assertions that the spec is being followed so violations raise
    exceptions.

    ...

    Attributes
    ----------
    data : dict or list
        The document's "primary data"
    errors: list
        a list of `error objects <http://jsonapi.org/format/#errors>`
    meta: dict
        a `meta object <http://jsonapi.org/format/#document-meta>` that contains
        non-standard meta-information.
    jsonapi: dict
        an object describing the server’s implementation
    links: dict
        a `links object <http://jsonapi.org/format/#document-links>` related to
        the primary data
    included: dict
    """

    def __init__(self, **kwargs):
        """
        Set local variables from keyword arguments

        :param jsonapi.objects.Document self: This object
        :param dict|list data: The document's "primary data"
        :param list errors: a list of `error objects <http://jsonapi.org/format/#errors>`
        :param dict meta: a `meta object <http://jsonapi.org/format/#document-meta>`
        that contains non-standard meta-information.
        :param dict jsonapi: An object describing the server’s implementation
        :param dict links: a `links object <http://jsonapi.org/format/#document-links>`
        related to the primary data
        :param dict included:
        """

        self.data = kwargs.get('data', {})
        self.errors = kwargs.get('errors', [])
        self.meta = kwargs.get('meta', {})
        self.jsonapi = kwargs.get('jsonapi', {})
        self.links = kwargs.get('links', {})
        self.included = kwargs.get('included', [])


class Error(APIException):
    """
    The root error object of a JSON API response
    """

    def __init__(self, detail, **kwargs):
        """
        Builds an error node of a JSON-API response

        :param jsonapi.objects.Error self: This object
        :param string detail: An error message
        :param dict id: a unique identifier for this particular occurrence of the problem.
        :param dict links: An error message's links dictionary <http://jsonapi.org/format/#document-links>
        :param int status_code: An error message's status code
        :param dict code: An application-specific error code, expressed as a string value
        :param dict title: A short, human-readable summary of the problem
        :param dict source: A dictionary containing references to the source of the error
        :param dict meta: a meta dictionary containing non-standard meta-information
        about the error. <http://jsonapi.org/format/#document-meta>
        """

        self.detail = detail
        self.id = kwargs.get('id', {})
        self.links = kwargs.get('links', {})
        self.status_code = kwargs.get('status_code', 400)
        self.code = kwargs.get('code', {})
        self.title = kwargs.get('title', {})
        self.source = kwargs.get('source', {})
        self.meta = kwargs.get('meta', {})
        super().__init__(detail)

    @staticmethod
    def parse_validation_errors(error_dict):
        """
        A simple helper factory that parses the standard output from
        Serializer.errors (dict) and returns an array of Error objects

        :param dict error_dict: A dictionary of error messages and codes
        :return: A list of errors
        :rtype: list
        """

        error_list = []

        for (attribute, errors) in error_dict.items():
            if isinstance(errors, str):
                errors = [errors]
            for error in errors:
                error_list.append(Error(
                    source={'pointer': "data/attributes/{}".format(attribute)},
                    detail=error,
                    status_code=400
                ))

        return error_list
