from drf_jsonapi.viewsets import ReadWriteViewSet

from api.models import Publisher, Author, Book

from api.serializers import PublisherSerializer, AuthorSerializer, BookSerializer


class PublisherViewSet(ReadWriteViewSet):
    serializer_class = PublisherSerializer

    def get_collection(self, request):
        return Publisher.objects.all()


class AuthorViewSet(ReadWriteViewSet):
    serializer_class = AuthorSerializer
    collection = Author.objects.all()


class BookViewSet(ReadWriteViewSet):
    serializer_class = BookSerializer
    collection = Book.objects.all()
