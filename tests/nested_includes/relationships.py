from drf_jsonapi.relationships import RelationshipHandler


class TrunkBranchesHandler(RelationshipHandler):
    many = True

    def get_serializer_class(self):
        from .serializers import BranchSerializer
        return BranchSerializer

    def get_related(self, instance):
        return instance.branches.all().order_by('id')


class BranchLeavesHandler(RelationshipHandler):
    many = True

    def get_serializer_class(self):
        from .serializers import LeafSerializer
        return LeafSerializer

    def get_related(self, instance):
        return instance.leaves.all().order_by('id')


class LeafBranchHandler(RelationshipHandler):
    many = False

    def get_serializer_class(self):
        from .serializers import BranchSerializer
        return BranchSerializer

    def get_related(self, instance):
        return instance.branch


class BranchTrunkHandler(RelationshipHandler):
    many = False

    def get_serializer_class(self):
        from .serializers import TrunkSerializer
        return TrunkSerializer

    def get_related(self, instance):
        return instance.trunk
