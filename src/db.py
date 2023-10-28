import sqlite3
from sqlite3 import Connection
from pathlib import Path
import logging
from dataclasses import dataclass
import sys

import settings


log = logging.getLogger('app.db')


MIGRATION_DIR = Path('migrations')
DATABASE_NAMES = ['cache', 'music', 'offline', 'meta']


def _open_sql(db_name: str):
    return open(f'sql/{db_name}.sql', 'r', encoding='utf-8')


def _connect(db_name: str, read_only: bool, foreign_keys: bool = True) -> Connection:
    db_path = Path(settings.data_path, db_name + '.db').absolute().as_posix()
    db_uri = f'file:{db_path}' + ('?mode=ro' if read_only else '')
    conn = sqlite3.connect(db_uri, uri=True, timeout=10.0)
    conn.execute('PRAGMA foreign_keys = ' + ('ON' if foreign_keys else 'OFF'))
    if not read_only:  # pragma sometimes throws error when executed in read-only mode
        conn.execute('PRAGMA journal_mode = WAL')
    if db_name == 'cache':
        conn.execute('PRAGMA auto_vacuum = INCREMENTAL')
    elif db_name == 'offline':
        conn.execute('PRAGMA auto_vacuum = FULL')
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
    if Path(settings.data_path, 'meta.db').exists():
        return

    for db_name in DATABASE_NAMES:
        log.info('Creating database: %s', db_name)
        with _open_sql(db_name) as sql_file:
            with _connect(db_name, False) as conn:
                conn.executescript(sql_file.read())

    with _connect('meta', False) as conn:
        migrations = get_migrations()
        if len(migrations) > 0:
            version = migrations[-1].to_version
        else:
            version = 0

        log.info('Setting initial database version to %s', version)

        conn.execute('INSERT INTO db_version VALUES(?)', (version,))


@dataclass
class Migration:
    file_name: str
    to_version: int
    db_name: str

    def run(self):
        # Very important to disable foreign keys here, or data might get deleted!
        with _connect(self.db_name, False, False) as conn:
            with open(Path(MIGRATION_DIR, self.file_name), encoding='utf-8') as migration_sql:
                conn.executescript(migration_sql.read())


def get_migrations() -> list[Migration]:
    migration_file_names = [path.name for path in MIGRATION_DIR.iterdir()
                            if path.name.endswith('.sql')]

    migrations: list[Migration] = []

    for i, file_name in enumerate(migration_file_names):
        name_split = file_name.split('-')
        assert len(name_split) == 2, name_split
        to_version = int(name_split[0])
        db_name = name_split[1][:-4]
        assert i + 1 == int(name_split[0]), f'{i} | {int(name_split[0])}'
        assert db_name in DATABASE_NAMES, db_name
        migrations.append(Migration(file_name, to_version, db_name))

    return migrations


def migrate():
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

if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    migrate()
