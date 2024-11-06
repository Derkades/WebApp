import os
import random
import secrets
from tempfile import TemporaryDirectory
import tracemalloc
from typing import Any, cast, override
import unittest
from pathlib import Path

from flask.testing import FlaskClient

from raphson_mp import auth, main, packer, reddit, settings
from raphson_mp.lyrics import AZLyricsFetcher, GeniusFetcher, LrcLibFetcher, PlainLyrics, TimeSyncedLyrics
from raphson_mp.spotify import SpotifyClient

tracemalloc.start()


TEST_USERNAME = 'robin'
TEST_PASSWORD = '1234'

settings.data_dir = Path('./data').resolve()
settings.music_dir = Path('./music').resolve()


class TestFlask(unittest.TestCase):
    client: FlaskClient  # pyright: ignore[reportUninitializedInstanceVariable]

    @override
    def setUp(self):
        app = main.get_app(0, False)
        app.testing = True
        self.client = app.test_client()
        response = self.client.post('/auth/login', data={'username': TEST_USERNAME, 'password': TEST_PASSWORD})
        assert response.status_code == 303

    def test_login_fail(self):
        response = self.client.post('/auth/login', json={'username': TEST_USERNAME, 'password': secrets.token_urlsafe(random.randint(1, 100))})
        assert response.status_code == 403, response.status + response.text

    def test_login_json(self):
        response = self.client.post('/auth/login', json={'username': TEST_USERNAME, 'password': TEST_PASSWORD})
        assert response.status_code == 200
        token = cast(str, response.json['token'])
        assert len(token) > 10

    def test_playlist_list(self):
        response = self.client.get('/playlist/list')
        playlists = cast(Any, response.json)
        playlist = playlists[0]
        assert type(playlist['name']) == str
        assert type(playlist['track_count']) == int
        assert type(playlist['favorite']) == bool
        assert type(playlist['write']) == bool


class TestLyrics(unittest.TestCase):
    client: SpotifyClient  # pyright: ignore[reportUninitializedInstanceVariable]

    def test_lrclib(self):
        # full length cd version
        lyrics = LrcLibFetcher().find('Strong', 'London Grammar', 'If You Wait', 276)
        assert isinstance(lyrics, TimeSyncedLyrics), lyrics
        assert lyrics.text[0].text == 'Excuse me for a while', lyrics.text[0]
        assert lyrics.text[0].start_time == 43.56, lyrics.text[0]

        # music video version
        lyrics = LrcLibFetcher().find('Strong', 'London Grammar', 'If You Wait', 242)
        assert isinstance(lyrics, TimeSyncedLyrics), lyrics
        assert lyrics.text[0].text == 'Excuse me for a while', lyrics.text[0]
        assert lyrics.text[0].start_time == 14.6, lyrics.text[0]

    def test_azlyrics(self):
        lyrics = AZLyricsFetcher().find('Starburster', 'Fontaines D.C.', None, None)
        assert isinstance(lyrics, PlainLyrics)
        assert "I wanna see you alone, I wanna sharp the stone" in lyrics.text, lyrics.text

    def test_genius(self):
        lyrics = GeniusFetcher().find('Give Me One Reason', 'Tracy Chapman', None, None)
        assert isinstance(lyrics, PlainLyrics)
        assert "You know that I called you, I called too many times" in lyrics.text, lyrics.text


class TestPacker(unittest.TestCase):
    def test_packer(self):
        with TemporaryDirectory() as tempdir:
            a = os.urandom(random.randint(0, 1000))
            b = os.urandom(random.randint(0, 1000))
            Path(tempdir, 'a').write_bytes(a)
            Path(tempdir, 'b').write_bytes(b)
            result = packer.pack(Path(tempdir))
            assert result == a + b


class TestReddit(unittest.TestCase):
    def test_search(self):
        image_url = reddit.search('test')
        assert image_url
        assert image_url.startswith('https://'), image_url


class TestPassword(unittest.TestCase):
    def test_hash(self):
        password = secrets.token_urlsafe(random.randint(0, 100))
        notpassword = secrets.token_urlsafe(random.randint(0, 100))
        hash = auth.hash_password(password)
        assert auth._verify_hash(hash, password)  # pyright: ignore[reportPrivateUsage]
        assert not auth._verify_hash(hash, notpassword)  # pyright: ignore[reportPrivateUsage]


if __name__ == '__main__':
    unittest.main()
