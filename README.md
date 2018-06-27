# JSON API with Django Rest Framework

[![Maintainability](https://api.codeclimate.com/v1/badges/c2d2715defce75b1dbd8/maintainability)](https://codeclimate.com/github/Vacasa/drf-jsonapi/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/c2d2715defce75b1dbd8/test_coverage)](https://codeclimate.com/github/Vacasa/drf-jsonapi/test_coverage)

## What is this?

This package adds support for the [JSON API](http://jsonapi.org) spec with [Django Rest Framework](http://www.django-rest-framework.org/). It is a collection of base classes that abstract away much of the logic needed to handle requests and responses according to the JSON API spec.

## Features

- Filtering via query params
- Sorting via query params
- Sparse fieldsets
- Resource Relationships
- Compound documents with full linkage
- Pagination (with links)

## What's included?

### `drf_jsonapi.serializers`

- **`DocumentSerializer`** For top-level JSON API documents
- **`ErrorSerializer`** For JSON API errors
- **`ResourceListSerializer`** sub-class of `ListSerializer`
- **`ResourceSerializer`** For serializing/deserializing JSON API resource objects

### `drf_jsonapi.filters`

- **`FilterSet`**: subclass of `django_filters.FilterSet` that parses and validates query params like `filter[is_active]=true` (suitable for filtering `QuerySet` objects)
- **`GenericFilterSet`**: a filter class that parses and validates query params but works with any collection of objects, not just `QuerySet` objects)

### `drf_jsonapi.viewsets`

- **`ViewSet`**: Base ViewSet with validation of params, request body, and serialization according to the JSON API spec.
- **`RelationshipViewSet`**: Base ViewSet for endpoints that deal with relationships between resources
- **`ReadOnlyViewSet`**: Convenience class that includes `mixins.ListMixin`, `mixins.RetrieveMixin`, and `ViewSet`
- **`ReadWriteViewSet`**: Convenience class that includes `mixins.ListMixin`, `mixins.CreateMixin`, `mixins.RetrieveMixin`, `mixins.PartialUpdateMixin`, `mixins.DestroyMixin`, and `ViewSet`
- **`ReadOnlyRelationshipViewSet`**: Convenience class that includes `mixins.RelationshipListMixin`, `mixins.RelationshipRetrieveMixin`, and `RelationshipViewSet`
- **`ReadWriteRelationshipViewSet`**: Convenience class that includes `mixins.RelationshipListMixin`, `mixins.RelationshipCreateMixin`, `mixins.RelationshipPatchMixin`, `mixins.RelationshipRetrieveMixin`, `mixins.RelationshipDestroyMixin`, and `RelationshipViewSet`

### `drf_jsonapi.mixins`

- **`ListMixin`**: Default behavior resource listing with sorting, filtering, paging, sparse fieldsets, and included relationships
- **`CreateMixin`**: Default behavior for creating a resource (`POST`)
- **`RetrieveMixin`**: Default behavior for fetching a single resource by ID
- **`PartialUpdateMixin`**: Default behavior for partial update (`PATCH`) of a single resource
- **`DestoryMixin`**: Default behavior for destorying (`DELETE`) a single resource
- **`RelationshipListMixin`**: Default behavior to listing relationships
- **`RelationshipRetrieveMixin`**: Default behavior for fetching a single relationship
- **`RelationshipCreateMixin`**: Default behavior for creating a relationship
- **`RelationshipPatchMixin`**: Default behavior for updating relationships
- **`RelationshipDestroyMixin`**: Default behavior for deleting a relationship

## What's missing?

- Django Rest Framework ships with UI elements to enable `POST`, `PATCH`, and `DELETE` on appropriate endpoints. These are currently disabled because they are broken, and not a priority to be fixed anytime soon.

## Quickstart Guide

This guide assumes you have a resource (we'll assume the resource is a Django Model but it could be any object) and you want to expose API endpoints for users to interact (CRUD + relationship management) with the resources.

NOTE: This guide does NOT include any authentication or access control. That is outside of the scope of this document but since this package is built on Django Rest Framework all of the same methods apply.

### Serializers

The first step is to create a Serializer class for your resource. If your resource is a Django model you can sub-class `drf_jsonapi.serializers.ResourceModelSerializer`. Otherwise, you'll want to sub-class `drf_jsonapi.serializers.ResourceSerializer`. The big difference between the two is that `ResourceModelSerializer` can automatically create the serializer fields based on the model definition. If you use `ResourceSerializer` you'll have to define the fields manually.

#### Serializer Meta options

Most of the behavior for the Serializer is defined in the `Meta` class. This follows Django Rest Framework conventions. The following Meta attributes are supported:

- **`type`** (string): Defines the `jsonapi` resource type for this resource.
- **`base_path`** (string): The base path for this resource. This is used to generate links.
- **`model`** (class): The model class. Used for auto-generating fields (for `ResourceModelSerializer` only)
- **`fields`** (tuple | list of strings): The fields that should be exposed via the API.
- **`read_only_fields`** (tuple | list of strings): Defines the fields that should be exposed but should NOT be included in request bodies.
- **`relationships`** (dict): This is an optional attribute that defines the relationships for the resource. The key is the name of the relationship and the value is the Serializer class for the related resources (or a string representing the absolute import path to the class)

#### Relationships

If you define any relationships in the Meta class of your serializer you need to define methods for fetching those relaitonships and define a method for getting the serializer for the related resource. These methods exist in the base `RelationshipHandler` class in `relationships.py` as abstract (not implemented) classes `get_related` and `get_serializer_class`. For example: If you define a relationship called `roles` you'll need to override the method `get_related(self, instance)` to fetch that relationship on the base instance.  The resource instance is passed in to this method and the return type should be the related resource or a collection of related resources.

Additionally defined abstract methods in the RelationshipHandler include `add_related`, `set_related`, and `remove_related` for the corresponding `POST`, `PATCH`, and `DELETE` requests.

Further, RelationshipHandler comes equiped with validation via the `validate` method, and links to the related resources via the `build_relationship_links(self, base_serializer, relation, resource)` method. Once the `build_relationship_links` method has been called the `get_links` method will return the built list of links.

### Views

The `jsonapi` class uses the Django Rest Framework `ViewSet` classes. For convenience there are two base classes you can extend: `ReadOnlyViewSet` and `ReadWriteViewSet`. These classes include the necessary mixins to define basic default behavior.

#### ViewSet class attributes

For your custom ViewSet to work properly you'll need to define some class-level attributes:

- **`view_name_prefix`** This is a human-readable string that is used in the browsable API.
- **`lookup_field`** The field on the resource object that is used as the ID for path lookups. This is OPTIONAL and defaults to `pk`. You should only need to override this if you're using a non-model resource.
- **`lookup_value_regex`** This is OPTIONAL and should only be needed if you need to support non-standard lookup patterns.
- **`serializer_class`** REQUIRED. This is the serializer class for the resource
- **`filter_class`** OPTIONAL. This is the Filter class for filtering list endpoints.
- **`collection`** This is the default resource collection (typically a QuerySet) If you need to declare this dynamically based on the request (to limit the values based on the user, for example) you can define a `get_collection(self, request, *args, **kwargs)` instance method.

### Filters

To support filtering of data via query params like `filter[field]=value` you can define custom FilterSet classes and attach them to your view via the `filter_class` attribute. These FilterSet classes are based on the `django_filters.FilterSet` classes but have custom validation and translation of the query params to support the syntax.

There are two base classes for FilterSet, `drf_jsonapi.filters.FilterSet` and `drf_jsonapi.filters.GenericFilterSet`. The one you extend depends on whether or not the underlying resource is a Django model. For Django models use `FilterSet`. This is simply a sub-class of `django_filters.FilterSet` with additional validation and translation. It assumes that the filter is working with a QuerySet. For non-model filtering use `GenericFilterSet`. This class is optimized for working with lists of resources.
