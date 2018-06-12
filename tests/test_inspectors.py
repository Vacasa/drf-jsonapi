from django.test import TestCase

from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.app_settings import swagger_settings
from drf_yasg import openapi

from drf_jsonapi.inspectors import SwaggerAutoSchema
from drf_jsonapi.generators import OpenAPISchemaGenerator
from drf_jsonapi.viewsets import ReadWriteViewSet
from drf_jsonapi.filters import FilterSet

from .mocks import TestModelSerializer


class FakeView(APIView):
    serializer_class = TestModelSerializer
    collection = []


class SwaggerAutoSchemaTestCase(TestCase):

    def setUp(self):
        factory = APIRequestFactory()
        request = factory.get('/swagger.json')
        self.request = FakeView().initialize_request(request)

        self.info = openapi.Info(
            title="Swagger Title",
            default_version='v2',
            contact=openapi.Contact(email="opensource@vacasa.com"),
            generator_class=OpenAPISchemaGenerator
        )

    def test_generate_schema(self):
        generator = OpenAPISchemaGenerator(
            info=self.info,
            url=swagger_settings.DEFAULT_API_URL
        )
        schema = generator.get_schema(request=self.request, public=True)
        self.assertIsInstance(schema, openapi.Swagger)

    def test_operation_ids_are_unique(self):
        generator = OpenAPISchemaGenerator(
            info=self.info,
            url=swagger_settings.DEFAULT_API_URL
        )
        schema = generator.get_schema(request=self.request, public=True)
        operation_ids = []
        for path, path_object in schema['paths'].items():
            for method, operation_object in path_object.items():
                if isinstance(operation_object, openapi.Operation):
                    operation_ids.append(operation_object.operationId)
        self.assertEqual(len(operation_ids), len(set(operation_ids)))
        self.assertIsInstance(schema, openapi.Swagger)
