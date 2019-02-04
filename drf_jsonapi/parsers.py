from rest_framework.parsers import JSONParser


class JSONAPIParser(JSONParser):
    """
    Parses JSON-serialized data.
    """

    media_type = "application/vnd.api+json"
