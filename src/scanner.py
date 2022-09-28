from pathlib import Path
import logging
from multiprocessing import Pool
from typing import List, Tuple, Optional

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
        track_insert.append((
            track_relpath,
            playlist_path.name,
            meta.duration,
            meta.title,
            meta.album,
            meta.album_artist,
            meta.album_index,
            meta.year,
        ))
        artists = meta.artists
        if artists is not None:
            for artist in artists:
                artist_insert.append((
                    track_relpath,
                    artist,
                ))
        for tag in meta.tags:
            tag_insert.append((
                track_relpath,
                tag,
            ))

    return track_insert, artist_insert, tag_insert

def rebuild_music_database(only_playlist: Optional[str] = None):
    """
    Scan disk for playlist and tracks, and create the corresponding rows
    in playlist, track, artist and tag tables. Previous table content is deleted.
    """
    tracks = []

    playlist_insert = []
    track_insert = []
    artist_insert = []
    tag_insert = []

    if only_playlist is not None:
        playlist_paths = [Path(settings.music_dir, only_playlist)]
        if not playlist_paths[0].is_dir():
            raise ValueError('Requested playlist directory does not exist (or is not a directory)')
        log.info('Scanning tracks for playlist %s...', only_playlist)
    else:
        playlist_paths = Path(settings.music_dir).iterdir()
        log.info('Scanning tracks for all playlists...')

    for playlist_path in playlist_paths:
        if playlist_path.name.startswith('Guest-'):
            playlist_name = playlist_path.name[6:]
            playlist_guest = True
        else:
            playlist_name = playlist_path.name
            playlist_guest = False

        playlist_dir_name = playlist_path.name

        playlist_insert.append((playlist_dir_name, playlist_name, playlist_guest))

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

        conn.executemany('INSERT INTO playlist VALUES (?, ?, ?)',
                         playlist_insert)
        conn.executemany('INSERT INTO track (path, playlist, duration, title, album, album_artist, album_index, year) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        track_insert)
        conn.executemany('INSERT INTO track_artist VALUES (?, ?)',
                        artist_insert)
        conn.executemany('INSERT INTO track_tag VALUES (?, ?)',
                        tag_insert)

    log.info('Done!')

if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    rebuild_music_database()