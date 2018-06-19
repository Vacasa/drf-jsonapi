from rest_framework_nested.routers import NestedSimpleRouter


class RelationshipRouter(NestedSimpleRouter):
    """
    Subclass a NestedSimpleRouter - adding patch mapping
    """

    def __init__(self, *args, **kwargs):
        """
        Adds a patch element to route mapping

        :param drf_jsonapi.routers.RelationshipRouter self: This object
        """

        self.routes[0].mapping['patch'] = 'patch'
        self.routes[0].mapping['delete'] = 'delete'
        super().__init__(*args, **kwargs)
