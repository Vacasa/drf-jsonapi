from django.test import TestCase

from drf_yasg import openapi


class EntitySwaggerAutoSchemaTestCase(TestCase):
    def setUp(self):
        response = self.client.get("/swagger.json")
        self.spec = response.data

    def test_schema_type(self):
        self.assertIsInstance(self.spec, openapi.Swagger)

    def test_paths(self):
        self.assertTrue("/test_resources" in self.spec.paths)
        self.assertTrue("/test_resources/{id}" in self.spec.paths)
        self.assertTrue(
            "/test_resources/{id}/relationships/related_things" in self.spec.paths
        )

    def test_http_verbs(self):
        path = self.spec.paths["/test_resources"]
        self.assertTrue("get" in path)
        self.assertTrue("post" in path)

    def test_paging_params(self):
        parameters = self.spec.paths["/test_resources"]["get"].parameters
        names = [param.name for param in parameters]
        self.assertTrue("page[size]" in names)
        self.assertTrue("page[number]" in names)

    def test_non_standard_route(self):
        self.assertTrue("/nonstandard/{uuid}" in self.spec.paths)
