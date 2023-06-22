"""
Functions related to the cache (cache.db)
"""

from typing import Any
import logging
import json
import time
import random

import db


# Number of seconds after which cache entries are considered outdated
CACHE_OUTDATED_TIME = 60*60*24*60  # 2 months
CACHE_OUTDATED_PROB = 0.05

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
        row = conn.execute('SELECT data, update_time FROM cache WHERE key=?',
                           (key,)).fetchone()

        if row is None:
            # Not cached
            return None

        data, update_time = row

        current_time = int(time.time())

        # log.info('Cache entry last updated %s days ago', int((current_time - update_time) / (60 * 60 * 24)))

        if current_time - update_time > CACHE_OUTDATED_TIME and random.random() < CACHE_OUTDATED_PROB:
            log.info('Cache entry is outdated, pretend it doesn\'t exist')
            # Pretend it's not cached
            return None

        conn.execute('UPDATE cache SET access_time=? WHERE key=?',
                     (current_time, key))

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
        two_months_ago = int(time.time()) - 60*60*24*30*2
        return conn.execute('DELETE FROM cache WHERE access_time < ?', (two_months_ago,)).rowcount
