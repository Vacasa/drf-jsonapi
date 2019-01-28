from collections import namedtuple

from django.urls import re_path

from rest_framework.routers import DefaultRouter
from rest_framework.urlpatterns import format_suffix_patterns


Route = namedtuple(
    "Route", ["url", "mapping", "name", "detail", "initkwargs", "kwargs"]
)


class Router(DefaultRouter):
    def get_routes(self, viewset):
        routes = super().get_routes(viewset)
        relationships = viewset.serializer_class.define_relationships()
        for relationship, handler in relationships.items():
            if handler.read_only:
                action_map = {"get": "relationship_retrieve"}
            else:
                action_map = {
                    "get": "relationship_retrieve",
                    "post": "relationship_create",
                    "patch": "relationship_update",
                    "delete": "relationship_destroy",
                }
            routes.append(
                Route(
                    url=r"^{{prefix}}/{{lookup}}/relationships/{}{{trailing_slash}}$".format(
                        relationship
                    ),
                    mapping=action_map,
                    name="{{basename}}-relationships-{}".format(relationship),
                    detail=True,
                    initkwargs={"suffix": relationship},
                    kwargs={"relationship": relationship},
                )
            )
        return routes

    def get_urls(self):
        """
        Use the registered viewsets to generate a list of URL patterns.
        """
        urls = []

        for prefix, viewset, basename in self.registry:
            urls.extend(self.get_urls_for_viewset(prefix, viewset, basename))

        if self.include_root_view:
            view = self.get_api_root_view(api_urls=urls)
            root_url = re_path(r"^$", view, name=self.root_view_name)
            urls.append(root_url)

        if self.include_format_suffixes:
            urls = format_suffix_patterns(urls)

        return urls

    def get_urls_for_viewset(self, prefix, viewset, basename):
        urls = []

        lookup = self.get_lookup_regex(viewset)
        routes = self.get_routes(viewset)

        for route in routes:
            # Only actions which actually exist on the viewset will be bound
            mapping = self.get_method_map(viewset, route.mapping)
            if not mapping:
                continue

            # Build the url pattern
            regex = route.url.format(
                prefix=prefix, lookup=lookup, trailing_slash=self.trailing_slash
            )

            if not prefix and regex[:2] == "^/":
                regex = "^" + regex[2:]

            initkwargs = route.initkwargs.copy()
            initkwargs.update({"basename": basename, "detail": route.detail})

            view = viewset.as_view(mapping, **initkwargs)
            name = route.name.format(basename=basename)
            urls.append(re_path(regex, view, getattr(route, "kwargs", {}), name=name))

        return urls

    def register(self, viewset):  # noqa
        basename = getattr(
            viewset.serializer_class.Meta,
            "basename",
            viewset.serializer_class.Meta.type,
        )
        super().register(basename, viewset, basename)
