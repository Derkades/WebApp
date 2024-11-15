from pathlib import Path
import random
import secrets
from typing import Any, cast, override
from unittest import TestCase
from flask.testing import FlaskClient

from raphson_mp import auth, main, settings, db


TEST_USERNAME: str = 'autotest'
TEST_PASSWORD: str = secrets.token_urlsafe()

settings.data_dir = Path('./data').resolve()
settings.music_dir = Path('./music').resolve()


def create_test_user():
    with db.connect() as conn:
        conn.execute('DELETE FROM user WHERE username = ?', (TEST_USERNAME,))
        hash = auth.hash_password(TEST_PASSWORD)
        conn.execute("INSERT INTO user (username, password) VALUES (?, ?)", (TEST_USERNAME, hash))


class TestFlask(TestCase):
    client: FlaskClient  # pyright: ignore[reportUninitializedInstanceVariable]
    csrf: str  # pyright: ignore[reportUninitializedInstanceVariable]

    @override
    def setUp(self):
        create_test_user()
        app = main.get_app()
        app.testing = True
        self.client = app.test_client()
        response = self.client.post('/auth/login', data={'username': TEST_USERNAME, 'password': TEST_PASSWORD})
        assert response.status_code == 303
        response = self.client.get('/auth/get_csrf')
        assert response.status_code == 200
        self.csrf = response.json['token']

    # --------------- ACCOUNT --------------- #

    def _db_nickname(self) -> None:
        with db.connect(read_only=True) as conn:
            return conn.execute('SELECT nickname FROM user WHERE username=?', (TEST_USERNAME,)).fetchone()[0]

    # def test_change_nickname(self):
    #     response = self.client.post('/account/change_nickname', data={'nickname': '🐢', 'csrf': self.csrf})
    #     assert response.status_code == 303, (response.status_code, response.text)
    #     assert self._db_nickname() == '🐢'

    def _db_password_hash(self) -> str:
        with db.connect(read_only=True) as conn:
            return conn.execute('SELECT password FROM user WHERE username=?', (TEST_USERNAME,)).fetchone()[0]

    def test_change_password(self):
        initial_hash= self._db_password_hash()

        # wrong current_password
        response = self.client.post('/account/change_password',
                                    data={'current_password': TEST_PASSWORD + 'a',
                                          'new_password': 'new_password',
                                          'repeat_new_password': 'new_password',
                                          'csrf': self.csrf})
        assert response.status_code == 400
        assert self._db_password_hash() == initial_hash  # password should not have changed

        # wrong repeat_new_password
        response = self.client.post('/account/change_password',
                                    data={'current_password': TEST_PASSWORD,
                                          'new_password': 'new_password',
                                          'repeat_new_password': 'new_password2',
                                          'csrf': self.csrf})
        assert response.status_code == 400
        assert self._db_password_hash() == initial_hash  # password should not have changed

        # correct
        response = self.client.post('/account/change_password',
                                    data={'current_password': TEST_PASSWORD,
                                          'new_password': 'new_password',
                                          'repeat_new_password': 'new_password',
                                          'csrf': self.csrf})
        assert response.status_code == 303
        assert self._db_password_hash() != initial_hash  # password should not have changed

        # restore initial password hash
        with db.connect() as conn:
            conn.execute('UPDATE user SET password = ? WHERE username = ?', (initial_hash, TEST_USERNAME,))

    # --------------- AUTH --------------- #

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
