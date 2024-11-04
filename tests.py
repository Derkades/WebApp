import random
import secrets
import tracemalloc
import unittest
from pathlib import Path

from flask.testing import FlaskClient

from raphson_mp import main, settings

tracemalloc.start()


TEST_USERNAME = 'robin'
TEST_PASSWORD = '1234'


class TestFlask(unittest.TestCase):
    client: FlaskClient

    def setUp(self):
        settings.data_dir = Path('./data').resolve()
        settings.music_dir = Path('./music').resolve()
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
        self.token: str = response.json['token']
        assert len(self.token) > 10

    def test_playlist_list(self):
        response = self.client.get('/playlist/list')
        playlists = response.json
        assert type(playlists) == list
        playlist = playlists[0]
        assert type(playlist['name']) == str
        assert type(playlist['track_count']) == int
        assert type(playlist['favorite']) == bool
        assert type(playlist['write']) == bool

if __name__ == '__main__':
    unittest.main()
