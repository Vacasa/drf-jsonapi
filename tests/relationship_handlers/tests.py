from django.test import TestCase

from drf_jsonapi.relationships import RelationshipHandler

from .models import Node
from .serializers import NodeSerializer
from .relationships import (
    NodeParentHandler,
    NodeChildrenHandler,
    NodeLinksToHandler
)


class TestHandler(RelationshipHandler):
    many = False
    serializer_class = NodeSerializer
    related_field = 'name'


class RelationshipHandlerTestCase(TestCase):

    def test_get_serializer_class_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            RelationshipHandler().get_serializer_class()

    def test_get_serializer_class_import_from_string(self):
        serializer = NodeParentHandler().get_serializer_class()
        self.assertEqual(serializer, NodeSerializer)

    def test_get_serializer_class_import_from_string_invalid(self):
        handler = NodeParentHandler()
        handler.serializer_class = "foo.bar.blah"
        with self.assertRaises(ImportError):
            handler.get_serializer_class()

    def test_get_serializer_class(self):
        serializer = TestHandler().get_serializer_class()
        self.assertEqual(serializer, NodeSerializer)

    def test_get_links(self):
        links = {"foo": "bar"}
        self.assertEqual(RelationshipHandler().get_links(None, links), links)

    def test_get_related_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            RelationshipHandler().get_related(None)

    def test_get_related_one(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b", parent=a)
        related = NodeParentHandler().get_related(b)
        self.assertEqual(related.id, a.id)

    def test_get_related_many(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b", parent=a)
        related = NodeChildrenHandler().get_related(a)
        self.assertEqual(len(related), 1)

    def test_add_related_not_implemented(self):
        handler = RelationshipHandler()
        handler.many = True
        with self.assertRaises(NotImplementedError):
            handler.add_related(None, None)

    def test_add_related_iterable(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        NodeLinksToHandler().add_related(a, [b])
        self.assertEquals(a.links_to.all().count(), 1)

    def test_add_related_scalar(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        NodeLinksToHandler().add_related(a, b)
        self.assertEquals(a.links_to.all().count(), 1)

    def test_set_related_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            RelationshipHandler().set_related(None, None)

    def test_set_related_one(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        NodeParentHandler().set_related(b, a)
        self.assertEquals(b.parent.id, a.id)

    def test_set_related_many(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        NodeLinksToHandler().set_related(b, [a])
        self.assertEquals(b.links_to.all().count(), 1)

    def test_remove_related_not_implemented(self):
        handler = RelationshipHandler()
        handler.many = True
        with self.assertRaises(NotImplementedError):
            handler.remove_related(None, None)

    def test_set_related_many_scalar(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        a.links_to.add(b)
        NodeLinksToHandler().remove_related(a, b)
        self.assertEquals(a.links_to.all().count(), 0)

    def test_set_related_many_iterable(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        a.links_to.add(b)
        NodeLinksToHandler().remove_related(a, [b])
        self.assertEquals(a.links_to.all().count(), 0)
