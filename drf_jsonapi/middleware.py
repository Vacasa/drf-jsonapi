import re

from rest_framework import status


class ExceptionMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response
        self.id_already_exists_re = re.compile(r'\S+ with this id already exists\.$')

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_template_response(self, request, response):
        if 'errors' not in response.data:
            return(response)

        error_codes = set()

        for error in response.data['errors']:
            if (error['status'] == '400' and
                self.id_already_exists_re.match(error['detail']) and
                    error['source']['pointer'] == 'data/attributes/id'):
                error_codes.add(status.HTTP_409_CONFLICT)

        if len(error_codes) == 1:
            response.status_code = error_codes.pop()

        return(response)
