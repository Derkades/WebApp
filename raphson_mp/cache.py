"""
Functions related to the cache (cache.db)
"""

import logging
import pickle
import random
import time
from typing import Any

from raphson_mp import db, jsonw

log = logging.getLogger(__name__)

HOUR = 60*60
DAY = 24*HOUR
WEEK = 7*DAY
MONTH = 30*DAY
HALFYEAR = 6*MONTH
YEAR = 12*MONTH


def store(key: str,
          data: bytes,
          duration: int) -> None:
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
                     INSERT OR REPLACE INTO cache (key, data, expire_time)
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
        row = conn.execute('SELECT data, expire_time FROM cache WHERE key=?',
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
    """
    Remove any cache entries that are beyond their expire time.
    """
    with db.cache() as conn:
        count = conn.execute('DELETE FROM cache WHERE expire_time < ?',
                            (int(time.time()),)).rowcount
        # The number of vacuumed pages is limited to prevent this function
        # from blocking for too long. Max 65536 pages = 256MiB
        conn.execute('PRAGMA incremental_vacuum(65536)')
        log.info('Deleted %s entries from cache', count)


def store_json(key: str, data: dict[Any, Any], duration: int) -> None:
    """
    Dump dict as json, encode as utf-8 and then use store()
    """
    store(key, jsonw.to_json(data).encode(), duration)


def retrieve_json(key: str, **kwargs) -> dict[Any, Any] | None:
    """
    Retrieve bytes, if exists decode and return dict
    """
    data = retrieve(key, **kwargs)
    if data is None:
        return None

    return jsonw.from_json(data.decode())
