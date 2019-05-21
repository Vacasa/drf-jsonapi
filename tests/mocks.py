from django.utils import timezone
from rest_framework import serializers

from drf_jsonapi.relationships import RelationshipHandler
from drf_jsonapi.viewsets import ReadWriteViewSet

from drf_jsonapi.serializers import ResourceSerializer, ResourceModelSerializer

from .models import TestModel


class TestResource:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestManyRelationshipHandler(RelationshipHandler):
    many = True

    def get_related(self, resource, request):
        return [
            TestResource(
                pk=5, name="Related Thing 1", count=5, created_at=timezone.now()
            ),
            TestResource(
                pk=6, name="Related Thing 2", count=5, created_at=timezone.now()
            ),
        ]

    def add_related(self, resource, related, request):
        return True

    def remove_related(self, resource, related, request):
        return True

    def set_related(self, resource, related, request):
        resource.related = related

    def get_links(self, resource, links, request):
        links = {"self": "http://testserver/"}
        return links


class TestManyEmptyRelationshipHandler(TestManyRelationshipHandler):
    def get_related(self, resource, request):
        return []


class TestOneRelationshipHandler(RelationshipHandler):
    many = False

    def set_related(self, resource, related, request):
        return True

    def get_related(self, resource, request):
        return TestResource(
            pk=5, name="Related Thing 1", count=5, created_at=timezone.now()
        )


class TestResourceSerializer(ResourceSerializer):
    name = serializers.CharField()
    count = serializers.IntegerField()
    created_at = serializers.DateTimeField()

    class Meta:
        type = "test_resource"
        basename = "test_resources"
        fields = ("name", "count", "created_at")

    @staticmethod
    def define_relationships():
        return {
            "related_things": TestManyRelationshipHandler(
                TestResourceSerializer, show_data=True
            ),
            "empty_things": TestManyEmptyRelationshipHandler(TestResourceSerializer),
        }

    def create(self, validated_data):
        return TestResource(**validated_data)

    def get_meta(self, instance):
        meta = super().get_meta(instance)
        meta["reverse_name"] = instance.name[::-1]
        return meta

    def get_links(self, instance, request=None):
        links = super().get_links(instance, request)
        links["self"] = "https://test.com/resources/{}".format(instance.pk)
        return links

    @classmethod
    def get_object_by_id(cls, identifier):
        return TestResource(id=identifier)


class EmptyRelationshipHandler(RelationshipHandler):
    many = False

    def get_related(self, resource, request):
        return None


class TestModelSerializer(ResourceModelSerializer):
    class Meta:
        model = TestModel
        type = "test_model_resource"
        basename = "test_resources"
        fields = ("name", "count", "is_active", "created_at")

    @staticmethod
    def define_relationships():
        return {
            "related_things": TestManyRelationshipHandler(TestResourceSerializer),
            "related_thing": TestOneRelationshipHandler(TestResourceSerializer),
            "empty_thing": EmptyRelationshipHandler(TestResourceSerializer),
            "read_only_thing": TestOneRelationshipHandler(
                TestResourceSerializer, read_only=True
            ),
            "read_only_things": TestManyRelationshipHandler(
                TestResourceSerializer, read_only=True
            ),
        }


class TestView(ReadWriteViewSet):
    view_name_prefix = "Test Resource"
    serializer_class = TestModelSerializer
    collection = []
