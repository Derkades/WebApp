import functools
import time

from prometheus_client import Gauge

from raphson_mp import db


def _active_players():
    with db.connect(read_only=True) as conn:
        return conn.execute('SELECT COUNT(*) FROM now_playing WHERE timestamp > ?',

                            (int(time.time()) - 30,)).fetchone()[0]

# Database size
g_database_size = Gauge('database_size', 'Size of SQLite database files', labelnames=('database',))
for db_name in db.DATABASE_NAMES:
    g_database_size.labels(db_name).set_function(functools.partial(db.db_size, db_name))

# Active players
Gauge('active_players', 'Active players').set_function(_active_players)
