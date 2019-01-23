from drf_jsonapi.serializers import ResourceModelSerializer

from .models import Node

from .relationships import (
    NodeParentHandler,
    NodeChildrenHandler,
    NodeLinksToHandler,
    NodeLinksFromHandler,
)


class NodeSerializer(ResourceModelSerializer):
    class Meta:
        model = Node
        type = "node"
        basename = "nodes"
        fields = "name"

    @staticmethod
    def define_relationships():
        return {
            "parent": NodeParentHandler(NodeSerializer),
            "children": NodeChildrenHandler(NodeSerializer),
            "links_to": NodeLinksToHandler(NodeSerializer),
            "links_from": NodeLinksFromHandler(NodeSerializer),
        }
