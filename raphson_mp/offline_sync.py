import logging
import random
import sys
import traceback
from multiprocessing.pool import ThreadPool
from sqlite3 import Connection
from urllib.parse import quote as urlencode

import requests
from requests import Response
from requests.exceptions import RequestException

from raphson_mp import db, settings

log = logging.getLogger(__name__)


class OfflineSync:
    db_offline: Connection
    db_music: Connection
    base_url: str
    token: str | None = None

    def __init__(self, db_offline: Connection, db_music: Connection):
        self.db_offline = db_offline
        self.db_music = db_music
        self.base_url = self.get_base_url()
        self.set_token()

    def get_headers(self) -> dict[str, str]:
        """
        Returns header dictionary for use by requests library
        """
        headers = {'User-Agent': settings.user_agent_offline_sync}
        if self.token is not None:
            headers['Cookie'] = 'token=' + self.token
        return headers

    def request_get(self, route: str, raise_for_status: bool = True) -> Response:
        response = requests.get(self.base_url + route,
                                headers=self.get_headers(),
                                timeout=60)
        if raise_for_status:
            response.raise_for_status()
        return response

    def request_post(self, route: str, data, raise_for_status: bool = True) -> Response:
        response = requests.post(self.base_url + route,
                                 json=data,
                                 headers=self.get_headers(),
                                 timeout=30)
        if raise_for_status:
            response.raise_for_status()
        return response

    def get_base_url(self):
        """
        Get base URL variable from database. If not stored in the database, the user is asked to enter one.
        """
        row = self.db_offline.execute("SELECT value FROM settings WHERE key='sync_url'").fetchone()
        if row:
            base_url, = row
        else:
            log.info('No sync server is configured')
            base_url = input('Enter server URL (https://example.com): ')
            self.db_offline.execute("INSERT INTO settings (key, value) VALUES ('sync_url', ?)",
                                    (base_url,))
            self.db_offline.commit()
        return base_url

    def set_token(self):
        """
        Set local token variable from database. If no token is stored, the user is asked to log in.
        """
        row = self.db_offline.execute("SELECT value FROM settings WHERE key='sync_token'").fetchone()
        if row:
            self.token, = row
            try:
                response = self.request_get('/auth/get_csrf', raise_for_status=False)
                if response.status_code == 403:
                    log.info('Got 403 response, authentication token is invalid, please log in again.')
                    self.login_prompt()
                    self.set_token()
                else:
                    response.raise_for_status()
                    log.info('Authentication token is valid')
            except RequestException:
                traceback.print_exc()
                log.info('Error testing authentication token. Do you have a working internet connection?')
                sys.exit(1)
        else:
            log.info('No authentication token stored, please log in')
            self.login_prompt()
            self.set_token()

    def login_prompt(self):
        """
        Ask user to log in, and store resulting token in database.
        """
        username = input('Enter username: ')
        password = input('Enter password: ')

        try:
            response = self.request_post('/auth/login',
                                         {'username': username,
                                          'password': password})
        except RequestException:
            traceback.print_exc()
            log.info('Error during log in, please try again.')
            self.login_prompt()
            return

        token = response.json()['token']
        self.db_offline.execute('''
                                INSERT INTO settings (key, value)
                                VALUES ('sync_token', ?)
                                ON CONFLICT (key)
                                    DO UPDATE SET value=?
                                ''',
                                (token, token))
        self.db_offline.commit()
        log.info('Logged in successfully')

    def _download_track_content(self, path: str) -> None:
        """
        Download audio, album cover and lyrics for a track and store in the 'content' database table.
        """
        def download_audio() -> bytes:
            return self.request_get(f'/track/{urlencode(path)}/audio?type=webm_opus_high').content

        def download_cover() -> bytes:
            return self.request_get(f'/track/{urlencode(path)}/cover?quality=high').content

        def download_lyrics() -> str:
            return self.request_get(f'/track/{urlencode(path)}/lyrics2').text

        with ThreadPool(3) as pool:
            result_audio = pool.apply_async(download_audio)
            result_cover = pool.apply_async(download_cover)
            result_lyrics = pool.apply_async(download_lyrics)
            audio = result_audio.get()
            cover = result_cover.get()
            lyrics = result_lyrics.get()

        self.db_offline.execute(
            """
            INSERT INTO content (path, music_data, cover_data, lyrics_json)
            VALUES(:path, :music_data, :cover_data, :lyrics_json)
            ON CONFLICT (path) DO UPDATE SET
                music_data = :music_data, cover_data = :cover_data, lyrics_json = :lyrics_json
            """,
            {'path': path,
             'music_data': audio,
             'cover_data': cover,
             'lyrics_json': lyrics})

    def _update_track(self, track) -> None:
        self._download_track_content(track['path'])

        self.db_music.execute('UPDATE track SET duration=?, title=?, album=?, album_artist=?, year=?, mtime=? WHERE path=?',
                              (track['duration'], track['title'], track['album'], track['album_artist'], track['year'],
                               track['mtime'], track['path']))

        self.db_music.execute('DELETE FROM track_artist WHERE track=?', (track['path'],))

        if track['artists']:
            insert = [(track['path'], artist) for artist in track['artists']]
            self.db_music.executemany('INSERT INTO track_artist (track, artist) VALUES (?, ?)', insert)

    def _insert_track(self, playlist: str, track) -> None:
        self._download_track_content(track['path'])

        self.db_music.execute(
            """
            INSERT INTO track (path, playlist, duration, title, album,
                               album_artist, year, mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (track['path'], playlist, track['duration'], track['title'],
             track['album'], track['album_artist'], track['year'], track['mtime'])
        )

        if track['artists']:
            insert = [(track['path'], artist) for artist in track['artists']]
            self.db_music.executemany('INSERT INTO track_artist (track, artist) VALUES (?, ?)', insert)

    def _prune_tracks(self, track_paths: set[str]):
        rows = self.db_music.execute('SELECT path FROM track').fetchall()
        for path, in rows:
            if path not in track_paths:
                log.info('Delete: %s', path)
                self.db_offline.execute('DELETE FROM content WHERE path=?',
                                        (path,))
                self.db_music.execute('DELETE FROM track WHERE path=?',
                                      (path,))

    def _prune_playlists(self):
        # Remove empty playlists
        rows = self.db_music.execute(
            '''
            SELECT path
            FROM playlist
            WHERE (SELECT COUNT(*) FROM track WHERE track.playlist=playlist.path) = 0
            ''').fetchall()

        for name, in rows:
            log.info('Delete empty playlist: %s', name)
            self.db_music.execute('DELETE FROM playlist WHERE path=?',
                                  (name,))

    def _sync_tracks_for_playlist(self,
                                  playlist: str,
                                  dislikes: set[str],
                                  all_track_paths: set[str],
                                  force_resync: float):
        log.info('Syncing playlist: %s', playlist)

        self.db_music.execute('INSERT INTO playlist VALUES (?) ON CONFLICT (path) DO NOTHING',
                                  (playlist,))

        r = self.request_get('/tracks/filter?playlist=' + urlencode(playlist))
        tracks = r.json()['tracks']

        for track in tracks:
            if track['path'] in dislikes:
                continue

            all_track_paths.add(track['path'])

            row = self.db_music.execute('SELECT mtime FROM track WHERE path=?',
                                        (track['path'],)).fetchone()
            if row:
                mtime, = row
                if mtime != track['mtime']:
                    log.info('Out of date: %s', track['path'])
                    self._update_track(track)
                elif force_resync > 0 and random.random() < force_resync:
                    log.info('Force resync: %s', track['path'])
                    self._update_track(track)
            else:
                log.info('Missing: %s', track['path'])
                self._insert_track(playlist, track)

            self.db_offline.commit()
            self.db_music.commit()

    def sync_tracks(self, force_resync: float) -> None:
        """
        Download added or modified tracks from the server, and delete local tracks that were deleted on the server
        """
        result = self.db_offline.execute('SELECT name FROM playlists')
        enabled_playlists = [row[0] for row in result]

        if len(enabled_playlists) == 0:
            log.info('No playlists selected. Fetching favorite playlists...')
            playlists = self.request_get('/playlist/list').json()
            enabled_playlists = [playlist['name'] for playlist in playlists if playlist['favorite']]

        log.info('Syncing playlists: %s', ','.join(enabled_playlists))

        log.info('Fetching disliked tracks')
        dislikes = set(self.request_get('/dislikes/json').json()['tracks'])

        all_track_paths: set[str] = set()

        for playlist in enabled_playlists:
            self._sync_tracks_for_playlist(playlist, dislikes, all_track_paths, force_resync)

        self._prune_tracks(all_track_paths)
        self._prune_playlists()

    def sync_history(self):
        """
        Send local playback history to server
        """
        csrf_token = self.request_get('/auth/get_csrf').json()['token']

        rows = self.db_offline.execute('SELECT rowid, timestamp, track FROM history ORDER BY timestamp ASC')
        for rowid, timestamp, track in rows:
            log.info('Played: %s', track)
            response = self.request_post('/activity/played',
                              {'csrf': csrf_token,
                               'track': track,
                               'timestamp': timestamp})
            assert response.status_code == 200
            self.db_offline.execute('DELETE FROM history WHERE rowid=?', (rowid,))
            self.db_offline.commit()


def do_sync(force_resync: float) -> None:
    if not settings.offline_mode:
        log.warning('Refusing to sync, music player is not in offline mode')
        return

    with db.connect() as db_music, db.offline() as db_offline:
        sync = OfflineSync(db_offline, db_music)
        log.info('Sync history')
        sync.sync_history()
        log.info('Sync tracks')
        sync.sync_tracks(force_resync)
        log.info('Cleaning up')
        db_offline.execute('PRAGMA incremental_vacuum')


def change_playlists(playlists: list[str]) -> None:
    if len(playlists) == 0:
        log.info('Resetting enabled playlists')
    else:
        log.info('Changing playlists: %s', ','.join(playlists))

    with db.offline() as conn:
        conn.execute('BEGIN')
        conn.execute('DELETE FROM playlists')
        conn.executemany('INSERT INTO playlists VALUES (?)',
                         [(playlist,) for playlist in playlists])
        conn.execute('COMMIT')
