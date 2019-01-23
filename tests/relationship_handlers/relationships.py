from drf_jsonapi.relationships import RelationshipHandler


class NodeParentHandler(RelationshipHandler):
    many = False
    related_field = "parent"


class NodeChildrenHandler(RelationshipHandler):
    many = True
    related_field = "children"


class NodeLinksToHandler(RelationshipHandler):
    many = True
    related_field = "links_to"


class NodeLinksFromHandler(RelationshipHandler):
    many = True
    related_field = "links_from"
