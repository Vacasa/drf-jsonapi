import re
from collections import defaultdict
from drf_yasg.generators import OpenAPISchemaGenerator as _OpenAPISchemaGenerator

path_pattern = re.compile(r"{\w+}")


class OpenAPISchemaGenerator(_OpenAPISchemaGenerator):
    """
    This class iterates over all registered API endpoints and returns an appropriate OpenAPI 2.0 compliant schema.
    """

    def get_endpoints(self, request):
        """
        Iterate over all the registered endpoints in the API and return a fake view with the right parameters.

        :param drf_jsonapi.generators.OpenAPISchemaGenerator self: This object
        :param rest_framework.request.Request request: request to bind to the endpoint views
        :return: {path: (view_class, list[(http_method, view_instance)])
        :rtype: dict
        """

        enumerator = self.endpoint_enumerator_class(
            self._gen.patterns, self._gen.urlconf, request=request
        )
        endpoints = enumerator.get_api_endpoints()

        view_paths = defaultdict(list)
        view_cls = {}

        for path, method, callback in endpoints:
            view = self.create_view(callback, method, request)
            path = self._gen.coerce_path(path, method, view)
            path = path_pattern.sub("{id}", path)
            view_paths[path].append((method, view))
            view_cls[path] = callback.cls

        return {path: (view_cls[path], methods) for path, methods in view_paths.items()}
