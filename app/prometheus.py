import os
import functools

from prometheus_client import Gauge

from app import db

def file_size(path):
    return os.stat(path).st_size

g_database_size = Gauge('database_size', 'Size of SQLite database files', labelnames=('database',))
for db_name in db.DATABASE_NAMES:
    db_path = db.db_path(db_name)
    g_database_size.labels(db_name).set_function(functools.partial(file_size, db_path))
