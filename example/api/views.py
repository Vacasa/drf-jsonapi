from drf_jsonapi.viewsets import ReadWriteViewSet
from drf_jsonapi.mixins import DebugMixin

from api.models import Publisher, Author, Book
from api.serializers import PublisherSerializer, AuthorSerializer, BookSerializer
from api.filters import BookFilterSet


class PublisherViewSet(DebugMixin, ReadWriteViewSet):
    serializer_class = PublisherSerializer

    # Nested includes must be explicitly allowed
    # and care taken to avoid n+1 query explosions
    allowed_includes = ("books", "books.authors")

    def get_collection(self, request):
        collection = Publisher.objects.all()

        # This is how we avoid n+1 traps.
        # By prefetching books we avoid separate queries for each resource
        # See: https://docs.djangoproject.com/en/2.1/ref/models/querysets/#prefetch-related
        if "books" in request.include:
            collection = collection.prefetch_related("books")

        if "books.authors" in request.include:
            collection = collection.prefetch_related("books__authors")

        return collection


class BookViewSet(DebugMixin, ReadWriteViewSet):
    serializer_class = BookSerializer

    filter_class = BookFilterSet

    def get_collection(self, request):
        collection = Book.objects.all()

        # Another example of n+1 prevention
        # since "publisher" is a foreign key reference we can use `select_related`
        # to do a JOIN rather than an additional query.
        # See: https://docs.djangoproject.com/en/2.1/ref/models/querysets/#select-related
        if "publisher" in request.include:
            collection = collection.select_related("publisher")

        if "authors" in request.include:
            collection = collection.prefetch_related("authors")

        return collection


class AuthorViewSet(DebugMixin, ReadWriteViewSet):
    serializer_class = AuthorSerializer

    allowed_includes = ("books", "books.publisher")

    def get_collection(self, request):
        collection = Author.objects.all()

        if "books" in request.include:
            collection = collection.prefetch_related("books")

        if "books.publisher" in request.include:
            collection = collection.prefetch_related("books__publisher")

        return collection
