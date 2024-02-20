"""
Functions related to the cache (cache.db)
"""

import logging
import random
import time
from typing import Any

from app import db, jsonw

log = logging.getLogger('app.cache')

HOUR = 60*60
DAY = 24*HOUR
WEEK = 7*DAY
MONTH = 30*DAY
DEFAULT = 4*MONTH


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
    """
    Retrieve object from cache
    Args:
        key: Cache key
        return_expired: Whether to return the object from cache even when expired, but not cleaned
                        up yet. Should be set to False for short lived cache objects.
    """
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
        count = conn.execute('DELETE FROM cache2 WHERE expire_time < ?',
                            (int(time.time()),)).rowcount
        # The number of vacuumed pages is limited to prevent this function
        # from blocking for too long. Max 65536 pages = 256MiB
        conn.execute('PRAGMA incremental_vacuum(65536)')
        log.info('Deleted %s entries from cache', count)


def store_json(key: str, data: Any, **kwargs) -> None:
    """
    Dump object as json, encode as utf-8 and then use store()
    """
    store(key, jsonw.to_json(data).encode(), **kwargs)


def retrieve_json(cache_key: str, **kwargs) -> Any | None:
    """
    Retrieve bytes, if exists decode and return object
    """
    data = retrieve(cache_key, **kwargs)
    if data is None:
        return None

    return jsonw.from_json(data.decode())
