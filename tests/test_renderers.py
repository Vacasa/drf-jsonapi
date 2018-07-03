from django.test import TestCase

from drf_jsonapi.renderers import BrowsableAPIRenderer, JSONRenderer


class BrowsableAPIRendererTestCase(TestCase):

    def test_get_raw_data_form(self):
        self.assertEqual(
            BrowsableAPIRenderer().get_raw_data_form(None, None, None, None),
            None
        )

class JSONRendererTestCase(TestCase):

    def test_get_raw_data_form(self):
        renderer = JSONRenderer()
        render_data = {'data': {'stuff': 'things'}}
        print(dir(renderer))
        # self.assertEqual(
        #     JSONRenderer().render(render_data),
        #     None
        # )
        self.assertEqual(
            JSONRenderer().format,
            None
        )
