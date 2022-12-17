import sqlite3
from sqlite3 import Connection
from pathlib import Path
import logging

import settings


db_path = Path(settings.data_path, 'music.db')
log = logging.getLogger('app.db')


def _connect(dbname: str) -> Connection:
    conn = sqlite3.connect(Path(settings.data_path, dbname + '.db'))
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def get() -> Connection:
    """
    Create new SQLite database connection
    Deprecated: use music() instead
    """
    return _connect('music')


def music() -> Connection:
    """
    Open music database
    """
    return _connect('music')


def users() -> Connection:
    """
    Open users database
    """
    return _connect('users')


def create_tables() -> None:
    """
    Initialise SQLite database with tables
    """
    # TODO enable strict mode after updating to newer sqlite version

    log.info('Creating tables')
    with music() as conn:
        conn.execute("""
                    CREATE TABLE IF NOT EXISTS playlist (
                        path TEXT NOT NULL UNIQUE PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        guest INTEGER NOT NULL
                    )
                    """)

        conn.execute("""
                    CREATE TABLE IF NOT EXISTS track (
                        path TEXT NOT NULL UNIQUE PRIMARY KEY,
                        playlist TEXT NOT NULL,
                        duration INTEGER NOT NULL,
                        title TEXT NULL,
                        album TEXT NULL,
                        album_artist TEXT NULL,
                        album_index INTEGER NULL,
                        year INTEGER NULL,
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

        # Like the track table but for persistent data. Unlike the regular track table, this table is not emptied at every startup.
        conn.execute("""
                    CREATE TABLE IF NOT EXISTS track_persistent (
                        path TEXT NOT NULL UNIQUE PRIMARY KEY,
                        last_played INTEGER NOT NULL DEFAULT 0
                    )
                    """)

        conn.execute("""
                     CREATE TABLE IF NOT EXISTS radio_track (
                         track TEXT NOT NULL,
                         start_time INTEGER NOT NULL,
                         FOREIGN KEY (track) REFERENCES track(path) ON DELETE CASCADE
                     )
                     """)

    with users() as conn:
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS user (
                         id INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
                         username TEXT NOT NULL UNIQUE,
                         password TEXT NOT NULL,
                         admin INT NOT NULL DEFAULT 0
                     )
                     """)

        conn.execute("""
                     CREATE TABLE IF NOT EXISTS user_lastfm (
                         user INTEGER NOT NULL UNIQUE PRIMARY KEY,
                         name TEXT NOT NULL,
                         key TEXT NOT NULL,
                         FOREIGN KEY (user) REFERENCES user(id) ON DELETE CASCADE
                     )
                     """)

        conn.execute("""
                     CREATE TABLE IF NOT EXISTS session (
                         user INTEGER NOT NULL,
                         token TEXT NOT NULL UNIQUE,
                         creation_date INTEGER NOT NULL,
                         last_user_agent TEXT NULL,
                         last_address TEXT NULL,
                         FOREIGN KEY (user) REFERENCES user(id) ON DELETE CASCADE
                     )
                     """)

        conn.execute("""
                     CREATE TABLE IF NOT EXISTS csrf (
                         user INTEGER NOT NULL,
                         token TEXT NOT NULL UNIQUE,
                         creation_date INTEGER NOT NULL,
                         UNIQUE(user, token),
                         FOREIGN KEY (user) REFERENCES user(id) ON DELETE CASCADE
                     )
                     """)


if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    create_tables()
