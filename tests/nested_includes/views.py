from drf_jsonapi.viewsets import ReadWriteViewSet

from .models import Trunk, Leaf

from .serializers import TrunkSerializer, LeafSerializer


class TrunkViewSet(ReadWriteViewSet):
    view_name_prefix = "Trunk"
    serializer_class = TrunkSerializer

    allowed_includes = ("branches", "branches.leaves")

    def get_collection(self, request):
        return Trunk.objects.all().order_by("id")


class LeafViewSet(ReadWriteViewSet):
    view_name_prefix = "Leaf"
    serializer_class = LeafSerializer

    allowed_includes = ("branch", "branch.trunk")

    def get_collection(self, request):
        return Leaf.objects.all().order_by("id")
