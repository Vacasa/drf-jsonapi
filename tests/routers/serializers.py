from drf_jsonapi.serializers import ResourceModelSerializer

from .models import Trunk, Branch, Leaf, Root

from . import relationships


class RootSerializer(ResourceModelSerializer):
    class Meta:
        model = Root
        type = "root"
        basename = "roots"
        fields = (("name"),)


class TrunkSerializer(ResourceModelSerializer):
    class Meta:
        model = Trunk
        type = "trunk"
        basename = "trunks"
        fields = ("name",)

    @staticmethod
    def define_relationships():
        return {
            "branches": relationships.TrunkBranchesHandler(BranchSerializer),
            "roots": relationships.TrunkRootRelationshipHandler(RootSerializer),
        }


class BranchSerializer(ResourceModelSerializer):
    class Meta:
        model = Branch
        type = "branch"
        basename = "branches"
        fields = ("name",)

    @staticmethod
    def define_relationships():
        return {
            "leaves": relationships.BranchLeavesHandler(LeafSerializer),
            "trunk": relationships.BranchTrunkHandler(TrunkSerializer),
        }


class LeafSerializer(ResourceModelSerializer):
    class Meta:
        model = Leaf
        type = "leaf"
        basename = "leaves"
        fields = ("name",)

    @staticmethod
    def define_relationships():
        return {
            "branch": relationships.LeafBranchHandler(BranchSerializer, read_only=True)
        }
