import logging
import random
from sqlite3 import Connection

from raphson_mp import db, settings
from raphson_music_client import RaphsonMusicClient, Track, asyncio

log = logging.getLogger(__name__)


class OfflineSync:
    db_offline: Connection
    db_music: Connection
    client: RaphsonMusicClient

    def __init__(self, db_offline: Connection, db_music: Connection):
        self.db_offline = db_offline
        self.db_music = db_music

        row = self.db_offline.execute("SELECT base_url, token FROM settings").fetchone()
        if row:
            base_url, token = row
        else:
            log.info('Server is not configured')
            base_url = input('Enter server URL (https://example.com): ')
            token = input('Enter token (visit /token page to get a token): ')
            self.db_offline.execute('INSERT INTO settings (base_url, token) VALUES (?, ?)', (base_url, token))

        self.client = RaphsonMusicClient(base_url=base_url, user_agent=settings.user_agent, token=token)

    async def _download_track_content(self, track: Track) -> None:
        """
        Download audio, album cover and lyrics for a track and store in the 'content' database table.
        """
        download = await self.client.download_track(track)

        self.db_offline.execute(
            """
            INSERT INTO content (path, music_data, cover_data, lyrics_json)
            VALUES(:path, :music_data, :cover_data, :lyrics_json)
            ON CONFLICT (path) DO UPDATE SET
                music_data = :music_data, cover_data = :cover_data, lyrics_json = :lyrics_json
            """,
            {'path': track.path,
             'music_data': download.audio,
             'cover_data': download.image,
             'lyrics_json': download.lyrics_json})

    async def _update_track(self, track: Track) -> None:
        await self._download_track_content(track)

        self.db_music.execute('UPDATE track SET duration=?, title=?, album=?, album_artist=?, year=?, mtime=? WHERE path=?',
                              (track.duration, track.title, track.album, track.album_artist, track.year,
                               track.mtime, track.path))
        self.db_music.execute('DELETE FROM track_artist WHERE track=?', (track.path,))
        self.db_music.executemany('INSERT INTO track_artist (track, artist) VALUES (?, ?)',
                                  [(track.path, artist) for artist in track.artists])

    async def _insert_track(self, playlist: str, track: Track) -> None:
        await self._download_track_content(track)

        self.db_music.execute(
            """
            INSERT INTO track (path, playlist, duration, title, album,
                               album_artist, year, mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (track.path, playlist, track.duration, track.title, track.album, track.album_artist, track.year, track.mtime)
        )
        self.db_music.executemany('INSERT INTO track_artist (track, artist) VALUES (?, ?)',
                                  [(track.path, artist) for artist in track.artists])

    def _prune_tracks(self, track_paths: set[str]):
        rows = self.db_music.execute('SELECT path FROM track').fetchall()
        for path, in rows:
            if path not in track_paths:
                log.info('Delete: %s', path)
                self.db_offline.execute('DELETE FROM content WHERE path=?', (path,))
                self.db_music.execute('DELETE FROM track WHERE path=?', (path,))

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

    async def _sync_tracks_for_playlist(self,
                                  playlist: str,
                                  dislikes: set[str],
                                  all_track_paths: set[str],
                                  force_resync: float):
        log.info('Syncing playlist: %s', playlist)

        self.db_music.execute('INSERT INTO playlist VALUES (?) ON CONFLICT (path) DO NOTHING',
                                  (playlist,))

        tracks = await self.client.list_tracks(playlist)

        for track in tracks:
            if track.path in dislikes:
                continue

            all_track_paths.add(track.path)

            row = self.db_music.execute('SELECT mtime FROM track WHERE path=?',
                                        (track.path,)).fetchone()
            if row:
                mtime, = row
                if mtime != track.mtime:
                    log.info('Out of date: %s', track.path)
                    await self._update_track(track)
                elif force_resync > 0 and random.random() < force_resync:
                    log.info('Force resync: %s', track.path)
                    await self._update_track(track)
            else:
                log.info('Missing: %s', track.path)
                await self._insert_track(playlist, track)

            self.db_offline.commit()
            self.db_music.commit()

    async def sync_tracks(self, force_resync: float) -> None:
        """
        Download added or modified tracks from the server, and delete local tracks that were deleted on the server
        """
        result = self.db_offline.execute('SELECT name FROM playlists')
        enabled_playlists: list[str] = [row[0] for row in result]

        if len(enabled_playlists) == 0:
            log.info('No playlists selected. Fetching favorite playlists...')
            playlists = await self.client.playlists()
            enabled_playlists = [playlist.name for playlist in playlists if playlist.favorite]

        log.info('Syncing playlists: %s', ','.join(enabled_playlists))

        log.info('Fetching disliked tracks')
        dislikes: set[str] = set()  # TODO implement retrieving dislikes
        # dislikes = set(self.request_get('/dislikes/json').json()['tracks'])

        all_track_paths: set[str] = set()

        for playlist in enabled_playlists:
            await self._sync_tracks_for_playlist(playlist, dislikes, all_track_paths, force_resync)

        self._prune_tracks(all_track_paths)
        self._prune_playlists()

    async def sync_history(self):
        """
        Send local playback history to server
        """
        rows = self.db_offline.execute('SELECT rowid, timestamp, track FROM history ORDER BY timestamp ASC')
        for rowid, timestamp, track in rows:
            log.info('Played: %s', track)
            await self.client.submit_played(track, timestamp)
            self.db_offline.execute('DELETE FROM history WHERE rowid=?', (rowid,))
            self.db_offline.commit()


async def do_sync_async(force_resync: float) -> None:
    if not settings.offline_mode:
        log.warning('Refusing to sync, music player is not in offline mode')
        return

    with db.connect() as db_music, db.offline() as db_offline:
        sync = OfflineSync(db_offline, db_music)
        try:
            log.info('Sync history')
            await sync.sync_history()
            log.info('Sync tracks')
            await sync.sync_tracks(force_resync)
            log.info('Cleaning up')
            db_offline.execute('PRAGMA incremental_vacuum')
        finally:
            if sync.client:
                await sync.client.close()


def do_sync(force_resync: float):
    asyncio.run(do_sync_async(force_resync=force_resync))


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
