from django.test import TestCase

from rest_framework.viewsets import ViewSet

from drf_jsonapi.routers import Router

from .serializers import TrunkSerializer
from .views import LeafViewSet, TrunkViewSet


class RouterTestCase(TestCase):
    def test_get_routes(self):
        router = Router(trailing_slash=False)
        routes = {
            route.name: route.mapping for route in router.get_routes(TrunkViewSet)
        }
        self.assertIn("{basename}-relationships-branches", routes)
        mappings = routes["{basename}-relationships-branches"]
        self.assertIn("get", mappings)
        self.assertIn("post", mappings)
        self.assertIn("patch", mappings)
        self.assertIn("delete", mappings)

    def test_get_routes_read_only(self):
        router = Router(trailing_slash=False)
        routes = {route.name: route.mapping for route in router.get_routes(LeafViewSet)}
        self.assertIn("{basename}-relationships-branch", routes)
        mappings = routes["{basename}-relationships-branch"]
        self.assertNotIn("post", mappings)
        self.assertNotIn("put", mappings)
        self.assertNotIn("patch", mappings)
        self.assertNotIn("delete", mappings)

    def test_get_urls_for_viewset(self):
        router = Router(trailing_slash=False)
        # router.register(LeafViewSet)
        urls = router.get_urls_for_viewset("prefix", LeafViewSet, "basename")
        base_names = [url.name for url in urls]
        self.assertListEqual(
            base_names,
            ["basename-list", "basename-detail", "basename-relationships-branch"],
        )

    def test_get_urls_missing_methods(self):
        class EmptyView(ViewSet):
            serializer_class = TrunkSerializer

        router = Router(trailing_slash=False)
        urls = router.get_urls_for_viewset("prefix", EmptyView, "basename")
        self.assertEqual(urls, [])

    def test_url_segment_kwarg_overrides_relationship_name(self):
        router = Router(trailing_slash=False)
        urls = router.get_urls_for_viewset("prefix", TrunkViewSet, "basename")
        patterns = [url.pattern._regex for url in urls]  # noqa
        self.assertIn("^prefix/(?P<pk>[^/.]+)/relationships/tree-roots$", patterns)

    def test_get_urls_no_root_view(self):
        router = Router(trailing_slash=False)
        router.include_root_view = False
        router.register(LeafViewSet)
        urls = router.get_urls()
        base_names = [url.name for url in urls]
        self.assertNotIn("api-root", base_names)

    def test_get_urls_no_format_suffixes(self):
        router = Router(trailing_slash=False)
        router.include_format_suffixes = False
        router.register(LeafViewSet)
        urls = router.get_urls()
        patterns = [url.pattern._regex for url in urls]  # noqa
        for pattern in patterns:
            self.assertNotIn(".(?P<format>[a-z0-9]+)", pattern)
