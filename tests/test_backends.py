from django.test import TestCase

from drf_jsonapi.backends import DjangoFilterBackend
from drf_jsonapi.filters import FilterSet

from .mocks import TestModel


class TestFilterSet(FilterSet):
    class Meta:
        model = TestModel
        fields = {
            'id': ['exact'],
            'name': ['exact', 'iexact', 'contains', 'icontains', 'startswith'],
            'is_active': ['exact']
        }


class DjangoFilterBackendTestCase(TestCase):

    def test_get_schema_fields(self):

        class FakeView(object):
            filter_class = TestFilterSet

        backend = DjangoFilterBackend()
        fields = backend.get_schema_fields(FakeView())
        field_names = {field.name for field in fields}
        expected_field_names = {
            'filter[id]',
            'filter[name]',
            'filter[name][iexact]',
            'filter[name][contains]',
            'filter[name][icontains]',
            'filter[name][startswith]',
            'filter[is_active]'
        }
        self.assertEqual(field_names, expected_field_names)

    def test_get_schema_fields_no_filter_class(self):

        class FakeView(object):
            pass

        backend = DjangoFilterBackend()
        fields = backend.get_schema_fields(FakeView())
        self.assertEqual(fields, [])
