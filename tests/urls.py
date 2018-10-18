import importlib
from django.urls import path, re_path

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from rest_framework.permissions import AllowAny

from .mocks import TestView, TestRelationshipViewSet

from rest_framework_nested import routers

from drf_jsonapi.generators import OpenAPISchemaGenerator
from drf_jsonapi.routers import RelationshipRouter

schema_view = get_schema_view(
    # TODO: Verify API info details
    openapi.Info(
        title="Vacasa Housekeeping API",
        default_version="v1",
        contact=openapi.Contact(email="housekeeping@vacasa.com"),
    ),
    validators=[],
    public=True,
    permission_classes=(AllowAny,),
    generator_class=OpenAPISchemaGenerator,
)

urlpatterns = [
    re_path(
        r"swagger(?P<format>.json|.yaml)$",
        schema_view.without_ui(cache_timeout=1),
        name="schema-json",
    ),
    path("spec", schema_view.with_ui("redoc", cache_timeout=1), name="schema-redoc"),
]

router = routers.DefaultRouter(trailing_slash=False)
router.register("test_resources", TestView, base_name="test_resources")
urlpatterns += router.urls

test_related_router = RelationshipRouter(
    router, "test_resources", lookup="test_resources", trailing_slash=False
)
test_related_router.register(
    "relationships/related_things",
    TestRelationshipViewSet,
    base_name="test_resources-related_things"
)

urlpatterns += test_related_router.urls


