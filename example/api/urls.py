from django.urls import re_path, path
from drf_jsonapi import routers

from rest_framework.permissions import AllowAny

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_jsonapi.generators import OpenAPISchemaGenerator

from api.views import PublisherViewSet, AuthorViewSet, BookViewSet

schema_view = get_schema_view(
    # TODO: Verify API info details
    openapi.Info(
        title="Example API",
        default_version="v1",
        contact=openapi.Contact(email="opensource@vacasa.com"),
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

router = routers.Router(trailing_slash=False)

router.register(PublisherViewSet)
router.register(AuthorViewSet)
router.register(BookViewSet)

urlpatterns += router.urls
