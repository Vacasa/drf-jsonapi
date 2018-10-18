from django.test import TestCase
from django.db import models

from rest_framework.test import APIRequestFactory

from drf_jsonapi.objects import Error
from drf_jsonapi.filters import FilterSet, GenericFilterSet
from django_filters.filters import CharFilter

from .mocks import TestModel


class TestFilterSet(FilterSet):
    custom__filter = CharFilter()

    class Meta:
        model = TestModel
        fields = {
            'id': ['exact'],
            'name': ['exact', 'iexact', 'contains', 'icontains', 'startswith'],
            'is_active': ['exact']
        }


class FilterSetTestCase(TestCase):

    def test_init(self):
        factory = APIRequestFactory()
        request = factory.get('/tests/?filter[id]=1&filter[name][contains]=foobar')
        TestFilterSet(request.GET, TestModel.objects.all())

    def test_invalid_filter(self):
        factory = APIRequestFactory()
        request = factory.get('/tests/?filter[foo]=bar')
        with self.assertRaises(Error):
            TestFilterSet(request.GET, TestModel.objects.all())

    def test_validate_boolean_value(self):
        factory = APIRequestFactory()
        request = factory.get('/tests/?filter[is_active]=true')
        TestFilterSet(request.GET, TestModel.objects.all())

    def test_dot_separated_filter(self):
        factory = APIRequestFactory()
        request = factory.get('/tests/?filter[custom.filter]=true')
        TestFilterSet(request.GET, TestModel.objects.all())

    def test_validate_invalid_boolean_value(self):
        factory = APIRequestFactory()
        request = factory.get('/tests/?filter[is_active]=sure')
        with self.assertRaises(Error):
            TestFilterSet(request.GET, TestModel.objects.all())

    def test_collection(self):
        factory = APIRequestFactory()
        request = factory.get('/tests/?filter[is_active]=true')
        filterset = TestFilterSet(request.GET, TestModel.objects.all())
        self.assertIsInstance(filterset.collection, models.QuerySet)


class TestGenericFilterSet(GenericFilterSet):
    class Meta:
        fields = {
            'name': ['exact'],
            'id': ['exact']
        }

    def filter_id(self, item, value):
        return item['id'] == int(value)

    def filter_name(self, item, value):
        return item['name'] == value


class GenericFilterSetTestCase(TestCase):

    def setUp(self):
        self.collection = [
            {
                'id': 1,
                'name': 'foo'
            },
            {
                'id': 2,
                'name': 'bar'
            },
            {
                'id': 3,
                'name': 'biz'
            }
        ]

    def test_init(self):
        factory = APIRequestFactory()
        request = factory.get('/tests/?filter[id]=1')
        filterset = TestGenericFilterSet(request.GET, self.collection)
        collection = filterset.collection
        self.assertEquals(collection, [
            {
                'id': 1,
                'name': 'foo'
            }
        ])
