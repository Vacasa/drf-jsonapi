from drf_jsonapi.relationships import RelationshipHandler


class NodeParentHandler(RelationshipHandler):
    many = False
    serializer_class = 'tests.relationship_handlers.serializers.NodeSerializer'
    related_field = 'parent'


class NodeChildrenHandler(RelationshipHandler):
    many = True
    serializer_class = 'tests.relationship_handlers.serializers.NodeSerializer'
    related_field = 'children'


class NodeLinksToHandler(RelationshipHandler):
    many = True
    serializer_class = 'tests.relationship_handlers.serializers.NodeSerializer'
    related_field = 'links_to'


class NodeLinksFromHandler(RelationshipHandler):
    many = True
    serializer_class = 'tests.relationship_handlers.serializers.NodeSerializer'
    related_field = 'links_from'
