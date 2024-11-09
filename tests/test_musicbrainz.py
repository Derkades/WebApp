import time
from unittest import TestCase

from raphson_mp import musicbrainz


class TestMusicBrainz(TestCase):
    def test_correct_release(self):
        time.sleep(1)  # avoid rate limit
        rg_id = musicbrainz._search_release_group('Red Hot Chili Peppers', 'Californication')
        # should find album, not single
        assert rg_id == 'ca5dfcc3-83fb-3eee-9061-c27296b77b2c'

    def test_cover(self):
        time.sleep(1)  # avoid rate limit
        cover = musicbrainz.get_cover('SebastiAn', 'Dancing By Night')
        assert cover
        assert len(cover) > 400000

    def test_metadata(self):
        time.sleep(1)  # avoid rate limit
        metas = list(musicbrainz.get_recording_metadata('a8fe7228-18fc-40d9-80c6-cbfb71d5d03e'))
        assert len(metas) == 2
        for meta in metas:
            assert meta.album in {'The Remixes', 'Dancing By Night'}
            assert meta.year == 2023
            assert 'London Grammar' in meta.artists
            assert 'SebastiAn' in meta.artists
