from drf_jsonapi.serializers import ResourceModelSerializer

from .models import Node

from .relationships import (
    NodeParentHandler,
    NodeChildrenHandler,
    NodeLinksToHandler,
    NodeLinksFromHandler
)

class NodeSerializer(ResourceModelSerializer):

    class Meta:
        model = Node
        type = "node"
        base_path = "/nodes"
        fields = (
            'name'
        )
        relationships = {
            'parent': NodeParentHandler(),
            'children': NodeChildrenHandler(),
            'links_to': NodeLinksToHandler(),
            'links_from': NodeLinksFromHandler()
        }
