from unittest import TestCase

from raphson_mp import music  # noqa: F401: required to prevent import loop
from raphson_mp import metadata


class TestMetadata(TestCase):
    def test_split(self):
        assert metadata._split_meta_list('hello;hello2 ; hello3') == ['hello', 'hello2', 'hello3']

    def test_ad(self):
        assert metadata._has_advertisement('djsoundtop.com')
        assert not metadata._has_advertisement('hello')

    def test_sort(self):
        assert metadata.sort_artists(['A', 'B'], 'B') == ['B', 'A']
