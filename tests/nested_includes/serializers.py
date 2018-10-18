from drf_jsonapi.serializers import ResourceModelSerializer

from .models import Trunk, Branch, Leaf

from . import relationships

class TrunkSerializer(ResourceModelSerializer):

    class Meta:
        model = Trunk
        type = "trunk"
        base_path = "/trunks"
        fields = (
            'name',
        )
        relationships = {
            "branches": relationships.TrunkBranchesHandler()
        }


class BranchSerializer(ResourceModelSerializer):

    class Meta:
        model = Branch
        type = "branch"
        base_path = "/branches"
        fields = (
            'name',
        )
        relationships = {
            "leaves": relationships.BranchLeavesHandler(),
            "trunk": relationships.BranchTrunkHandler()
        }


class LeafSerializer(ResourceModelSerializer):

    class Meta:
        model = Leaf
        type = "leaf"
        base_path = "/leafs"
        fields = (
            'name',
        )
        relationships = {
            "branch": relationships.LeafBranchHandler()
        }
