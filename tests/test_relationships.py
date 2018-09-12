from django.test import TestCase

from drf_jsonapi.relationships import RelationshipHandler


class RelationshipHandlerTestCase(TestCase):

    def test_get_serializer_class(self):
        with self.assertRaises(NotImplementedError):
            RelationshipHandler().get_serializer_class()

    def test_get_links(self):
        links = {"foo": "bar"}
        self.assertEqual(RelationshipHandler().get_links(None, links), links)

    def test_get_related(self):
        with self.assertRaises(NotImplementedError):
            RelationshipHandler().get_related(None)

    def test_add_related(self):
        handler = RelationshipHandler()
        handler.many = True
        with self.assertRaises(NotImplementedError):
            handler.add_related(None, None)

    def test_set_related(self):
        with self.assertRaises(NotImplementedError):
            RelationshipHandler().set_related(None, None)

    def test_remove_related(self):
        handler = RelationshipHandler()
        handler.many = True
        with self.assertRaises(NotImplementedError):
            handler.remove_related(None, None)
