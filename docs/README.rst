# JSONAPI with Django Rest Framework

## What is this?

This package adds support for the JSONAPI spec with Django Rest Frameowork. It
is a collection of base classes that abstract away much of the logic needed to 
handle requests and responses according to the JSONAPI spec.

## Features
1. Filtering via query params
2. Sorting via query params
3. Sparse fieldsets
4. Resource Relationships
5. Compound documents with full linkage
6. Pagination (with links)

## What's included?

### drf_jsonapi.serializers
- **DocumentSerializer**: For top-level JSONAPI documents
- **ErrorSerializer**: For JSONAPI errors
- **ResourceListSerializer**: sub-class of ListSerializer
- **ResourceSerializer**: For serializing/deserializing JSONAPI resource objects

### drf_jsonapi.filters
- **FilterSet**: subclass of django_filters.FilterSet that parses and validates 
query params like `filter[is_active]=true` (suitable for filtering QuerySets)
- **GenericFilterSet**: a filter class that parses and validates query params but works with any
collection of objects, not just QuerySets)

### drf_jsonapi.viewsets
- **ViewSet**: Base ViewSet with validation of params, request body, and serialization according to the jsonAPI spec.
- **RelationshipViewSet**: Base ViewSet for endpoints that deal with relationships between resources
- **ReadOnlyViewSet**: Convenience class that includes mixins.ListMixin, mixins.RetrieveMixin, and ViewSet
- **ReadWriteViewSet**: Convenience class that includes mixins.ListMixin, mixins.CreateMixin, mixins.RetrieveMixin, mixins.PartialUpdateMixin, mixins.DestroyMixin, and ViewSet
- **ReadOnlyRelationshipViewSet**: Convenience class that includes mixins.RelationshipListMixin, mixins.RelationshipRetrieveMixin, and RelationshipViewSet
- **ReadWriteRelationshipViewSet**: Convenience class that includes mixins.RelationshipListMixin, mixins.RelationshipCreateMixin, mixins.RelationshipPatchMixin, mixins.RelationshipRetrieveMixin, mixins.RelationshipDestroyMixin, and RelationshipViewSet

### drf_jsonapi.mixins
- **ListMixin**: Default behavior resource listing with sorting, filtering, paging, sparse fieldsets, and included relationships
- **CreateMixin**: Default behavior for creating a resource (POST)
- **RetrieveMixin**: Default behavior for fetching a single resource by ID
- **PartialUpdateMixin**: Default behavior for partial update (PATCH) of a single resource
- **DestoryMixin**: Default behavior for destorying (DELETE) a single resource
- **RelationshipListMixin**: Default behavior to listing relationships
- **RelationshipRetrieveMixin**: Default behavior for fetching a single relationship
- **RelationshipCreateMixin**: Default behavior for creating a relationship
- **RelationshipPatchMixin**: Default behavior for updating relationships
- **RelationshipDestroyMixin**: Default behavior for deleting a relationship

# Quickstart Guide

This guide assumes you have a resource (we'll assume the resource is a Django Model but it could be any object) and you want to expose API endpoints for users to interact (CRUD + relationship management) with the resources.

NOTE: This guide does NOT include any authentication or access control. That is outside of the scope of this document but since the drf_jsonapi package is built on Django Rest Framework all of the same methods apply.

## Serializers

The first step is to create a Serializer class for your resource. If your resource is a Django model you can sub-class `jsonapi.serializers.ResourceModelSerializer`. Otherwise, you'll want to sub-class `drf_jsonapi.serializers.ResourceSerializer`. The big difference between the two is that `ResourceModelSerializer` can automatically create the serializer fields based on the model definition. If you use `ResourceSerializer` you'll have to define the fields manually.

### Serializer Meta options

Most of the behavior for the Serializer is defined in the Meta class. This follows Django Rest Framework conventions. The following Meta attributes are supported:

- **type** (string): Defines the jsonapi resource type for this resource.
- **base_path** (string): The base path for this resource. This is used to generate links.
- **model** (class): The model class. Used for auto-generating fields (for `ResourceModelSerializer` only)
- **fields** (tuple|list of strings): The fields that should be exposed via the API.
- **read_only_fields** (tuple| list of strings): Defines the fields that should be exposed but should NOT be included in request bodies.
- **relationships** (dict): This is an optional attribute that defines the relationships for the resource. The key is the name of the relationship and the value is the Serializer class for the related resources (or a string representing the absolute import path to the class)

#### Relationships

If you define any relationships in the Meta class of your serializer you need to define methods for fetching those relaitonships and define a method for getting the serializer for the related resource. These methods exist in the base RelationshipHandler class in relationships.py as abstract (not implemented) classes get_related and get_serializer_class. For example: If you define a relationship called `roles` you'll need to override the method `get_related(self, instance)` to fetch that relationship on the base instance.  The resource instance is passed in to this method and the return type should be the related resource or a collection of related resources. 

Additionally defined abstract methods in the RelationshipHandler include add_related, set_related, and remove_related for the corresponding post, put, and delete requests. 

Further, RelationshipHandler comes equiped with validation via the validate method, and links to the related resources via the build_relationship_links(self, base_serializer, relation, resource) method. Once the build_relationship_links method has been called the get_links method will return the built list of links.

## Views

The jsonapi class uses Django Rest Frameworks ViewSet classes. For convenience there are two base classes you can extend: `ReadOnlyViewSet` and `ReadWriteViewSet`. These classes include the necessary mixins to define basic default behavior.

### ViewSet class attributes

For your custom ViewSet to work properly you'll need to define some class-level attributes:

- **view_name_prefix**: This is a human-readable string that is used in the browsable API.
- **lookup_field**: The field on the resource object that is used as the ID for path lookups. This is OPTIONAL and defaults to `pk`. You should only need to override this if you're using a non-model resource.
- **lookup_value_regex**: This is OPTIONAL and should only be needed if you need to support non-standard lookup patterns.
- **serializer_class**: REQUIRED. This is the serializer class for the resource
- **filter_class**: OPTIONAL. This is the Filter class for filtering list endpoints.
- **collection**: This is the default resource collection (typically a queryset) If you need to declare this dynamically based on the request (to limit the values based on the user, for example) you can define a `get_collection(self, request, *args, **kwargs)` instance method.

## Filters

To support filtering of data via query params like `filter[field]=value` you can define custom FilterSet classes and attach them to your view via the `filter_class` attribute. These FilterSet classes are based on the `django_filters` FilterSets but have custom validation and translation of the query params to support the syntax.

There are two base classes for FilterSets, `drf_jsonapi.filters.FilterSet` and `drf_jsonapi.filters.GenericFilterSet`. The one you extend depends on whether or not the underlying resource is a Django model. For Django models use `FilterSet` this is simply a sub-class of `django_filters.FilterSet` with additional validation and translation. It assumes that the filter is working with a queryset. For non-model filtering use `GenericFilterSet`. This class is optimized for working with lists of resources.

