import functools
import os
import time

from prometheus_client import Gauge

from raphson_mp import db


def _file_size(path):
    return os.stat(path).st_size


def _active_players():
    with db.connect(read_only=True) as conn:
        return conn.execute('SELECT COUNT(*) FROM now_playing WHERE timestamp > ?',

                            (int(time.time()) - 30,)).fetchone()[0]

def register_collectors():
    # Database size
    g_database_size = Gauge('database_size', 'Size of SQLite database files', labelnames=('database',))
    for db_name in db.DATABASE_NAMES:
        db_path = db.db_path(db_name)
        g_database_size.labels(db_name).set_function(functools.partial(_file_size, db_path))

    # Active players
    Gauge('active_players', 'Active players').set_function(_active_players)
