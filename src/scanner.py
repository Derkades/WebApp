from pathlib import Path
import logging
from sqlite3 import Connection

import db
import metadata
import music
from music import Playlist
import settings


log = logging.getLogger('app.scanner')


def scan_playlists(conn: Connection) -> set[str]:
    """
    Scan playlist directories, add or remove playlists from the database
    where necessary.
    """
    paths_db = {row[0] for row in conn.execute('SELECT path FROM playlist').fetchall()}
    paths_disk = {p.name for p in Path(settings.music_dir).iterdir() if p.is_dir() and not p.name.startswith('.trash.')}

    add_to_db = []

    for path in paths_db:
        if path not in paths_disk:
            log.info('Removing playlist: %s', path)
            conn.execute('DELETE FROM playlist WHERE path=?', (path,))

    for path in paths_disk:
        if path not in paths_db:
            log.info('Adding playlist: %s', path)
            add_to_db.append({'path': path})

    conn.executemany('INSERT INTO playlist (path, name) VALUES (:path, :path)', add_to_db)

    return paths_disk


def query_params(relpath: str, path: Path) -> tuple[dict[str, object], list[dict[str, str]], list[dict[str, str]]]:
    """
    Create dictionary of track metadata, to be used as SQL query parameters
    """
    meta = metadata.probe(path)

    main_data = {'path': relpath,
                 'duration': meta.duration,
                 'title': meta.title,
                 'album': meta.album,
                 'album_artist': meta.album_artist,
                 'album_index': meta.album_index,
                 'year': meta.year}
    if meta.artists is None:
        artist_data = []
    else:
        artist_data = [{'track': relpath,
                        'artist': artist} for artist in meta.artists]
    tag_data = [{'track': relpath,
                 'tag': tag} for tag in meta.tags]

    return main_data, artist_data, tag_data


def scan_tracks(conn: Connection, playlist: Playlist | str) -> None:
    """
    Scan for added, removed or changed tracks in a playlist.
    """
    if isinstance(playlist, Playlist):
        playlist_path = playlist.relpath
    else:
        playlist_path = playlist

    log.info('Scanning playlist: %s', playlist_path)

    paths_db: set[str] = set()

    for relpath, db_mtime in conn.execute('SELECT path, mtime FROM track WHERE playlist=?',
                                          (playlist_path,)).fetchall():
        path = music.from_relpath(relpath)
        if not path.exists():
            log.info('deleting: %s', relpath)
            conn.execute('DELETE FROM track WHERE path=?', (relpath,))
            continue

        paths_db.add(relpath)

        file_mtime = int(path.stat().st_mtime)
        if file_mtime != db_mtime:
            log.info('changed, update: %s (%s, %s)', relpath, file_mtime, db_mtime)
            main_data, artist_data, tag_data = query_params(relpath, path)
            conn.execute('''
                         UPDATE track
                         SET duration=:duration,
                             title=:title,
                             album=:album,
                             album_artist=:album_artist,
                             album_index=:album_index,
                             year=:year,
                             mtime=:mtime
                         WHERE path=:path
                        ''',
                        {**main_data,
                         'mtime': file_mtime})
            conn.execute('DELETE FROM track_artist WHERE track=?', (relpath,))
            conn.executemany('INSERT INTO track_artist (track, artist) VALUES (:track, :artist)', artist_data)
            conn.execute('DELETE FROM track_tag WHERE track=?', (relpath,))
            conn.executemany('INSERT INTO track_tag (track, tag) VALUES (:track, :tag)', tag_data)

    for path in music.scan_playlist(playlist_path):
        relpath = music.to_relpath(path)
        if relpath not in paths_db:
            mtime = int(path.stat().st_mtime)
            log.info('new track, insert: %s', relpath)
            main_data, artist_data, tag_data = query_params(relpath, path)
            conn.execute('''
                         INSERT INTO track (path, playlist, duration, title, album, album_artist, album_index, year, mtime)
                         VALUES (:path, :playlist, :duration, :title, :album, :album_artist, :album_index, :year, :mtime)
                         ''',
                         {**main_data,
                          'playlist': playlist_path,
                          'mtime': mtime})
            conn.executemany('INSERT INTO track_artist (track, artist) VALUES (:track, :artist)', artist_data)
            conn.executemany('INSERT INTO track_tag (track, tag) VALUES (:track, :tag)', tag_data)


def scan(conn: Connection) -> None:
    """
    Main function for scanning music directory structure
    """
    playlists = scan_playlists(conn)
    for playlist in playlists:
        scan_tracks(conn, playlist)


if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    with db.connect() as conn:
        scan(conn)
