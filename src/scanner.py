from pathlib import Path
import logging
from multiprocessing import Pool
from typing import List, Tuple

import db
import metadata
import music
import settings
import logconfig


log = logging.getLogger('app.scanner')


def create_tables():
    """
    Initialise SQLite database with tables
    """
    # TODO enable strict mode after updating to newer sqlite version

    with db.get() as conn:
        conn.execute("""
                    CREATE TABLE IF NOT EXISTS playlist (
                        path TEXT NOT NULL UNIQUE PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        guest INT NOT NULL
                    )
                    """)

        conn.execute("""
                    CREATE TABLE IF NOT EXISTS track (
                        path TEXT NOT NULL UNIQUE PRIMARY KEY,
                        playlist TEXT NOT NULL,
                        duration INT NOT NULL,
                        title TEXT NULL,
                        album TEXT NULL,
                        album_artist TEXT NULL,
                        album_index INT NULL,
                        year INT NULL,
                        last_played INT DEFAULT 0,
                        FOREIGN KEY (playlist) REFERENCES playlist(path) ON DELETE CASCADE
                    )
                    """)

        conn.execute("""
                    CREATE TABLE IF NOT EXISTS track_artist (
                        track TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        FOREIGN KEY (track) REFERENCES track(path) ON DELETE CASCADE,
                        UNIQUE (track, artist)
                    )
                    """)

        conn.execute("""
                    CREATE TABLE IF NOT EXISTS track_tag (
                        track TEXT NOT NULL,
                        tag TEXT NOT NULL,
                        FOREIGN KEY (track) REFERENCES track(path) ON DELETE CASCADE,
                        UNIQUE (track, tag)
                    )
                    """)

def scan_tracks(paths: List[Tuple[Path, Path]]):
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

    with db.get() as conn:
        conn.executemany('INSERT INTO track (path, playlist, duration, title, album, album_artist, album_index, year) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        track_insert)
        conn.executemany('INSERT INTO track_artist VALUES (?, ?)',
                        artist_insert)
        conn.executemany('INSERT INTO track_tag VALUES (?, ?)',
                        tag_insert)

    return len(paths)

def rebuild_music_database():
    """
    Scan disk for playlist and tracks, and create the corresponding rows
    in playlist, track, artist and tag tables. Previous table content is deleted.
    """
    log.info('Scanning tracks...')

    tracks = []

    with db.get() as conn:
        conn.execute('DELETE FROM track_artist')
        conn.execute('DELETE FROM track_tag')
        conn.execute('DELETE FROM track')
        conn.execute('DELETE FROM playlist')

        for playlist_path in Path(settings.music_dir).iterdir():
            if playlist_path.name.startswith('Guest-'):
                playlist_name = playlist_path.name[6:]
                playlist_guest = True
            else:
                playlist_name = playlist_path.name
                playlist_guest = False

            playlist_dir_name = playlist_path.name

            conn.execute('INSERT INTO playlist VALUES (?, ?, ?)',
                    (playlist_dir_name, playlist_name, playlist_guest))

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
        for result in pool.imap_unordered(scan_tracks, chunks):
            processed += result
            log.info('Scanned %s / %s', processed, len(tracks))

    log.info('Done scanning tracks')

if __name__ == '__main__':
    create_tables()
    rebuild_music_database()