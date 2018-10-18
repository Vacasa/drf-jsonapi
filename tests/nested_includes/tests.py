from django.test import TestCase, override_settings

from .models import Trunk, Branch, Leaf

@override_settings(ROOT_URLCONF = 'tests.nested_includes.urls')
class NestedIncludesTestCase(TestCase):

    def setUp(self):
        self.trunk = Trunk.objects.create(name="Trunk")
        self.branch = Branch.objects.create(name="Branch", trunk=self.trunk)
        self.leaf = Leaf.objects.create(name="Leaf", branch=self.branch)

    def test_trunks_include_leaves(self):
        response = self.client.get('/trunks?include=branches.leaves')
        self.assertEquals(
            len(response.data['data'][0]['relationships']['branches']['data']),
            1
        )
        self.assertEquals(
            len(response.data['included']),
            2
        )

    def test_leaves_include_trunk(self):
        response = self.client.get('/leaves?include=branch.trunk')
        self.assertEquals(
            response.data['data'][0]['relationships']['branch']['data']['type'],
            'branch'
        )
        self.assertEquals(
            len(response.data['included']),
            2
        )

    def test_invalid_include(self):
        response = self.client.get('/leaves?include=foo.bar')
        self.assertEquals(response.status_code, 400)
