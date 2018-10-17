from django_filters.rest_framework.backends import DjangoFilterBackend as BaseClass
from django_filters import compat
from django.db.models import Field

LOOKUP_TYPES = Field.get_lookups().keys()


class DjangoFilterBackend(BaseClass):
    """
    Supports field filtering.
    This functionality requires an entry to the REST_FRAMEWORK settings
    dictionary in settings.py:
    'DEFAULT_FILTER_BACKENDS': ('drf_jsonapi.backends.DjangoFilterBackend')
    """

    def get_schema_fields(self, view):
        """
        Retrieve a list of Field objects from a view

        :param self: This object instance
        :param view: A Django View
        :returns: A list of CoreApi Field objects
        """

        filter_class = getattr(view, 'filter_class', None)
        fields = []

        if not filter_class:
            return fields

        for field_name, field in filter_class.base_filters.items():

            parts = field_name.split('__')

            if parts[-1] in LOOKUP_TYPES:
                lookup = parts.pop()
                field_name = "filter[{}][{}]".format('.'.join(parts), lookup)
            else:
                field_name = "filter[{}]".format('.'.join(parts))

            fields.append(compat.coreapi.Field(
                name=field_name,
                required=field.extra['required'],
                location='query',
                schema=self.get_coreschema_field(field)
            ))

        return fields
