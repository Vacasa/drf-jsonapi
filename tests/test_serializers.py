from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.utils import dateparse, timezone
from django.urls import path
from django.views.defaults import page_not_found

from rest_framework.exceptions import ParseError
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from drf_jsonapi.objects import Document, Error

from drf_jsonapi.serializers import (
    DocumentSerializer,
    ErrorSerializer,
    ResourceSerializer,
    resource_identifier,
)

from . import mocks

urlpatterns = [
    path("test_resources", page_not_found),
    path("test_resources/<int:pk>", page_not_found),
    path("test_resources/<int:pk>/relationships/related_things", page_not_found),
    path("test_resources/<int:pk>/related_things", page_not_found),
]


class DocumentSerializerTestCase(TestCase):
    def setUp(self):

        self.document = Document(
            data={"type": "test", "id": "12345"},
            jsonapi={"version": "1.0"},
            links={"google": "https://google.com"},
            meta={"foo": "bar"},
            included=[
                {"type": "included_thing", "id": "5678", "attributes": {"foo": "bar"}}
            ],
        )

    def test_to_representation(self):
        serializer = DocumentSerializer(self.document)
        self.assertDictEqual(
            serializer.data,
            {
                "data": self.document.data,
                "jsonapi": self.document.jsonapi,
                "links": self.document.links,
                "included": self.document.included,
                "meta": self.document.meta,
            },
        )

    def test_to_representation_with_errors(self):
        """
        Accoring to the JSON API spec the members 'data' and 'errors'
        MUST NOT coexist in the same document.

        If a Document has both data and errors we supress "data"
        """
        self.document.errors = [{"detail": "This is an error"}]
        serializer = DocumentSerializer(self.document)
        self.assertNotIn("data", serializer.data)


class ErrorSerializerTestCase(TestCase):
    def setUp(self):

        self.error = Error(
            detail="This is an error",
            id="12345",
            links={"google": "https://google.com"},
            status_code=405,
            code="12345",
            title="Error",
            source={"parameter": "foobar"},
            meta={"foo": "bar"},
        )

    def test_to_representation(self):
        serializer = ErrorSerializer(self.error)
        self.assertDictEqual(
            serializer.data,
            {
                "detail": self.error.detail,
                "id": self.error.id,
                "links": self.error.links,
                "status": str(self.error.status_code),  # status should be a string!
                "code": self.error.code,
                "title": self.error.title,
                "source": self.error.source,
                "meta": self.error.meta,
            },
        )

    def test_to_representation_no_status_or_detail(self):
        self.error.status_code = None
        self.error.detail = None
        serializer = ErrorSerializer(self.error)
        self.assertDictEqual(
            serializer.data,
            {
                "id": self.error.id,
                "links": self.error.links,
                "code": self.error.code,
                "title": self.error.title,
                "source": self.error.source,
                "meta": self.error.meta,
            },
        )


class ResourceListSerializerTestCase(TestCase):

    serializer_class = mocks.TestResourceSerializer

    def setUp(self):
        self.collection = [
            mocks.TestResource(
                pk=1, name="Test Resource 1", count=5, created_at=timezone.now()
            ),
            mocks.TestResource(
                pk=2, name="Test Resource 2", count=4, created_at=timezone.now()
            ),
            mocks.TestResource(
                pk=3, name="Test Resource 3", count=3, created_at=timezone.now()
            ),
            mocks.TestResource(
                pk=4, name="Test Resource 4", count=2, created_at=timezone.now()
            ),
        ]

    def test_include(self):
        serializer = self.serializer_class(
            self.collection, many=True, include=["related_things"]
        )
        # We need to access data before included can be populated
        data = serializer.data
        del data
        included = serializer.included
        self.assertEqual(len(included), 2)


@override_settings(ROOT_URLCONF=__name__)
class ResourceSerializerTestCase(TestCase):

    serializer_class = mocks.TestResourceSerializer

    def setUp(self):
        self.resource = mocks.TestResource(
            pk=1, name="Test Resource", count=5, created_at=timezone.now()
        )
        self.test_request = {
            "type": "test_resource",
            "attributes": {
                "name": "Test Resource",
                "count": 5,
                "created_at": "1981-11-26T03:24:00",
            },
        }

    def test_define_relationships(self):
        self.assertDictEqual(ResourceSerializer.define_relationships(), {})

    def test_save(self):
        serializer = self.serializer_class(data=self.test_request)
        self.assertTrue(serializer.is_valid())
        resource = serializer.save()
        self.assertIsInstance(resource, mocks.TestResource)
        for attr in [
            attr for attr in self.test_request["attributes"] if attr != "created_at"
        ]:
            self.assertEqual(
                getattr(resource, attr), self.test_request["attributes"][attr]
            )
        if "created_at" in self.test_request["attributes"]:
            self.assertEqual(
                resource.created_at,
                dateparse.parse_datetime(self.test_request["attributes"]["created_at"]),
            )

    def test_run_validation_fails_without_attributes(self):
        data = self.test_request
        del (data["attributes"])
        serializer = self.serializer_class(data=data)
        with self.assertRaises(ParseError):
            serializer.is_valid()

    def test_run_validation_fails_without_type(self):
        data = self.test_request
        del (data["type"])
        serializer = self.serializer_class(data=data)
        with self.assertRaises(ParseError):
            serializer.is_valid()

    def test_run_validation_fails_with_wrong_type(self):
        data = self.test_request
        data["type"] = "homunculus"
        serializer = self.serializer_class(data=data)
        with self.assertRaises(ParseError):
            serializer.is_valid()

    def test_to_representation(self):
        serializer = mocks.TestResourceSerializer(self.resource)
        self.assertDictEqual(
            serializer.data,
            {
                "type": mocks.TestResourceSerializer.Meta.type,
                "id": self.resource.pk,
                "meta": {"reverse_name": self.resource.name[::-1]},
                "links": {
                    "self": "https://test.com/resources/{}".format(self.resource.pk)
                },
                "attributes": {
                    "name": self.resource.name,
                    "count": self.resource.count,
                    "created_at": serializers.DateTimeField().to_representation(
                        self.resource.created_at
                    ),
                },
                "relationships": {
                    "related_things": {"links": {"self": "http://testserver/"}},
                    "empty_things": {"links": {"self": "http://testserver/"}},
                },
            },
        )

    def test_to_representation_identity(self):
        serializer = resource_identifier(mocks.TestResourceSerializer)(self.resource)
        self.assertDictEqual(
            serializer.data,
            {"type": mocks.TestResourceSerializer.Meta.type, "id": self.resource.pk},
        )

    def test_invalid_relationship(self):
        with self.assertRaises(Error):
            mocks.TestResourceSerializer(self.resource, include=["foobar"])

    def test_no_includes(self):
        serializer = mocks.TestResourceSerializer(self.resource, include=["", None])
        self.assertNotIn("data", serializer.data["relationships"])

    def test_get_relationships_empty(self):
        serializer = mocks.TestResourceSerializer(
            self.resource, include=["empty_things"], page_size=10
        )
        data = serializer.data
        self.assertIn("relationships", data)
        self.assertDictEqual(
            data["relationships"]["empty_things"],
            {"links": {"self": "http://testserver/"}, "data": []},
        )

    def test_get_relationships(self):
        serializer = mocks.TestResourceSerializer(
            self.resource, include=["related_things"], page_size=10
        )
        data = serializer.data
        self.assertIn("relationships", data)
        self.assertDictEqual(
            data["relationships"]["related_things"],
            {
                "links": {"self": "http://testserver/"},
                "data": [
                    {"type": "test_resource", "id": 5},
                    {"type": "test_resource", "id": 6},
                ],
            },
        )

    def test_no_relationships(self):
        class TestSerializer(mocks.TestResourceSerializer):
            @staticmethod
            def define_relationships():
                return {}

        serializer = TestSerializer(self.resource, page_size=10)
        data = serializer.data
        self.assertNotIn("relationships", data)

    def test_get_relationships_with_pagination(self):
        factory = APIRequestFactory()
        request = factory.get("/tests/?page[related_things][size]=5")
        serializer = mocks.TestResourceSerializer(
            self.resource,
            include=["related_things"],
            page_size=10,
            context={"request": request},
        )
        data = serializer.data
        self.assertIn("relationships", data)
        self.assertDictEqual(
            data["relationships"]["related_things"],
            {
                "links": {"self": "http://testserver/"},
                "data": [
                    {"type": "test_resource", "id": 5},
                    {"type": "test_resource", "id": 6},
                ],
                "meta": {
                    "count": 2,
                    "has_next": False,
                    "has_previous": False,
                    "page_size": 5,
                    "page": 1,
                    "num_pages": 1,
                },
            },
        )

    def test_included_single(self):
        serializer = mocks.TestResourceSerializer(
            self.resource, include=["related_things"]
        )
        data = serializer.data
        del data
        included = serializer.included
        self.assertEqual(included[0]["type"], mocks.TestResourceSerializer.Meta.type)
        self.assertEqual(included[0]["id"], 5)
        self.assertEqual(len(included), 2)

    def test_included_list(self):
        serializer = mocks.TestResourceSerializer(
            self.resource, include=["related_things"]
        )
        serializer.get_related_things = lambda x: [
            mocks.TestResource(
                pk=5, name="Related Thing 1", count=5, created_at=timezone.now()
            ),
            mocks.TestResource(
                pk=6, name="Related Thing 2", count=5, created_at=timezone.now()
            ),
        ]
        data = serializer.data
        del data
        included = serializer.included
        self.assertEqual(len(included), 2)

    def test_apply_sparse_fieldset(self):
        serializer = mocks.TestResourceSerializer(
            self.resource, only_fields={"test_resource": ["name"]}
        )
        self.assertDictEqual(
            serializer.data,
            {
                "type": mocks.TestResourceSerializer.Meta.type,
                "id": self.resource.pk,
                "meta": {"reverse_name": self.resource.name[::-1]},
                "links": {
                    "self": "https://test.com/resources/{}".format(self.resource.pk)
                },
                "attributes": {"name": self.resource.name},
                "relationships": {
                    "related_things": {"links": {"self": "http://testserver/"}},
                    "empty_things": {"links": {"self": "http://testserver/"}},
                },
            },
        )

    def test_apply_sparse_fielset_invalid_fields(self):
        with self.assertRaises(ParseError):
            mocks.TestResourceSerializer(
                self.resource, only_fields={"test_resource": ["foobar"]}
            )

    def test_get_meta(self):
        self.assertEqual(
            mocks.TestResourceSerializer().get_meta(self.resource),
            {"reverse_name": "ecruoseR tseT"},
        )

    def test_get_links(self):
        request = RequestFactory().get("https://test.com")
        self.assertEqual(
            mocks.TestResourceSerializer().get_links(self.resource, request),
            {"self": "https://test.com/resources/1"},
        )

    def test_get_id(self):
        serializer = mocks.TestResourceSerializer(self.resource)
        self.assertEqual(serializer.get_id(serializer.instance), self.resource.pk)

    def test_get_object_by_id(self):
        with self.assertRaises(NotImplementedError):
            ResourceSerializer.get_object_by_id("foobar")

    def test_sort(self):

        collection = [
            mocks.TestResource(id=5, count=1),
            mocks.TestResource(id=4, count=1),
            mocks.TestResource(id=3, count=1),
            mocks.TestResource(id=2, count=3),
            mocks.TestResource(id=1, count=3),
        ]
        sorted_collection = ResourceSerializer.sort("-count,id", collection)
        self.assertEqual(sorted_collection[0].count, 3)
        self.assertEqual(sorted_collection[0].id, 1)


class ResourceModelSerializerTestCase(TestCase):
    def test_from_identity(self):
        identity_data = {"type": "test_model_resource", "id": 5}
        model = mocks.TestModelSerializer.from_identity(identity_data)
        self.assertIsInstance(model, mocks.TestModel)
        self.assertEqual(model.pk, 5)

    def test_from_identity_many(self):
        identity_data = [
            {"type": "test_model_resource", "id": 1},
            {"type": "test_model_resource", "id": 2},
            {"type": "test_model_resource", "id": 3},
        ]
        models = mocks.TestModelSerializer.from_identity(identity_data, many=True)
        self.assertIsInstance(models, list)
        self.assertIsInstance(models[0], mocks.TestModel)
        self.assertEqual(models[2].pk, 3)

    def test_from_identity_does_not_exist(self):
        identity_data = {"type": "test_model_resource", "id": 666}
        with self.assertRaises(Error):
            mocks.TestModelSerializer.from_identity(identity_data)

    def test_sort(self):
        queryset = mocks.TestModelSerializer.sort(
            "id,-name", mocks.TestModel.objects.all()
        )
        self.assertEqual(queryset.query.order_by, ("id", "-name"))

    def test_sort_default(self):
        queryset = mocks.TestModelSerializer.sort(None, mocks.TestModel.objects.all())
        self.assertEqual(queryset.query.order_by, ())

    def test_sort_invalid_field(self):
        with self.assertRaises(ParseError):
            mocks.TestModelSerializer.sort("foobar", mocks.TestModel.objects.all())


class ResourceIdentifierTestCase(TestCase):
    def test_resource_identifier(self):
        serializer_class = resource_identifier(mocks.TestModelSerializer)
        self.assertEqual(serializer_class.Meta.type, "test_model_resource")
