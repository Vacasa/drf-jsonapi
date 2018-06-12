from django.test import TestCase

from drf_jsonapi.objects import Document, Error


class DocumentTestCase(TestCase):

    def test_default_object_creation(self):
        document = Document()

        # Default data should be empty dict
        self.assertEqual(document.data, {})

        # Default errors should be empty list
        self.assertEqual(document.errors, [])

        # Default meta should be empty dict
        self.assertEqual(document.meta, {})

        # Default jsonapi should be an empty dict
        self.assertEqual(document.jsonapi, {})

        # Default links should be an empty dict
        self.assertEqual(document.links, {})

        # Default included should be an empty list
        self.assertEqual(document.included, [])


class ErrorTestCase(TestCase):

    def test_default_object_creation(self):
        message = "This is my error message"
        error = Error(message)

        self.assertEqual(error.detail, message)
        self.assertEqual(str(error), message)

    def test_parse_validation_errors(self):
        errors_dict = {
            'foo': [
                "This is an error with foo",
                "This is another error with foo"
            ],
            'bar': [
                "This is an error with bar"
            ]
        }

        errors = Error.parse_validation_errors(errors_dict)

        self.assertEqual(len(errors), 3)
