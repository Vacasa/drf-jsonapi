from django.test import TestCase

from rest_framework.exceptions import ValidationError, NotFound
from django.core.paginator import EmptyPage
from django.core.exceptions import (
    PermissionDenied,
    ValidationError as DjangoValidationError,
)

from drf_jsonapi.exception_handlers import jsonapi_exception_handler
from drf_jsonapi.objects import Error


class ExceptionHandlersTestCase(TestCase):
    def test_jsonapi_error_handling(self):
        error = Error(
            detail="detail",
            id="id",
            links={"about": "http://www.google.com"},
            status_code="400",
            code="code",
            title="title",
            source={"parameter": "foobar"},
            meta={"foo": "bar"},
        )

        response = jsonapi_exception_handler(error, {})
        self.assertDictEqual(
            response.data,
            {
                "errors": [
                    {
                        "detail": error.detail,
                        "id": error.id,
                        "links": error.links,
                        "status": error.status_code,
                        "code": error.code,
                        "title": error.title,
                        "source": error.source,
                        "meta": error.meta,
                    }
                ]
            },
        )

    def test_validationerror_with_dict_detail(self):
        """
        Tests that we handle ValidationError with dicts
        """
        error = ValidationError({"foo": "foo is invalid"})
        response = jsonapi_exception_handler(error, {})
        self.assertDictEqual(
            response.data,
            {
                "errors": [
                    {
                        "detail": "foo is invalid",
                        "source": {"pointer": "data/attributes/foo"},
                        "status": "400",
                    }
                ]
            },
        )

    def test_validationerror_without_dict_detail(self):
        """
        Tests that we handle ValidationError without dicts
        (ie. UUID validation error)
        """
        error = DjangoValidationError('"ocelot" is an invalid UUID')
        response = jsonapi_exception_handler(error, {})
        self.assertIn("errors", response.data)
        self.assertEqual(
            response.data["errors"][0]["detail"], "['\"ocelot\" is an invalid UUID']"
        )
        self.assertEqual(response.data["errors"][0]["status"], "400")

    def test_apiexception(self):
        error = NotFound("Not Found.")
        response = jsonapi_exception_handler(error, {})
        self.assertDictEqual(
            response.data, {"errors": [{"detail": "Not Found.", "status": "404"}]}
        )

    def test_pagination_exceptions(self):
        error = EmptyPage("Test")
        response = jsonapi_exception_handler(error, {})
        self.assertDictEqual(
            response.data,
            {
                "errors": [
                    {
                        "detail": str(error),
                        "source": {"parameter": "page[number]"},
                        "status": "400",
                    }
                ]
            },
        )

    def test_default_handler(self):
        error = PermissionDenied()
        response = jsonapi_exception_handler(error, {})
        self.assertEqual(response.data["errors"][0]["status"], "403")

    def test_no_default_response(self):
        error = Exception()
        response = jsonapi_exception_handler(error, {})
        self.assertIsNone(response)
