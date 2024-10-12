import functools
import os
import time

from prometheus_client import Gauge

from raphson_mp import db


def file_size(path):
    return os.stat(path).st_size


g_database_size = Gauge('database_size', 'Size of SQLite database files', labelnames=('database',))
for db_name in db.DATABASE_NAMES:
    db_path = db.db_path(db_name)
    g_database_size.labels(db_name).set_function(functools.partial(file_size, db_path))


def active_players():
    with db.connect(read_only=True) as conn:
        return conn.execute('SELECT COUNT(*) FROM now_playing WHERE timestamp > ?',
                            (int(time.time()) - 30,)).fetchone()[0]


Gauge('active_players', 'Active players').set_function(active_players)
