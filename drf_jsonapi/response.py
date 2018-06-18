from rest_framework.response import Response as BaseResponse

CONTENT_TYPE = 'application/vnd.api+json'

class Response(BaseResponse):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content_type = CONTENT_TYPE
