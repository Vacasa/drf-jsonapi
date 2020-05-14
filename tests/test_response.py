from django.test import TestCase
from rest_framework import status

from drf_jsonapi.response import Response


class ResponseTestCase(TestCase):
    def test_init_with_context(self):
        context = {"key": "value"}
        response = Response(context=context)
        self.assertDictEqual(response.context, context)

    def test_ok_success(self):
        response = Response(status=status.HTTP_200_OK)
        self.assertTrue(response.ok)

    def test_ok_error(self):
        response = Response(status=status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.ok)

    def test_created_true(self):
        response = Response(status=status.HTTP_201_CREATED)
        self.assertTrue(response.created)

    def test_created_false(self):
        response = Response(status=status.HTTP_200_OK)
        self.assertFalse(response.created)
