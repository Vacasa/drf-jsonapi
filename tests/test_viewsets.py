from django.test import TestCase

from rest_framework.test import APIRequestFactory

from drf_jsonapi.viewsets import ViewSet
from drf_jsonapi.response import Response
from drf_jsonapi.objects import Error


class TestViewSet(ViewSet):
    authentication_classes = []
    permission_classes = []
    collection = ["foobar"]

    def list(self, request):
        return Response("OK")

    def paged_list(self, request):
        items = range(100)
        self.apply_pagination(items)
        return Response(self.document.data)

    def create(self, request):
        return self.error_response([Error(detail="This is an error")])


class ViewSetTestCase(TestCase):
    def test_get_view_name(self):
        viewset = TestViewSet()
        viewset.view_name_prefix = "test"
        viewset.suffix = "list"
        self.assertEqual(
            viewset.get_view_name(), viewset.view_name_prefix + " " + viewset.suffix
        )

    def test_get_view_name_no_suffix(self):
        viewset = TestViewSet()
        viewset.view_name_prefix = "test"
        self.assertEqual(viewset.get_view_name(), viewset.view_name_prefix)

    def test_get_queryset(self):
        viewset = TestViewSet()
        viewset.request = None
        self.assertEqual(viewset.get_queryset(), viewset.collection)

    def test_initial(self):
        factory = APIRequestFactory()
        request = factory.get("/tests/")
        view = TestViewSet.as_view({"get": "list"})
        response = view(request)
        self.assertTrue(hasattr(response.renderer_context["view"], "document"))
        self.assertTrue(hasattr(response.renderer_context["view"], "errors"))
        self.assertEqual("OK", response.data)

        # Validate top-level object
        bogus_bodies = [
            {"bogus_key": "bogus_value"},  # Missing "data" element
            {"data": "bogus_value"},  # Wrong "data" type
            {"data": [], "bogus_key": "bogus_value"},  # Extra attributes
        ]

        for bogus_body in bogus_bodies:
            request = factory.post("/tests/", bogus_body, format="json")
            view = TestViewSet.as_view({"post": "create"})
            response = view(request)
            self.assertEqual(response.status_code, 400)

    def test_sparse_fieldset_parsing(self):
        factory = APIRequestFactory()
        request = factory.get("/tests/?fields[foo]=bar,biz")
        ViewSet().parse_sparse_fieldset(request)
        self.assertTrue(hasattr(request, "fields"))
        self.assertEqual(set(request.fields["foo"]), set(["bar", "biz"]))

    def test_sparse_fieldset_parsing_trailing_comma(self):
        """
        If a user submits a field list with a trailing comma (like
        `fields[foo]=bar,biz,`) we need to strip out the empty values
        """
        factory = APIRequestFactory()
        request = factory.get("/tests/?fields[foo]=bar,biz,")
        ViewSet().parse_sparse_fieldset(request)
        self.assertTrue(hasattr(request, "fields"))
        self.assertEqual(set(request.fields["foo"]), set(["bar", "biz"]))

    def test_error_response(self):
        factory = APIRequestFactory()
        request = factory.post("/tests/", data={"data": {}}, format="json")
        view = TestViewSet.as_view({"post": "create"})
        response = view(request)
        self.assertEqual(
            response.data, {"errors": [{"detail": "This is an error", "status": "400"}]}
        )

    def test_apply_pagination(self):
        factory = APIRequestFactory()
        request = factory.get("/tests?page[size]=25")
        view = TestViewSet.as_view({"get": "paged_list"})
        response = view(request)
        self.assertEqual(response.data["meta"]["count"], 100)
        self.assertEqual(response.data["meta"]["has_next"], True)
        self.assertEqual(response.data["meta"]["has_previous"], False)
        self.assertEqual(response.data["meta"]["page_size"], 25)
        self.assertEqual(response.data["meta"]["page"], 1)
        self.assertEqual(response.data["meta"]["num_pages"], 4)
        self.assertEqual(
            response.data["links"]["first"],
            "http://testserver/tests?page[size]=25&page[number]=1",
        )
        self.assertEqual(
            response.data["links"]["next"],
            "http://testserver/tests?page[size]=25&page[number]=2",
        )
        self.assertEqual(response.data["links"]["prev"], None)
        self.assertEqual(
            response.data["links"]["last"],
            "http://testserver/tests?page[size]=25&page[number]=4",
        )

    def test_apply_pagination_page_2(self):
        factory = APIRequestFactory()
        request = factory.get("/tests?page[size]=25&page[number]=2")
        view = TestViewSet.as_view({"get": "paged_list"})
        response = view(request)
        self.assertEqual(response.data["meta"]["count"], 100)
        self.assertEqual(response.data["meta"]["has_next"], True)
        self.assertEqual(response.data["meta"]["has_previous"], True)
        self.assertEqual(response.data["meta"]["page_size"], 25)
        self.assertEqual(response.data["meta"]["page"], 2)
        self.assertEqual(response.data["meta"]["num_pages"], 4)
        self.assertEqual(
            response.data["links"]["first"],
            "http://testserver/tests?page[size]=25&page[number]=1",
        )
        self.assertEqual(
            response.data["links"]["next"],
            "http://testserver/tests?page[size]=25&page[number]=3",
        )
        self.assertEqual(
            response.data["links"]["prev"],
            "http://testserver/tests?page[size]=25&page[number]=1",
        )
        self.assertEqual(
            response.data["links"]["last"],
            "http://testserver/tests?page[size]=25&page[number]=4",
        )

    def test_apply_pagination_one_page(self):
        factory = APIRequestFactory()
        request = factory.get("/tests?page[size]=100&page[number]=1")
        view = TestViewSet.as_view({"get": "paged_list"})
        response = view(request)
        self.assertEqual(response.data["meta"]["has_next"], False)
        self.assertEqual(response.data["links"]["next"], None)
