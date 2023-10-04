import sqlite3
from sqlite3 import Connection
from pathlib import Path
import logging

import settings


log = logging.getLogger('app.db')


def _open_sql(db_name: str):
    return open(f'sql/{db_name}.sql', 'r', encoding='utf-8')


def _connect(db_name: str, read_only: bool) -> Connection:
    db_path = Path(settings.data_path, db_name + '.db').absolute().as_posix()
    db_uri = f'file:{db_path}' + ('?mode=ro' if read_only else '')
    conn = sqlite3.connect(db_uri, uri=True, timeout=10.0)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    return conn


def connect(read_only: bool = False) -> Connection:
    """
    Create new SQLite database connection to main music database
    """
    return _connect('music', read_only)


def cache(read_only: bool = False) -> Connection:
    """
    Create new SQLite database connection to cache database
    """
    return _connect('cache', read_only)


def offline(read_only: bool = False) -> Connection:
    """
    Create new SQLite database connection to offline database
    """
    conn = _connect('offline', read_only)
    # Slow writes don't matter for the offline database, as writing only happens when syncing
    # which is slow anyway.
    conn.execute('PRAGMA auto_vacuum = FULL')
    return conn


def create_tables():
    """
    Initialize SQLite databases using SQL scripts
    """
    log.info('Initializing databases')

    for db_name in ['music', 'cache', 'offline']:
        with _open_sql(db_name) as sql_file:
            _connect(db_name, False).executescript(sql_file.read())


if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    create_tables()
