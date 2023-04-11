import logging
from sqlite3 import Connection
import traceback

import requests
from requests.exceptions import RequestException

import settings
import db
import logconfig


log = logging.getLogger('app.offline')


class OfflineSync:
    db_offline: Connection
    db_music: Connection
    base_url: str
    token: str | None = None

    def __init__(self, db_offline: Connection, db_music: Connection):
        self.db_offline = db_offline
        self.db_music = db_music
        self.set_base_url()
        self.set_token()

    def set_base_url(self):
        row = self.db_offline.execute("SELECT value FROM settings WHERE key='sync_url'").fetchone()
        if row:
            self.base_url, = row
        else:
            log.info('No sync server is configured')
            self.base_url = input('Enter URL: ')
            self.db_offline.execute("INSERT INTO settings (key, value) VALUES ('sync_url', ?)",
                                    (self.base_url,))
            self.db_offline.commit()

    def request_get(self, route: str):
        response = requests.get(self.base_url + route,
                                headers={'Cookie': 'token=' + self.token,
                                         'User-Agent': 'MusicPlayer Offline'})
        return response.json()

    def request_post(self, route: str, data):
        headers = {'User-Agent': 'MusicPlayer Offline'}
        if self.token is not None:
            headers['Cookie'] = 'token=' + self.token
        response = requests.post(self.base_url + route,
                                 json=data,
                                 headers=headers)
        print(response.status_code, response.text)
        return response.json()

    def set_token(self):
        row = self.db_offline.execute("SELECT value FROM settings WHERE key='sync_token'").fetchone()
        if row:
            self.token, = row
            try:
                self.request_get('/get_csrf')
                log.info('Authentication token is valid')
            except RequestException:
                traceback.print_exc()
                log.info('Error testing authentication token. Please log in again.')
                self.login_prompt()
                self.set_token()
        else:
            log.info('No authentication token stored, please log in')
            self.login_prompt()
            self.set_token()

    def login_prompt(self):
        username = input('Enter username: ')
        password = input('Enter password: ')

        try:
            response = self.request_post('/login',
                                         {'username': username,
                                          'password': password})
        except RequestException:
            traceback.print_exc()
            log.info('Error during log in, please try again.')
            self.login_prompt()
            return

        token = response['token']
        self.db_offline.execute("INSERT INTO settings (key, value) VALUES ('sync_token', ?)",
                                (token,))
        self.db_offline.commit()
        log.info('Logged in successfully')

    def sync_tracks(self):
        log.info('Deleting existing track data')
        self.db_music.execute('DELETE FROM playlist')

        log.info('Downloading track list')
        response = self.request_get('/track_list')

        for playlist in response['playlists']:
            log.info('Processing playlist %s', playlist['name'])
            self.db_music.execute('INSERT INTO playlist VALUES (?)',
                                  (playlist['name'],))

            for track in playlist['tracks']:
                self.db_music.execute(
                    """
                    INSERT INTO track (path, playlist, duration, title, album,
                                       album_artist, year, mtime)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (track['path'], playlist['name'], track['duration'], track['title'],
                     track['album'], track['album_artist'], track['year'], track['mtime'])
                )

                if track['artists']:
                    for artist in track['artists']:
                        self.db_music.execute(
                            'INSERT INTO track_artist (track, artist) VALUES (?, ?)',
                            (track['path'], artist)
                        )

                # TODO tags


def main():
    if not settings.offline_mode:
        return

    with db.connect() as db_music, db.offline() as db_offline:
        log.info('Starting sync')
        sync = OfflineSync(db_offline, db_music)
        sync.sync_tracks()


if __name__ == '__main__':
    logconfig.apply()
    main()
