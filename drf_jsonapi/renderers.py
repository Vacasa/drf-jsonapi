from rest_framework import renderers
from . import response


class JSONRenderer(renderers.JSONRenderer):
    """
    Set media type and format.
    This functionality requires an entry to the REST_FRAMEWORK settings
    dictionary in settings.py:
    'DEFAULT_RENDERER_CLASSES': (
        'drf_jsonapi.renderers.JSONRenderer',
        'drf_jsonapi.renderers.BrowsableAPIRenderer'
    ),
    """

    media_type = response.CONTENT_TYPE
    format = response.FORMAT


class BrowsableAPIRenderer(renderers.BrowsableAPIRenderer):

    def get_raw_data_form(self, data, view, method, request):
        """
        This is currently broken because of the way jsonapi requests are formatted
        (differently from generalized drf requests).
        TODO: Fix this.

        :param BrowsableAPIRenderer self:
        :param data:
        :param view:
        :param method:
        :param request:

        """

        return None
