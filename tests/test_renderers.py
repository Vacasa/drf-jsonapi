from django.test import TestCase

from drf_jsonapi.renderers import BrowsableAPIRenderer


class BrowsableAPIRendererTestCase(TestCase):

    def test_get_raw_data_form(self):
        self.assertEqual(
            BrowsableAPIRenderer().get_raw_data_form(None, None, None, None),
            None
        )
