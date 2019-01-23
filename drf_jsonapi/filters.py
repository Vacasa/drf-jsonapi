import re
from collections import OrderedDict

import django_filters
from django_filters.filterset import BaseFilterSet, FilterSetMetaclass
from django_filters.filters import Filter
from .objects import Error


FILTER_PATTERN = re.compile(r"^filter\[([\w\._-]+)\]\[?([\w_-]+)?\]?$")


class FilterParseError(Exception):
    pass


class ParseFiltersMixin:
    """
    Helper functions used by the FilterSet class.  Translate a query dictionary
    to a standard dictionary.
    """

    @classmethod
    def parse_filters(cls, data):
        """
        Retrieve a dictionary of filters from submitted data

        :param django_filters.filterset.FilterSetMetaclass cls: A class instance
        :param django.http.request.QueryDict data: Data coming in from an Http request
        :return: A dictionary of filters requested by the client
        :rtype: dict
        """
        translated_data = {}
        for param, value in data.items():
            filterstring = cls.parse_filter_field(param)
            if filterstring:
                translated_data[filterstring] = value
        return translated_data

    @classmethod
    def parse_filter_field(cls, param):
        """
        Examine a parameter and convert to Django-style filter format if it
        matches that pattern.

        :param django_filters.filterset.FilterSetMetaclass cls: A class instance
        :param str param: A URI parameter
        :return: A filter formatted for Django - using underscores instead
        of brackets
        :rtype: str
        """
        match = FILTER_PATTERN.search(param)
        if not match:
            return None
        field = match.group(1).replace(".", "__")
        expr = match.group(2) or "exact"
        return field if expr == "exact" else field + "__" + expr


class FilterSet(ParseFiltersMixin, django_filters.FilterSet):
    """
    By default django_filters supports query params like `foobar__gt=5` to
    filter results where `foobar` is greater than 5. You can also drill into
    relationships like `author__name__startswith=bill`. Django_filters looks
    for matching query params to apply a filter and ignores everything else.

    However, with JSON API's recommended syntax the above examples would look
    like `filter[foobar][gt]` and `filter[author.name][startswith]`, respectively.

    This class translates JSON API-style filter params into django_filters
    standard dialect before passing them to the FilterSet.
    """

    def __init__(self, data=None, queryset=None, **kwargs):
        """
        Validate given data filters against available model filters.

        :param resource filter self: This object
        :param django.http.request.QueryDict data: URI data provided by client
        :throws Error: If filter is not one specified in the model
        """

        # Translate filters in data
        translated_data = self.parse_filters(data)

        super().__init__(translated_data, queryset, **kwargs)

        for field, value in self.data.items():
            if field not in self.filters:
                raise Error(detail="Invalid filter field: {}".format(field))
            self.data[field] = self.validate_value(field, value)

    def validate_value(self, field, value):
        """
        Validate filter values and convert booleans to django_filter paradigms

        :param resource filter self: This object
        :param str field: Name of a filter
        :param str value: A filter value
        :throws Error: If neither true or false is given as filter value
        """

        # translate BooleanFilters to 'True' or 'False'
        # django_filter expects boolean strings to be capitalized
        if isinstance(self.filters[field], django_filters.filters.BooleanFilter):
            if value.lower() == "true" or value.lower() == "false":
                return value.lower().title()

            raise Error(
                detail="Invalid filter value for {}. Allowed values: true, false".format(
                    field
                )
            )

        return value

    @property
    def collection(self):
        return self.qs


class GenericFilterSet(ParseFiltersMixin, BaseFilterSet, metaclass=FilterSetMetaclass):
    """
    Perform the filtering on a collection with the given filters and values.
    """

    class Meta:
        pass

    def __init__(self, data=None, collection=None):
        """
        Set class variables using given data and collection.

        :param self: This object
        :param django.http.request.QueryDict data: Submitted data, including filters
        :param list collection: A collection of models
        """

        self.data = self.parse_filters(data)
        self._collection = collection or []

    @property
    def collection(self):
        return list(filter(self.dispatch, self._collection))

    def dispatch(self, item):
        """
        Executes filtering with given data, and returns a boolean
        indicating success.

        :param self: This object
        :param item: An item from this object's collection
        :return: Boolean true if successful
        """

        results = []
        for expr, value in self.data.items():
            results.append(getattr(self, "filter_{}".format(expr))(item, value))

        return all(results)

    @classmethod
    def get_filters(cls):
        """
        Retrieve a list of filters from this object's meta property

        :param django_filters.filterset.FilterSetMetaclass cls: A class instance
        :return: A filter dictionary
        :rtype: dict
        """

        if not cls._meta.fields:
            return {}

        filters = OrderedDict()
        fields = cls.get_fields()

        for field_name, lookups in fields.items():
            for lookup_expr in lookups:
                filter_name = cls.get_filter_name(field_name, lookup_expr)
                filters[filter_name] = Filter()

        return filters
