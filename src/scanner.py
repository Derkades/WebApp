from pathlib import Path
import logging
from multiprocessing import Pool
from typing import List, Tuple, Optional, Iterable

import db
import metadata
import music
import settings


log = logging.getLogger('app.scanner')


def _scan_tracks(paths: List[Tuple[Path, Path]]):
    """
    Get metadata for provided tracks, and write it to the database.
    """
    track_insert = []
    artist_insert = []
    tag_insert = []

    for playlist_path, track_path in paths:
        track_relpath = music.to_relpath(track_path)
        meta = metadata.probe(track_path)
        track_insert.append({'path': track_relpath,
                             'playlist': playlist_path.name,
                             'duration': meta.duration,
                             'title': meta.title,
                             'album': meta.album,
                             'album_artist': meta.album_artist,
                             'album_index': meta.album_index,
                             'year': meta.year})
        artists = meta.artists
        if artists is not None:
            for artist in artists:
                artist_insert.append({'track': track_relpath,
                                      'artist': artist})
        for tag in meta.tags:
            tag_insert.append({'track': track_relpath,
                               'tag': tag})

    return track_insert, artist_insert, tag_insert

# def upsert(conn, table: str, values: List[Dict[str, Any]]):
#     keys = list(values[0].keys())
#     query = 'INSERT INTO ' + table + ' (' + ', '.join(keys) + ') '
#     query += 'VALUES (' + ', '.join([':' + key for key in keys]) + ') '
#     query += 'ON CONFLICT(' + keys[0] + ') DO UPDATE '
#     query += 'SET ' + ', '.join([f'{key}=:{key}' for key in keys[1:]])
#     conn.executemany(query, values)

def rebuild_music_database(only_playlist: Optional[str] = None) -> None:
    """
    Scan disk for playlist and tracks, and create the corresponding rows
    in playlist, track, artist and tag tables. Previous table content is deleted.
    """
    tracks = []

    playlist_insert = [] # path, name, guest
    track_insert = [] # path, playlist, duration, title, album_artist, album_index, year
    artist_insert = [] # track, artist
    tag_insert = [] # track, tag

    playlist_paths: Iterable[Path]

    if only_playlist is not None:
        playlist_paths = [music.from_relpath(only_playlist)]
        if not playlist_paths[0].is_dir():
            raise ValueError('Requested playlist directory does not exist (or is not a directory)')
        log.info('Scanning tracks for playlist %s...', only_playlist)
    else:
        playlist_paths = [p for p in Path(settings.music_dir).iterdir() if p.is_dir()]
        log.info('Scanning tracks for all playlists...')

    for playlist_path in playlist_paths:
        if playlist_path.name.startswith('Guest-'):
            playlist_name = playlist_path.name[6:]
            playlist_guest = True
        else:
            playlist_name = playlist_path.name
            playlist_guest = False

        playlist_dir_name = playlist_path.name

        playlist_insert.append({'path': playlist_dir_name,
                                'name': playlist_name,
                                'guest': playlist_guest})

        for track_path in music.scan_music(playlist_path):
            tracks.append((playlist_path, track_path))

    chunk_size = 5 if len(tracks) < 50*settings.scanner_processes else 50

    chunks = []
    current_chunk = []
    for track in tracks:
        current_chunk.append(track)
        if len(current_chunk) > chunk_size:
            chunks.append(current_chunk)
            current_chunk = []
    if len(current_chunk) > 0:
        chunks.append(current_chunk)

    with Pool(settings.scanner_processes) as pool:
        processed = 0
        for result_tracks, result_artists, result_tags in pool.imap_unordered(_scan_tracks, chunks):
            track_insert.extend(result_tracks)
            artist_insert.extend(result_artists)
            tag_insert.extend(result_tags)
            processed += len(result_tracks)
            log.info('Scanned %s / %s', processed, len(tracks))

    log.info('Done scanning tracks. Inserting into database...')

    with db.get() as conn:
        if only_playlist:
            conn.execute('DELETE FROM playlist WHERE path=?', (only_playlist,))
        else:
            conn.execute('DELETE FROM playlist')

        conn.executemany('INSERT INTO playlist VALUES (:path, :name, :guest)',
                         playlist_insert)
        conn.executemany('''
                         INSERT INTO track (path, playlist, duration, title, album, album_artist, album_index, year)
                         VALUES (:path, :playlist, :duration, :title, :album, :album_artist, :album_index, :year)
                         ''', track_insert)
        conn.executemany('INSERT INTO track_artist VALUES (:track, :artist)',
                        artist_insert)
        conn.executemany('INSERT INTO track_tag VALUES (:track, :tag)',
                        tag_insert)

        conn.executemany('INSERT OR IGNORE INTO track_persistent (path) VALUES (:path)', track_insert)

        if only_playlist is None:
            count = conn.execute('DELETE FROM track_persistent WHERE path NOT IN (' + (','.join(len(track_insert) * ['?'])) + ')',
                                 [track['path'] for track in track_insert]).rowcount
            log.info('Deleted %s tracks from persistent data', count)

    log.info('Done.')

if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    rebuild_music_database()
