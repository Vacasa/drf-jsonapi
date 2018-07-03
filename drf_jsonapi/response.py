from rest_framework.response import Response as BaseResponse


CONTENT_TYPE = 'application/vnd.api+json'
FORMAT = 'vnd.api+json'


class Response(BaseResponse):
    pass
