class ResourceIdentifierSerializer:
    pass


def resource_identifier(serializer_class):
    """
    Wraps a ResourceSerializer class and overrides to_representation
    to return a JSON API Resource Identifier
    See: http://jsonapi.org/format/#document-resource-identifier-objects

    :param rest_framework.serializers.SerializerMetaclass serializer_class: A ResourceSerializer object
    :return: A SerializerMetaclass object
    :rtype: rest_framework.serializers.SerializerMetaclass
    """

    # TODO: Validate serializer_class is sub_class of ResourceSerializer
    class ResourceIdentifier(ResourceIdentifierSerializer, serializer_class):
        """
        Creates a representation of an model instance
        """

        def to_representation(self, instance):
            """
            Creates a JSON-API Resource Identifier from a model instance

            :param self: This object instance
            :param instance: A model instance
            :return: A JSON-API Resource Identifier dictionary representing a model instance
            :rtype: dict
            """

            return {"type": self.Meta.type, "id": self.get_id(instance)}

    return ResourceIdentifier
