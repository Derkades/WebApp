import sqlite3
from pathlib import Path
import logging

import settings


db_path = Path(settings.data_path, 'music.db')
log = logging.getLogger('app.db')

def get():
    """
    Create new SQLite database connection
    """
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def create_tables():
    """
    Initialise SQLite database with tables
    """
    # TODO enable strict mode after updating to newer sqlite version

    log.info('Creating tables')
    with get() as conn:
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


if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    create_tables()