import logging
from sqlite3 import Connection
import traceback
from urllib.parse import quote as urlencode

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
                                         'User-Agent': settings.user_agent})
        return response

    def request_post(self, route: str, data):
        headers = {'User-Agent': settings.user_agent}
        if self.token is not None:
            headers['Cookie'] = 'token=' + self.token
        response = requests.post(self.base_url + route,
                                 json=data,
                                 headers=headers)
        return response

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

        token = response.json()['token']
        self.db_offline.execute("INSERT INTO settings (key, value) VALUES ('sync_token', ?)",
                                (token,))
        self.db_offline.commit()
        log.info('Logged in successfully')

    def _download_track_content(self, path: str):
        log.info('Downloading audio data')
        response = self.request_get('/get_track?type=webm_opus_high&path=' + urlencode(path))
        assert response.status_code == 200
        music_data = response.content
        log.info('Downloading album cover')
        response = self.request_get('/get_album_cover?quality=high&path=' + urlencode(path))
        assert response.status_code == 200
        cover_data = response.content
        log.info('Downloading lyrics')
        response = self.request_get('/get_lyrics?path=' + urlencode(path))
        assert response.status_code == 200
        lyrics_json = response.text
        self.db_offline.execute(
            """
            INSERT INTO content (path, music_data, cover_data, lyrics_json)
            VALUES(:path, :music_data, :cover_data, :lyrics_json)
            ON CONFLICT (path) DO UPDATE SET
                music_data = :music_data, cover_data = :cover_data, lyrics_json = :lyrics_json
            """,
            {'path': path,
             'music_data': music_data,
             'cover_data': cover_data,
             'lyrics_json': lyrics_json})

    def _update_track(self, track):
        self._download_track_content(track['path'])

        log.info('Updating metadata')

        self.db_music.execute('UPDATE track SET duration=?, title=?, album=?, album_artist=?, year=?, mtime=?',
                              (track['duration'], track['title'], track['album'], track['album_artist'], track['year']))

        self.db_music.execute('DELETE FROM track_artist WHERE track=?', (track['path'],))

        if track['artists']:
            insert = [(track['path'], artist) for artist in track['artists']]
            self.db_music.executemany('INSERT INTO track_artist (track, artist) VALUES (?, ?)', insert)

    def _insert_track(self, playlist, track):
        self._download_track_content(track['path'])

        log.info('Storing metadata')

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
            insert = [(track['path'], artist) for artist in track['artists']]
            self.db_music.executemany('INSERT INTO track_artist (track, artist) VALUES (?, ?)', insert)

    def _prune_tracks(self, track_paths: set[str]):
        rows = self.db_music.execute('SELECT path FROM track').fetchall()
        for path, in rows:
            if path not in track_paths:
                log.info('delete: %s', path)
                self.db_offline.execute('DELETE FROM content WHERE path=?',
                                        (path,))
                self.db_music.execute('DELETE FROM track WHERE path=?',
                                      (path,))

    def sync_tracks(self):
        log.info('Downloading track list')
        response = self.request_get('/track_list').json()

        track_paths: set[str] = set()

        for playlist in response['playlists']:
            log.info('Processing playlist %s', playlist['name'])
            self.db_music.execute('INSERT INTO playlist VALUES (?) ON CONFLICT (path) DO NOTHING',
                                  (playlist['name'],))

            for track in playlist['tracks']:
                track_paths.add(track['path'])

                row = self.db_music.execute('SELECT mtime FROM track WHERE path=?',
                                            (track['path'],)).fetchone()
                if row:
                    mtime, = row
                    if mtime == track['mtime']:
                        # log.info('up to date: %s', track['path'])
                        pass
                    else:
                        log.info('out of date: %s', track['path'])
                        self._update_track(track)
                else:
                    log.info('missing: %s', track['path'])
                    self._insert_track(playlist, track)

                self.db_offline.commit()
                self.db_music.commit()

        self._prune_tracks(track_paths)


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
