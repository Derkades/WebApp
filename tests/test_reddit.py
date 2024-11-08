from unittest import TestCase

from raphson_mp import reddit


class TestReddit(TestCase):
    def test_search(self):
        image_url = reddit.search('test')
        assert image_url
        assert image_url.startswith('https://'), image_url
