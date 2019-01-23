from django.test import TestCase

from drf_jsonapi.relationships import RelationshipHandler

from .models import Node
from .serializers import NodeSerializer
from .relationships import NodeParentHandler, NodeChildrenHandler, NodeLinksToHandler


class TestHandler(RelationshipHandler):
    many = False
    serializer_class = NodeSerializer
    related_field = "name"


class RelationshipHandlerTestCase(TestCase):
    def setUp(self):
        self.relationship_handler = RelationshipHandler(NodeSerializer)
        self.node_parent_handler = NodeParentHandler(NodeSerializer)
        self.node_children_handler = NodeChildrenHandler(NodeSerializer)
        self.node_links_to_handler = NodeLinksToHandler(NodeSerializer)

    def test_get_links(self):
        links = {"foo": "bar"}
        self.assertEqual(self.relationship_handler.get_links(None, links, None), links)

    def test_get_related_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.relationship_handler.get_related(None, None)

    def test_get_related_one(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b", parent=a)
        related = self.node_parent_handler.get_related(b, None)
        self.assertEqual(related.id, a.id)

    def test_get_related_many(self):
        a = Node.objects.create(name="a")
        Node.objects.create(name="b", parent=a)
        related = self.node_children_handler.get_related(a, None)
        self.assertEqual(len(related), 1)

    def test_add_related_not_implemented(self):
        self.relationship_handler.many = True
        with self.assertRaises(NotImplementedError):
            self.relationship_handler.add_related(None, None, None)

    def test_add_related_iterable(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        self.node_links_to_handler.add_related(a, [b], None)
        self.assertEqual(a.links_to.all().count(), 1)

    def test_add_related_scalar(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        self.node_links_to_handler.add_related(a, b, None)
        self.assertEqual(a.links_to.all().count(), 1)

    def test_set_related_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.relationship_handler.set_related(None, None, None)

    def test_set_related_one(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        self.node_parent_handler.set_related(b, a, None)
        self.assertEqual(b.parent.id, a.id)

    def test_set_related_many(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        self.node_links_to_handler.set_related(b, [a], None)
        self.assertEqual(b.links_to.all().count(), 1)

    def test_remove_related_not_implemented(self):
        self.relationship_handler.many = True
        with self.assertRaises(NotImplementedError):
            self.relationship_handler.remove_related(None, None, None)

    def test_set_related_many_scalar(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        a.links_to.add(b)
        self.node_links_to_handler.remove_related(a, b, None)
        self.assertEqual(a.links_to.all().count(), 0)

    def test_set_related_many_iterable(self):
        a = Node.objects.create(name="a")
        b = Node.objects.create(name="b")
        a.links_to.add(b)
        self.node_links_to_handler.remove_related(a, [b], None)
        self.assertEqual(a.links_to.all().count(), 0)
