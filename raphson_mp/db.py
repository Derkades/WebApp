import logging
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection

from raphson_mp import settings

log = logging.getLogger(__name__)


DATABASE_NAMES = ['cache', 'music', 'offline', 'meta']


def db_path(db_name: str) -> Path:
    return settings.data_dir / (db_name + '.db')


def _connect(db_name: str, read_only: bool) -> Connection:
    db_uri = f'file:{db_path(db_name)}'
    if read_only:
        db_uri += '?mode=ro'
    conn = sqlite3.connect(db_uri, uri=True, timeout=30.0)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA temp_store = MEMORY')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA synchronous = NORMAL')
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
    return _connect('offline', read_only)


def create_databases() -> None:
    """
    Initialize SQLite databases using SQL scripts
    """
    if (settings.data_dir / 'meta.db').exists():
        return

    for db_name in DATABASE_NAMES:
        log.info('Creating database: %s', db_name)
        with _connect(db_name, False) as conn:
            conn.execute('PRAGMA auto_vacuum = INCREMENTAL') # must be set before any tables are created
            conn.executescript((settings.init_sql_dir / f'{db_name}.sql').read_text(encoding='utf-8'))

    with _connect('meta', False) as conn:
        migrations = get_migrations()
        if len(migrations) > 0:
            version = migrations[-1].to_version
        else:
            version = 0

        log.info('Setting initial database version to %s', version)

        conn.execute('INSERT INTO db_version VALUES (?)', (version,))


@dataclass
class Migration:
    file_name: str
    to_version: int
    db_name: str

    def run(self) -> None:
        """Execute migration file"""
        with _connect(self.db_name, False) as conn:
            conn.executescript((settings.migration_sql_dir / self.file_name).read_text(encoding='utf-8'))


def get_migrations() -> list[Migration]:
    migration_file_names = [path.name for path in settings.migration_sql_dir.iterdir()
                            if path.name.endswith('.sql')]

    migrations: list[Migration] = []

    for i, file_name in enumerate(sorted(migration_file_names)):
        name_split = file_name.split('-')
        assert len(name_split) == 2, name_split
        to_version = int(name_split[0])
        db_name = name_split[1][:-4]
        assert i + 1 == int(name_split[0]), f'{i} | {int(name_split[0])}'
        assert db_name in DATABASE_NAMES, db_name
        migrations.append(Migration(file_name, to_version, db_name))

    return migrations


def get_version():
    with sqlite3.connect(':memory:') as conn:
        return conn.execute('SELECT sqlite_version()').fetchone()[0]


def migrate() -> None:
    log.info('Using SQLite version: %s', get_version())

    log.info('Migrating databases...')
    create_databases()

    with _connect('meta', True) as conn:
        version_row = conn.execute('SELECT version FROM db_version').fetchone()
        if version_row:
            version = version_row[0]
        else:
            log.error('Version missing from database. Cannot continue.')
            sys.exit(1)

    migrations = get_migrations()

    if len(migrations) < version:
        log.error('Database version is greater than number of migration files')
        sys.exit(1)

    pending_migrations = migrations[version:]
    if len(pending_migrations) == 0:
        log.info('Nothing to do')

    for migration in pending_migrations:
        log.info('Running migration to version %s', migration.to_version)
        migration.run()
        with _connect('meta', False) as conn:
            conn.execute('UPDATE db_version SET version=?', (migration.to_version,))
