from django.test import TestCase

from drf_jsonapi.parsers import JSONAPIParser


class ParsersTestCase(TestCase):
    def test_jsonapi_parser(self):
        self.assertEqual(JSONAPIParser.media_type, "application/vnd.api+json")

