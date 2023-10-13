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


def store(key: str,
          data: bytes,
          duration: int = 60*24*60*60) -> None:
    """
    Args:
        key: Cache key
        data: Data to cache
        duration: Suggested cache duration in seconds. Duration may be extended by up to 50%.
    """
    with db.cache() as conn:
        # Vary cache duration so cached data doesn't all expire at once
        duration += random.randint(0, duration // 2)

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


def cleanup():
    with db.cache() as conn:
        return conn.execute('DELETE FROM cache2 WHERE expire_time < ?',
                            (int(time.time()),)).rowcount


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
