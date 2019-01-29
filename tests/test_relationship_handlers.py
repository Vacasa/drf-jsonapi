from django.test import TestCase, RequestFactory

from drf_jsonapi.relationships import RelationshipHandler
from drf_jsonapi.serializers import ResourceModelSerializer

from .models import TestModel


class TestModelSerializer(ResourceModelSerializer):
    class Meta:
        model = TestModel
        type = "test_model_resource"
        basename = "test_resources"
        fields = ("name", "count", "is_active", "created_at")


class RelationshipHandlerTestCase(TestCase):
    def test_to_one_relationship(self):
        handler = RelationshipHandler(
            TestModelSerializer, related_field="related_things", many=False
        )
        self.assertEqual(handler.related_field, "related_things")
        self.assertEqual(handler.many, False)

    def test_apply_pagination(self):
        related = list(range(20))
        handler = RelationshipHandler(
            TestModelSerializer, related_field="related_things", many=True
        )
        data, meta = handler.apply_pagination(related, page_size=10, page_number=1)
        self.assertEqual(len(data), 10)
        self.assertEqual(meta["count"], 20)
        self.assertTrue(meta["has_next"])

    def test_apply_pagination_empty_page(self):
        related = list(range(9))
        handler = RelationshipHandler(
            TestModelSerializer, related_field="related_things", many=True
        )
        data, meta = handler.apply_pagination(related, page_size=10, page_number=2)
        self.assertEqual(len(data), 0)
        self.assertEqual(meta["count"], 9)
        self.assertFalse(meta["has_next"])
        self.assertTrue(meta["has_previous"])