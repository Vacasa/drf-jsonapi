from drf_jsonapi.relationships import RelationshipHandler


class TrunkBranchesHandler(RelationshipHandler):
    many = True

    def get_related(self, resource, request):
        return resource.branches.all().order_by("id")


class BranchLeavesHandler(RelationshipHandler):
    many = True

    def get_related(self, resource, request):
        return resource.leaves.all().order_by("id")


class LeafBranchHandler(RelationshipHandler):
    many = False

    def get_related(self, resource, request):
        return resource.branch


class BranchTrunkHandler(RelationshipHandler):
    many = False

    def get_related(self, resource, request):
        return resource.trunk
