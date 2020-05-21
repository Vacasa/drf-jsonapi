from django.test import TestCase
from django.test.utils import override_settings

from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import NotFound, MethodNotAllowed, ParseError

from drf_jsonapi.viewsets import ViewSet
from drf_jsonapi.filters import FilterSet
from drf_jsonapi.response import Response
from drf_jsonapi import mixins

from .mocks import TestModel, TestModelSerializer


class TestFilterSet(FilterSet):
    class Meta:
        model = TestModel
        fields = {
            "id": ["exact"],
            "name": ["exact", "iexact", "contains", "icontains", "startswith"],
            "is_active": ["exact"],
        }


class TestViewSet(
    mixins.DebugMixin,
    mixins.ListMixin,
    mixins.CreateMixin,
    mixins.RetrieveMixin,
    mixins.PartialUpdateMixin,
    mixins.DestroyMixin,
    ViewSet,
):
    authentication_classes = []
    permission_classes = []
    view_name_prefix = "Test"
    serializer_class = TestModelSerializer
    filter_class = TestFilterSet
    collection = TestModel.objects.none()


class DebugMixinsTestCase(TestCase):
    @override_settings(DEBUG=True)
    def test_finalize_response(self):
        factory = APIRequestFactory()
        request = factory.get("/test_resources")
        response = Response({"data": {}})
        view = TestViewSet()
        view.headers = {}
        decorated_response = view.finalize_response(request, response)
        self.assertIn("meta", decorated_response.data)
        self.assertIn("num_queries", decorated_response.data["meta"])

    @override_settings(DEBUG=False)
    def test_finalize_response_debug_false(self):
        factory = APIRequestFactory()
        request = factory.get("/test_resources")
        response = Response({"data": {}})
        view = TestViewSet()
        view.headers = {}
        decorated_response = view.finalize_response(request, response)
        self.assertNotIn("meta", decorated_response.data)


class MixinsTestCase(TestCase):
    def test_list_mixin(self):
        factory = APIRequestFactory()
        request = factory.get("/test_resources")
        view = TestViewSet.as_view({"get": "list"})
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_list_no_filter(self):
        class TestViewSetNoFilter(TestViewSet):
            filter_class = None

        factory = APIRequestFactory()
        request = factory.get("/test_resources")
        view = TestViewSetNoFilter.as_view({"get": "list"})
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_retrieve_mixin(self):
        factory = APIRequestFactory()
        request = factory.get(
            "/test_resources/1", headers={"Accept": "application/vnd.api+json"}
        )
        view = TestViewSet.as_view({"get": "retrieve"})
        response = view(request, pk=1)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["resource"], TestModel)

    def test_create_mixin(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/test_resources",
            {
                "data": {
                    "type": "test_model_resource",
                    "attributes": {"name": "Test Resource"},
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 201)
        self.assertIsInstance(response.context["resource"], TestModel)

    def test_create_mixin_with_relationships_to_many(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/test_resources",
            {
                "data": {
                    "type": "test_model_resource",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "related_things": {
                            "data": [
                                {"type": "test_resource", "id": "5"},
                                {"type": "test_resource", "id": "6"},
                            ]
                        }
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 201)

    def test_create_mixin_with_relationships_to_one(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/test_resources",
            {
                "data": {
                    "type": "test_model_resource",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "related_thing": {"data": {"type": "test_resource", "id": "5"}}
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 201)

    def test_create_mixin_invalid_relationship(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/test_resources",
            {
                "data": {
                    "type": "test_model_resource",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "bogus_relationship": {
                            "data": {"type": "test_resource", "id": "5"}
                        }
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 400)

    def test_create_mixin_read_only_relationship_to_one(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/test_resources",
            {
                "data": {
                    "type": "test_model_resource",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "read_only_thing": {
                            "data": {"type": "test_resource", "id": "5"}
                        }
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 400)

    def test_create_missing_relationship_data_keyword(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/test_resources/1",
            {
                "data": {
                    "type": "test_model_resource",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "related_things": {
                            "invalid": [{"type": "test_resource", "id": "5"}]
                        }
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"], "Missing key `data` in relationship object"
        )

    def test_create_missing_resource_obj_keyword_id(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/test_resources/1",
            {
                "data": {
                    "type": "test_model_resource",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "related_things": {
                            "data": [{"type": "test_resource", "pk": "5"}]
                        }
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Missing `id` in resource object")

    def test_create_mixin_invalid(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/test_resources",
            {"data": {"type": "test_model_resource", "attributes": {"count": "bar"}}},
            format="json",
        )
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 400)

    def test_partial_update_mixin(self):
        factory = APIRequestFactory()
        request = factory.patch(
            "/test_resources/1",
            {
                "data": {
                    "type": "test_model_resource",
                    "id": "1",
                    "attributes": {"name": "Test Resource"},
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"patch": "partial_update"})
        response = view(request, pk=1)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["resource"], TestModel)

    def test_partial_update_mixin_with_relationships(self):
        factory = APIRequestFactory()
        request = factory.patch(
            "/test_resources/1",
            {
                "data": {
                    "type": "test_model_resource",
                    "id": "1",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "related_things": {
                            "data": [{"type": "test_resource", "id": "5"}]
                        }
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"patch": "partial_update"})
        response = view(request, pk=1)
        response.render()
        self.assertEqual(response.status_code, 200)

    def test_partial_update_mixin_invalid(self):
        factory = APIRequestFactory()
        request = factory.patch(
            "/test_resources/1",
            {
                "data": {
                    "type": "test_model_resource",
                    "id": "1",
                    "attributes": {"count": "bar"},
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"patch": "partial_update"})
        response = view(request, pk=1)
        response.render()
        self.assertEqual(response.status_code, 400)

    def test_partial_update_missing_relationship_data_keyword(self):
        factory = APIRequestFactory()
        request = factory.patch(
            "/test_resources/1",
            {
                "data": {
                    "type": "test_model_resource",
                    "id": "1",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "related_things": {
                            "invalid": [{"type": "test_resource", "id": "5"}]
                        }
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"patch": "partial_update"})
        response = view(request, pk=1)
        response.render()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"], "Missing key `data` in relationship object"
        )

    def test_partial_update_missing_resource_obj_keyword_id(self):
        factory = APIRequestFactory()
        request = factory.patch(
            "/test_resources/1",
            {
                "data": {
                    "type": "test_model_resource",
                    "id": "1",
                    "attributes": {"name": "Test Resource"},
                    "relationships": {
                        "related_things": {
                            "data": [{"type": "test_resource", "pk": "5"}]
                        }
                    },
                }
            },
            format="json",
        )
        view = TestViewSet.as_view({"patch": "partial_update"})
        response = view(request, pk=1)
        response.render()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Missing `id` in resource object")

    def test_destroy_mixin(self):
        factory = APIRequestFactory()
        request = factory.delete("/test_resources/1")
        view = TestViewSet.as_view({"delete": "destroy"})
        response = view(request, pk=1)
        self.assertEqual(response.status_code, 204)
        self.assertIsInstance(response.context["resource"], TestModel)


class RelationshipCreateMixinTestCase(TestCase):
    class TestManyView(mixins.RelationshipCreateMixin, ViewSet):
        serializer_class = TestModelSerializer
        relationship = "related_things"

        def get_resource(self, request, pk):
            return TestModel()

    class TestOneView(mixins.RelationshipCreateMixin, ViewSet):
        serializer_class = TestModelSerializer
        relationship = "related_thing"

        def get_resource(self, request, pk):
            return TestModel()

    def test_create_valid(self):
        factory = APIRequestFactory()
        request = factory.post("/test_resources", {}, format="json")
        request.data = {"data": [{"type": "test_resource", "id": "test_id"}]}
        view = self.TestManyView()
        response = view.relationship_create(request, 1, "related_things")
        self.assertIsInstance(response.context["resource"], TestModel)

    def test_create_to_many_invalid(self):
        factory = APIRequestFactory()
        request = factory.post("/test_resources", {}, format="json")
        request.data = {"data": "blah"}
        view = self.TestManyView()
        with self.assertRaises(ParseError):
            view.relationship_create(request, 1, "related_things")

    def test_create_to_many_with_dict_invalid(self):
        factory = APIRequestFactory()
        request = factory.post("/test_resources", {}, format="json")
        request.data = {"data": {"stuff": "blah"}}
        view = self.TestManyView()
        with self.assertRaises(ParseError):
            view.relationship_create(request, 1, "related_things")

    def test_create_to_one_invalid(self):
        factory = APIRequestFactory()
        request = factory.post("/test_resources", {}, format="json")
        request.data = {"data": []}
        view = self.TestOneView()
        with self.assertRaises(MethodNotAllowed):
            view.relationship_create(request, 1, "related_thing")


class RelationshipPatchMixinTestCase(TestCase):
    class TestManyView(mixins.RelationshipUpdateMixin):
        serializer_class = TestModelSerializer
        relationship = "related_things"

        def get_resource(self, request, pk):
            return TestModel()

    class TestOneView(mixins.RelationshipUpdateMixin, ViewSet):
        serializer_class = TestModelSerializer
        relationship = "related_thing"

        def get_resource(self, request, pk):
            return TestModel()

    def test_patch_one_valid(self):
        factory = APIRequestFactory()
        request = factory.patch("/test_resources", {}, format="json")
        request.data = {"data": {"type": "test_resource", "id": "test_id"}}
        view = self.TestOneView()
        response = view.relationship_update(request, 1, "related_thing")
        self.assertIsInstance(response.context["resource"], TestModel)

    def test_patch_one_invalid(self):
        factory = APIRequestFactory()
        request = factory.patch("/test_resources", {}, format="json")
        request.data = {"data": []}
        view = self.TestOneView()
        with self.assertRaises(ParseError):
            view.relationship_update(request, 1, "related_thing")


class RelationshipDeleteMixinTestCase(TestCase):
    class TestManyView(mixins.RelationshipDestroyMixin, ViewSet):
        serializer_class = TestModelSerializer
        relationship = "related_things"

        def get_resource(self, request, pk):
            return TestModel()

    class TestOneView(mixins.RelationshipDestroyMixin, ViewSet):
        serializer_class = TestModelSerializer
        relationship = "related_thing"

        def get_resource(self, request, pk):
            return TestModel()

    def test_destroy_to_one_invalid(self):
        factory = APIRequestFactory()
        request = factory.delete(
            "/test_resources/relationships/related_thing",
            {"data": {"type": "related_thing", "id": "5"}},
            format="json",
        )
        view = self.TestOneView()
        with self.assertRaises(NotFound):
            view.relationship_destroy(request, 1, "related_thing")

    def test_destroy_to_many_valid(self):
        factory = APIRequestFactory()
        request = factory.delete(
            "/test_resources/relationships/related_thing", format="json"
        )
        view = self.TestManyView()
        request.data = {"data": {"type": "test_resource", "id": "5"}}
        response = view.relationship_destroy(request, 1, "related_things")
        self.assertIsInstance(response.context["resource"], TestModel)

    def test_destroy_to_many_valid_iterator(self):
        factory = APIRequestFactory()
        request = factory.delete(
            "/test_resources/relationships/related_thing", format="json"
        )
        view = self.TestManyView()
        request.data = {"data": [{"type": "test_resource", "id": "5"}]}
        view.relationship_destroy(request, 1, "related_things")


class RelationshipRetrieveMixinTestCase(TestCase):
    class TestManyView(mixins.RelationshipRetrieveMixin, ViewSet):
        serializer_class = TestModelSerializer
        relationship = "related_things"

        def get_resource(self, request, pk):
            return TestModel()

    class TestOneView(mixins.RelationshipRetrieveMixin, ViewSet):
        serializer_class = TestModelSerializer
        relationship = "related_thing"

        def get_resource(self, request, pk):
            return TestModel()

    class TestEmptyView(mixins.RelationshipRetrieveMixin, ViewSet):
        serializer_class = TestModelSerializer
        relationship = "empty_thing"

        def get_resource(self, request, pk):
            return TestModel()

    def test_list_mixin_one(self):
        factory = APIRequestFactory()
        request = factory.get("/test_resources/1/relationships/related_thing")
        view = self.TestOneView.as_view({"get": "relationship_retrieve"})
        response = view(request, 1, "related_thing")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["resource"], TestModel)

    def test_list_mixin_many(self):
        factory = APIRequestFactory()
        request = factory.get("/test_resources/1/relationships/related_things")
        view = self.TestManyView.as_view({"get": "relationship_retrieve"})
        response = view(request, 1, "related_things")
        self.assertEqual(response.status_code, 200)

    def test_list_mixin_empty(self):
        factory = APIRequestFactory()
        request = factory.get("/test_resources/1/relationships/empty_thing")
        view = self.TestEmptyView.as_view({"get": "relationship_retrieve"})
        response = view(request, 1, "empty_thing")
        self.assertEqual(response.status_code, 200)
