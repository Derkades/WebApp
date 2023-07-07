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


def _legacy_cleanup() -> int:
    """
    Remove entries from cache that have not been used for a long time
    Returns: Number of removed entries
    """
    with db.cache() as conn:
        month_ago = int(time.time()) - 30*24*60*60
        return conn.execute('DELETE FROM cache WHERE access_time < ?', (month_ago,)).rowcount


def store(key: str,
          data: bytes,
          duration: int | None = None) -> None:
    with db.cache() as conn:
        if duration is None:
            # Varying cache duration, between 30 and 60 days
            duration = random.randint(30*24*60*60, 60*24*60*60)

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
            # Not cached, try legacy cache
            # Don't update access_time, so entries are slowly deleted by cleanup()
            row = conn.execute('SELECT data FROM cache WHERE key=?',
                               (key,)).fetchone()

            if row is None:
                return None

            log.info('Cache entry returned from legacy cache')
            return row[0]

        data, expire_time = row

        if expire_time < time.time():
            if return_expired:
                log.info('Cache entry has expired, returning it anyway')
                return data

            return None

        return data


def cleanup():
    # Also cleanup old table
    legacy_rowcount = _legacy_cleanup()
    log.info('Deleted %s entries from legacy cache', legacy_rowcount)

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
