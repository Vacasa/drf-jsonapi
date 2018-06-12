from django.utils import timezone
from django.db import models
from rest_framework import serializers

from drf_jsonapi.relationships import RelationshipHandler

from drf_jsonapi.serializers import (
    ResourceSerializer,
    ResourceModelSerializer,
    ResourceListSerializer
)


class TestResource(object):

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestManyRelationshipHandler(RelationshipHandler):
    many = True

    def get_serializer_class(self):
        return TestResourceSerializer

    def get_related(self, instance):
        return [
            TestResource(
                pk=5,
                name="Related Thing 1",
                count=5,
                created_at=timezone.now()
            ),
            TestResource(
                pk=6,
                name="Related Thing 2",
                count=5,
                created_at=timezone.now()
            )
        ]

    def add_related(self, resource, related):
        return True

    def remove_related(self, resource, related):
        return True

    def set_related(self, instance, related):
        instance.related = related

    def get_links(self, instance, links):
        links = {
            'self': "http://testserver/"
        }
        return links


class TestOneRelationshipHandler(RelationshipHandler):
    many = False

    def get_serializer_class(self):
        return TestResourceSerializer

    def set_related(self, instance, related):
        return True


class TestResourceSerializer(ResourceSerializer):
    name = serializers.CharField()
    count = serializers.IntegerField()
    created_at = serializers.DateTimeField()

    class Meta:
        type = "test_resource"
        base_path = "/test_resources"
        fields = (
            'name',
            'count',
            'created_at'
        )
        relationships = {
            'related_things': TestManyRelationshipHandler()
        }

    def create(self, validated_data):
        return TestResource(**validated_data)

    def get_meta(self, instance):
        meta = super().get_meta(instance)
        meta["reverse_name"] = instance.name[::-1]
        return meta

    def get_links(self, instance):
        links = super().get_links(instance)
        links["self"] = "https://test.com/resources/{}".format(instance.pk)
        return links

    @classmethod
    def get_object_by_id(cls, id):
        return TestResource(id=id)


class TestModelQuerySet(models.QuerySet):
    def get(self, pk, **kwargs):
        if pk == 666:
            raise TestModel.DoesNotExist()
        return TestModel(
            pk=pk,
            name="Test Model",
            is_active=True
        )


class TestModelManager(models.Manager):
    def get_queryset(self):
        return TestModelQuerySet(self.model, using=self._db)

    def get(self, pk, **kwargs):
        return self.get_queryset().get(pk=pk, **kwargs)


class TestModel(models.Model):
    name = models.CharField(max_length=128, null=True)
    count = models.IntegerField(null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    related_things = models.ForeignKey('self', on_delete=models.CASCADE)

    # Override manager so we can mock the methods
    objects = TestModelManager()

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self


class TestModelSerializer(ResourceModelSerializer):

    class Meta:
        model = TestModel
        type = "test_model_resource"
        base_path = "/test_resources"
        fields = (
            'name',
            'count',
            'is_active',
            'created_at'
        )
        relationships = {
            'related_things': TestManyRelationshipHandler(),
            'related_thing': TestOneRelationshipHandler()
        }
