import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection
from typing import Optional

from raphson_mp import db, metadata, music, settings

log = logging.getLogger(__name__)


def scan_playlists(conn: Connection) -> set[str]:
    """
    Scan playlist directories, add or remove playlists from the database
    where necessary.
    """
    paths_db = {row[0] for row in conn.execute('SELECT path FROM playlist').fetchall()}
    paths_disk = {p.name for p in settings.music_dir.iterdir() if p.is_dir() and not music.is_trashed(p)}

    add_to_db = []

    for path in paths_db:
        if path not in paths_disk:
            log.info('Removing playlist: %s', path)
            conn.execute('DELETE FROM playlist WHERE path=?', (path,))

    for path in paths_disk:
        if path not in paths_db:
            log.info('Adding playlist: %s', path)
            add_to_db.append((path,))

    conn.executemany('INSERT INTO playlist (path) VALUES (?)', add_to_db)

    return paths_disk


@dataclass
class QueryParams:
    main_data: dict[str, str|int|None]
    artist_data: list[dict[str, str]]
    tag_data: list[dict[str, str]]


def query_params(relpath: str, path: Path) -> QueryParams | None:
    """
    Create dictionary of track metadata, to be used as SQL query parameters
    """
    meta = metadata.probe(path)

    if not meta:
        return None

    main_data: dict[str, str|int|None] = {'path': relpath,
                                          'duration': meta.duration,
                                          'title': meta.title,
                                          'album': meta.album,
                                          'album_artist': meta.album_artist,
                                          'track_number': meta.track_number,
                                          'year': meta.year,
                                          'lyrics': meta.lyrics}
    if meta.artists is None:
        artist_data = []
    else:
        artist_data = [{'track': relpath,
                        'artist': artist} for artist in meta.artists]
    tag_data = [{'track': relpath,
                 'tag': tag} for tag in meta.tags]

    return QueryParams(main_data, artist_data, tag_data)


def scan_track(conn: Connection, playlist_name: str, track_path: Path, track_relpath: str) -> bool:
    """
    Scan single track.
    Returns: Whether track exists (False if deleted)
    """
    if not track_path.exists():
        log.info('Deleted: %s', track_relpath)
        conn.execute('DELETE FROM track WHERE path=?', (track_relpath,))
        conn.execute('''
                        INSERT INTO scanner_log (timestamp, action, playlist, track)
                        VALUES (?, 'delete', ?, ?)
                        ''', (int(time.time()), playlist_name, track_relpath))
        return False

    row = conn.execute('SELECT mtime FROM track WHERE path=?', (track_relpath,)).fetchone()
    db_mtime = row[0] if row else None
    file_mtime = int(track_path.stat().st_mtime)

    # Track does not yet exist in database
    if db_mtime is None:
        log.info('New track, insert: %s', track_relpath)
        params = query_params(track_relpath, track_path)
        if not params:
            log.warning('Skipping due to metadata error')
            return False
        conn.execute('''
                     INSERT INTO track (path, playlist, duration, title, album, album_artist, track_number, year, lyrics, mtime)
                     VALUES (:path, :playlist, :duration, :title, :album, :album_artist, :track_number, :year, :lyrics, :mtime)
                     ''',
                     {**params.main_data,
                      'playlist': playlist_name,
                      'mtime': file_mtime})
        conn.executemany('INSERT INTO track_artist (track, artist) VALUES (:track, :artist)', params.artist_data)
        conn.executemany('INSERT INTO track_tag (track, tag) VALUES (:track, :tag)', params.tag_data)

        conn.execute('''
                     INSERT INTO scanner_log (timestamp, action, playlist, track)
                     VALUES (?, 'insert', ?, ?)
                     ''', (int(time.time()), playlist_name, track_relpath))
        return True

    if file_mtime != db_mtime:
        log.info('Changed, update: %s (%s to %s)', track_relpath, datetime.fromtimestamp(db_mtime, tz=timezone.utc), datetime.fromtimestamp(file_mtime, tz=timezone.utc))
        params = query_params(track_relpath, track_path)
        if not params:
            log.warning('Metadata error, delete track from database')
            conn.execute('DELETE FROM track WHERE path=?', (track_relpath,))
            return False
        conn.execute('''
                        UPDATE track
                        SET duration=:duration,
                            title=:title,
                            album=:album,
                            album_artist=:album_artist,
                            track_number=:track_number,
                            year=:year,
                            lyrics=:lyrics,
                            mtime=:mtime
                        WHERE path=:path
                    ''',
                    {**params.main_data,
                     'mtime': file_mtime})
        conn.execute('DELETE FROM track_artist WHERE track=?', (track_relpath,))
        conn.executemany('INSERT INTO track_artist (track, artist) VALUES (:track, :artist)', params.artist_data)
        conn.execute('DELETE FROM track_tag WHERE track=?', (track_relpath,))
        conn.executemany('INSERT INTO track_tag (track, tag) VALUES (:track, :tag)', params.tag_data)

        conn.execute('''
                     INSERT INTO scanner_log (timestamp, action, playlist, track)
                     VALUES (?, 'update', ?, ?)
                     ''', (int(time.time()), playlist_name, track_relpath))
        return True

    # Track exists in filesystem and is unchanged
    return True


def scan_tracks(conn: Connection, playlist_name: str) -> None:
    """
    Scan for added, removed or changed tracks in a playlist.
    """
    log.info('Scanning playlist: %s', playlist_name)
    paths_db: set[str] = set()

    for track_relpath, in conn.execute('SELECT path FROM track WHERE playlist=?',
                                        (playlist_name,)).fetchall():
        if scan_track(conn, playlist_name, music.from_relpath(track_relpath), track_relpath):
            paths_db.add(track_relpath)

    for track_path in music.list_tracks_recursively(music.from_relpath(playlist_name)):
        track_relpath = music.to_relpath(track_path)
        if track_relpath not in paths_db:
            scan_track(conn, playlist_name, track_path, track_relpath)


def last_change(conn: Connection, playlist: Optional[str] = None):
    if playlist:
        query = 'SELECT timestamp FROM scanner_log WHERE playlist = ? ORDER BY id DESC LIMIT 1'
        params = (playlist,)
    else:
        query = 'SELECT timestamp FROM scanner_log ORDER BY id DESC LIMIT 1'
        params = ()
    timestamp_row = conn.execute(query, params).fetchone()
    if timestamp_row:
        return datetime.fromtimestamp(timestamp_row[0], timezone.utc)

    return datetime.fromtimestamp(0, timezone.utc)


def scan() -> None:
    """
    Main function for scanning music directory structure
    """
    if settings.offline_mode:
        log.info('Skip scanner in offline mode')
        return

    with db.connect() as conn:
        start_time_ns = time.time_ns()
        playlists = scan_playlists(conn)
        for playlist in playlists:
            scan_tracks(conn, playlist)
        duration_ms = (time.time_ns() - start_time_ns) // 1000000
        log.info('Took %sms', duration_ms)
