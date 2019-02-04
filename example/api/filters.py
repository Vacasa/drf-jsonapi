from drf_jsonapi.filters import FilterSet

from api.models import Book


class BookFilterSet(FilterSet):
    class Meta:
        model = Book
        fields = {
            "title": ["exact", "contains"],
            "authors__name": ["exact", "contains"],
        }
