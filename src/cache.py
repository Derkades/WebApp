"""
Functions related to the cache (cache.db)
"""

from typing import Any
import logging
import json
import time

import db


log = logging.getLogger('app.cache')


def store(key: str, data: bytes) -> None:
    """
    Save data to cache
    """
    with db.cache() as conn:
        timestamp = int(time.time())
        conn.execute("""
                     INSERT OR REPLACE INTO cache (key, data, update_time, access_time)
                     VALUES (?, ?, ?, ?)
                     """, (key, data, timestamp, timestamp))


def store_json(key: str, data: Any) -> None:
    """
    Dump object as json, encode as utf-8 and then use store()
    """
    store(key, json.dumps(data).encode())


def retrieve(key: str) -> bytes | None:
    """
    Retrieve data from cache.
    Returns: Cached data bytes or None if data is not cached.
    """
    with db.cache() as conn:
        row = conn.execute('SELECT data FROM cache WHERE key=?',
                           (key,)).fetchone()

        if row is None:
            # Not cached
            return None

        data, = row

        timestamp = int(time.time())
        conn.execute('UPDATE cache SET access_time=? WHERE key=?',
                     (timestamp, key))

        return data

def retrieve_json(cache_key: str) -> Any | None:
    """
    Retrieve bytes, if exists decode and return object
    """
    data = retrieve(cache_key)
    if data is None:
        return None

    return json.loads(data.decode())

def cleanup() -> int:
    """
    Remove entries from cache that have not been used for a long time
    Returns: Number of removed entries
    """
    with db.cache() as conn:
        one_month_ago = int(time.time()) - 60*60*24*30
        return conn.execute('DELETE FROM cache WHERE access_time < ?', (one_month_ago,)).rowcount
