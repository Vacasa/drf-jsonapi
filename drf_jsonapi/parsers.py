from rest_framework.parsers import JSONParser
from .response import CONTENT_TYPE


class JSONAPIParser(JSONParser):
    """
    Parses JSON-serialized data.
    """
    media_type = CONTENT_TYPE
