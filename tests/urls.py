from django.urls import path, re_path

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from rest_framework.permissions import AllowAny

from .mocks import TestView, NonStandardViewSet

from drf_jsonapi.generators import OpenAPISchemaGenerator
from drf_jsonapi.routers import Router

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

router = Router(trailing_slash=False)
router.register(TestView)
urlpatterns += router.urls

non_standard_endpoint = path(
    "nonstandard/<uuid>", NonStandardViewSet.as_view({"get": "get_item"})
)

urlpatterns += [non_standard_endpoint]
