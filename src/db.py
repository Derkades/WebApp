import sqlite3
from sqlite3 import Connection
from pathlib import Path
import logging

import settings


db_path = Path(settings.data_path, 'music.db')
log = logging.getLogger('app.db')


def _connect(db_name: str, read_only: bool) -> Connection:
    db_uri = 'file:' + \
          Path(settings.data_path, db_name + '.db').absolute().as_posix() + \
          ('?mode=ro' if read_only else '')
    conn = sqlite3.connect(db_uri, uri=True, timeout=10.0)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    return conn


def connect(read_only: bool = False) -> Connection:
    """
    Create new SQLite database connection
    """
    return _connect('music', read_only)


def cache(read_only: bool = False) -> Connection:
    """
    Create new SQLite database connection to cache database
    """
    return _connect('cache', read_only)


def create_tables():
    """
    Initialize SQLite databases using SQL scripts
    """
    with open('sql/music.sql', 'r', encoding='utf-8') as music_sql_f:
        connect().executescript(music_sql_f.read())

    with open('sql/cache.sql', 'r', encoding='utf-8') as cache_sql_f:
        cache().executescript(cache_sql_f.read())


if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    create_tables()
