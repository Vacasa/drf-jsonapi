from django.test import TestCase, override_settings

from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import NotFound, MethodNotAllowed, ParseError

from drf_jsonapi.viewsets import ViewSet, RelationshipViewSet
from drf_jsonapi.filters import FilterSet
from drf_jsonapi import mixins

from .mocks import TestModel, TestModelSerializer


class TestFilterSet(FilterSet):
    class Meta:
        model = TestModel
        fields = {
            'id': ['exact'],
            'name': ['exact', 'iexact', 'contains', 'icontains', 'startswith'],
            'is_active': ['exact']
        }


class TestViewSet(mixins.ListMixin, mixins.CreateMixin, mixins.RetrieveMixin,
                  mixins.PartialUpdateMixin, mixins.DestroyMixin, ViewSet):
    authentication_classes = []
    permission_classes = []
    view_name_prefix = 'Test'
    serializer_class = TestModelSerializer
    filter_class = TestFilterSet
    collection = TestModel.objects.none()


class MixinsTestCase(TestCase):

    def test_list_mixin(self):
        factory = APIRequestFactory()
        request = factory.get('/test_resources')
        view = TestViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEquals(response.status_code, 200)

    def test_retrieve_mixin(self):
        factory = APIRequestFactory()
        request = factory.get('/test_resources/1')
        view = TestViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=1)
        self.assertEquals(response.status_code, 200)

    def test_create_mixin(self):
        factory = APIRequestFactory()
        request = factory.post('/test_resources', {
            "data": {
                "type": "test_model_resource",
                "attributes": {
                    "name": "Test Resource"
                }
            }
        }, format="json")
        view = TestViewSet.as_view({'post': 'create'})
        response = view(request)
        response.render()
        self.assertEquals(response.status_code, 201)

    def test_create_mixin_with_relationships(self):
        factory = APIRequestFactory()
        request = factory.post('/test_resources', {
            "data": {
                "type": "test_model_resource",
                "attributes": {
                    "name": "Test Resource"
                },
                "relationships": {
                    "related_things": {
                        "data": [
                            {
                                "type": "test_resource",
                                "id": "5"
                            },
                            {
                                "type": "test_resource",
                                "id": "6"
                            },
                        ]
                    }
                }
            }
        }, format="json")
        view = TestViewSet.as_view({'post': 'create'})
        response = view(request)
        response.render()
        self.assertEquals(response.status_code, 201)

    def test_create_mixin_invalid_relationship(self):
        factory = APIRequestFactory()
        request = factory.post('/test_resources', {
            "data": {
                "type": "test_model_resource",
                "attributes": {
                    "name": "Test Resource"
                },
                "relationships": {
                    "bogus_relationship": {
                        "data": {
                            "type": "test_resource",
                            "id": "5"
                        },
                    }
                }
            }
        }, format="json")
        view = TestViewSet.as_view({'post': 'create'})
        response = view(request)
        response.render()
        self.assertEquals(response.status_code, 400)

    def test_create_mixin_invalid(self):
        factory = APIRequestFactory()
        request = factory.post('/test_resources', {
            "data": {
                "type": "test_model_resource",
                "attributes": {
                    "count": "bar"
                }
            }
        }, format="json")
        view = TestViewSet.as_view({'post': 'create'})
        response = view(request)
        response.render()
        self.assertEquals(response.status_code, 400)

    def test_partial_update_mixin(self):
        factory = APIRequestFactory()
        request = factory.patch('/test_resources/1', {
            "data": {
                "type": "test_model_resource",
                "id": "1",
                "attributes": {
                    "name": "Test Resource"
                }
            }
        }, format="json")
        view = TestViewSet.as_view({'patch': 'partial_update'})
        response = view(request, pk=1)
        response.render()
        self.assertEquals(response.status_code, 200)

    def test_partial_update_mixin_with_relationships(self):
        factory = APIRequestFactory()
        request = factory.patch('/test_resources/1', {
            "data": {
                "type": "test_model_resource",
                "id": "1",
                "attributes": {
                    "name": "Test Resource"
                },
                "relationships": {
                    "related_things": {
                        "data": [
                            {
                                "type": "test_resource",
                                "id": "5"
                            }
                        ]
                    }
                }
            }
        }, format="json")
        view = TestViewSet.as_view({'patch': 'partial_update'})
        response = view(request, pk=1)
        response.render()
        self.assertEquals(response.status_code, 200)

    def test_partial_update_mixin_invalid(self):
        factory = APIRequestFactory()
        request = factory.patch('/test_resources/1', {
            "data": {
                "type": "test_model_resource",
                "id": "1",
                "attributes": {
                    "count": "bar"
                }
            }
        }, format="json")
        view = TestViewSet.as_view({'patch': 'partial_update'})
        response = view(request, pk=1)
        response.render()
        self.assertEquals(response.status_code, 400)

    def test_destroy_mixin(self):
        factory = APIRequestFactory()
        request = factory.delete('/test_resources/1')
        view = TestViewSet.as_view({'delete': 'destroy'})
        response = view(request, pk=1)
        self.assertEquals(response.status_code, 204)


class RelationshipCreateMixinTestCase(TestCase):

    class TestManyView(mixins.RelationshipCreateMixin, RelationshipViewSet):
        serializer_class = TestModelSerializer
        relationship = 'related_things'

        def get_resource(self, *args, **kwargs):
            return True

    class TestOneView(mixins.RelationshipCreateMixin, RelationshipViewSet):
        serializer_class = TestModelSerializer
        relationship = 'related_thing'

        def get_resource(self, *args, **kwargs):
            return True

    def test_create_valid(self):
        factory = APIRequestFactory()
        request = factory.post('/test_resources', {}, format="json")
        request.data = {
            "data": [{"type": "test_resource", 'id': 'test_id'}],
        }
        view = self.TestManyView()
        view.create(request)

    def test_create_to_many_invalid(self):
        factory = APIRequestFactory()
        request = factory.post('/test_resources', {}, format="json")
        request.data = {
            "data": "blah"
        }
        view = self.TestManyView()
        with self.assertRaises(ParseError):
            view.create(request)

    def test_create_to_many_with_dict_invalid(self):
        factory = APIRequestFactory()
        request = factory.post('/test_resources', {}, format="json")
        request.data = {
            "data": {"stuff": "blah"}
        }
        view = self.TestManyView()
        with self.assertRaises(ParseError):
            view.create(request)

    def test_create_to_one_invalid(self):
        factory = APIRequestFactory()
        request = factory.post('/test_resources', {}, format="json")
        request.data = {
            "data": []
        }
        view = self.TestOneView()
        with self.assertRaises(MethodNotAllowed):
            view.create(request)


class RelationshipPatchMixinTestCase(TestCase):

    class TestManyView(mixins.RelationshipPatchMixin, RelationshipViewSet):
        serializer_class = TestModelSerializer
        relationship = 'related_things'

        def get_resource(self, *args, **kwargs):
            return TestModel()

    class TestOneView(mixins.RelationshipPatchMixin, RelationshipViewSet):
        serializer_class = TestModelSerializer
        relationship = 'related_thing'

        def get_resource(self, *args, **kwargs):
            return TestModel()

    def test_patch_one_valid(self):
        factory = APIRequestFactory()
        request = factory.patch('/test_resources', {}, format="json")
        request.data = {
            "data": {"type": "test_resource", "id": "test_id"}
        }
        view = self.TestOneView()
        view.patch(request)

    def test_patch_one_invalid(self):
        factory = APIRequestFactory()
        request = factory.patch('/test_resources', {}, format="json")
        request.data = {
            "data": []
        }
        view = self.TestOneView()
        with self.assertRaises(ParseError):
            view.patch(request)


class RelationshipDeleteMixinTestCase(TestCase):

    class TestManyView(mixins.RelationshipDeleteMixin, RelationshipViewSet):
        serializer_class = TestModelSerializer
        relationship = 'related_things'

        def get_resource(self, *args, **kwargs):
            return True

    class TestOneView(mixins.RelationshipDeleteMixin, RelationshipViewSet):
        serializer_class = TestModelSerializer
        relationship = 'related_thing'

        def get_resource(self, *args, **kwargs):
            return True

    def test_destroy_to_one_invalid(self):
        factory = APIRequestFactory()
        request = factory.delete(
            '/test_resources/relationships/related_thing',
            {
                "data": {
                    "type": "related_thing",
                    "id": "5"
                }
            },
            format="json"
        )
        view = self.TestOneView()
        with self.assertRaises(NotFound):
            view.delete(request)

    def test_destroy_to_many_valid(self):
        factory = APIRequestFactory()
        request = factory.delete(
            '/test_resources/relationships/related_thing',
            format="json"
        )
        view = self.TestManyView()
        request.data = {
            "data": {
                "type": "test_resource",
                "id": "5"
            }
        }
        view.delete(request)


class RelationshipListMixinTestCase(TestCase):

    class TestManyView(mixins.RelationshipListMixin, RelationshipViewSet):
        serializer_class = TestModelSerializer
        relationship = 'related_things'

        def get_resource(self, *args, **kwargs):
            return True

    class TestOneView(mixins.RelationshipListMixin, RelationshipViewSet):
        serializer_class = TestModelSerializer
        relationship = 'related_thing'

        def get_resource(self, *args, **kwargs):
            return True

    def test_list_mixin_one(self):
        factory = APIRequestFactory()
        request = factory.get('/test_resources/relationships/related_thing')
        view = self.TestOneView.as_view({'get': 'list'})
        response = view(request)
        self.assertEquals(response.status_code, 200)

    def test_list_mixin_many(self):
        factory = APIRequestFactory()
        request = factory.get('/test_resources/relationships/related_thing')
        view = self.TestManyView.as_view({'get': 'list'})
        response = view(request)
        self.assertEquals(response.status_code, 200)
