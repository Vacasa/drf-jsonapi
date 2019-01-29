from drf_jsonapi.serializers import ResourceModelSerializer
from drf_jsonapi.relationships import RelationshipHandler

from api.models import Publisher, Author, Book


class PublisherSerializer(ResourceModelSerializer):
    class Meta:
        type = "publisher"
        basename = "publishers"
        model = Publisher
        id_field = "pk"
        fields = ("name",)

    @staticmethod
    def define_relationships():
        return {"books": RelationshipHandler(BookSerializer, "books", many=True)}


class AuthorSerializer(ResourceModelSerializer):
    class Meta:
        type = "author"
        basename = "authors"
        model = Author
        id_field = "pk"
        fields = ("name",)

    @staticmethod
    def define_relationships():
        return {"books": RelationshipHandler(BookSerializer, "books", many=True)}


class BookSerializer(ResourceModelSerializer):
    class Meta:
        type = "book"
        basename = "books"
        model = Book
        id_field = "pk"
        fields = ("title",)

    @staticmethod
    def define_relationships():
        return {
            "authors": RelationshipHandler(AuthorSerializer, "authors", many=True),
            "publisher": RelationshipHandler(PublisherSerializer, "publisher"),
        }
