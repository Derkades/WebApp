"""
Functions related to the cache (cache.db)
"""

from typing import Any
import logging
import json
import time
import random

import db


log = logging.getLogger('app.cache')


WEEK = 7*24*60*60
MONTH = 30*24*60*60
DEFAULT = 90*24*60*60
YEAR = 365*24*60*60


def store(key: str,
          data: bytes,
          duration: int = DEFAULT) -> None:
    """
    Args:
        key: Cache key
        data: Data to cache
        duration: Suggested cache duration in seconds. Cache duration is varied by up to 25%, to
                  avoid high load when cache entries all expire at roughly the same time.
    """
    with db.cache() as conn:
        # Vary cache duration so cached data doesn't all expire at once
        duration += random.randint(-duration // 4, duration // 4)

        expire_time = int(time.time()) + duration
        conn.execute("""
                     INSERT OR REPLACE INTO cache2 (key, data, expire_time)
                     VALUES (?, ?, ?)
                     """, (key, data, expire_time))


def retrieve(key: str,
             return_expired: bool = True) -> bytes | None:
    with db.cache(read_only=True) as conn:
        row = conn.execute('SELECT data, expire_time FROM cache2 WHERE key=?',
                           (key,)).fetchone()

        if row is None:
            return None

        data, expire_time = row

        if expire_time < time.time():
            if return_expired:
                log.info('Cache entry has expired, returning it anyway')
                return data

            return None

        return data


def cleanup() -> None:
    with db.cache() as conn:
        # The number of deleted rows and vacuumed pages is limited to prevent this
        # function from blocking for too long.
        count = conn.execute('DELETE FROM cache2 WHERE expire_time < ? LIMIT 250',
                            (int(time.time()),)).rowcount
        conn.execute('PRAGMA incremental_vacuum(65536)') # max 65536 pages = 256MiB
        log.info('Deleted %s entries from cache', count)


def store_json(key: str, data: Any, **kwargs) -> None:
    """
    Dump object as json, encode as utf-8 and then use store()
    """
    store(key, json.dumps(data).encode(), **kwargs)


def retrieve_json(cache_key: str, **kwargs) -> Any | None:
    """
    Retrieve bytes, if exists decode and return object
    """
    data = retrieve(cache_key, **kwargs)
    if data is None:
        return None

    return json.loads(data.decode())
