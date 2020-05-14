from rest_framework import status
from rest_framework.response import Response as BaseResponse


class Response(BaseResponse):
    def __init__(self, *args, **kwargs):
        context = kwargs.pop("context", {})
        super(Response, self).__init__(*args, **kwargs)
        self.context = context

    @property
    def ok(self):
        """Returns True if :attr:`status_code` is less than 400, False if not."""
        if self.status_code >= status.HTTP_400_BAD_REQUEST:
            return False
        return True

    @property
    def created(self):
        """Returns True if :attr:`status_code` is 201, False if not."""
        return self.status_code == status.HTTP_201_CREATED
