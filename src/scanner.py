from pathlib import Path
import logging

import db
import metadata
import music
import settings
import logconfig

log = logging.getLogger('app.scanner')

def create_tables(conn):
    # TODO enable strict mode after updating to newer sqlite version
    conn.execute('PRAGMA foreign_keys = ON;')

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

def rebuild_music_database(conn):
    conn.execute('DELETE FROM track_artist')
    conn.execute('DELETE FROM track')
    conn.execute('DELETE FROM playlist')

    playlist_insert = []
    track_insert = []
    artist_insert = []
    tag_insert = []

    for playlist_path in Path(settings.music_dir).iterdir():
        if playlist_path.name.startswith('Guest-'):
            playlist_name = playlist_path.name[6:]
            playlist_guest = True
        else:
            playlist_name = playlist_path.name
            playlist_guest = False

        playlist_dir_name = playlist_path.name
        playlist_insert.append((playlist_dir_name, playlist_name, playlist_guest))

        log.info('Scanning playlist %s', playlist_dir_name)

        # TODO recursive
        for track_path in playlist_path.iterdir():
            track_relpath = music.to_relpath(track_path)
            meta = metadata.probe(track_path)
            track_insert.append((
                track_relpath,
                playlist_dir_name,
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

    conn.executemany('INSERT INTO playlist VALUES (?, ?, ?)',
                     playlist_insert)
    conn.executemany('INSERT INTO track VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     track_insert)
    conn.executemany('INSERT INTO track_artist VALUES (?, ?)',
                     artist_insert)
    conn.executemany('INSERT INTO track_tag VALUES (?, ?)',
                     tag_insert)


if __name__ == '__main__':
    with db.get() as conn:
        create_tables(conn)
        rebuild_music_database(conn)