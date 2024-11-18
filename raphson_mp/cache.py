"""
Functions related to the cache (cache.db)
"""
import hashlib
import logging
from pathlib import Path
import random
import shutil
import time
from typing import Any, Callable

from flask import request, send_file
from werkzeug.wrappers import Response

from raphson_mp import db, jsonw, settings

log = logging.getLogger(__name__)

HOUR = 60*60
DAY = 24*HOUR
WEEK = 7*DAY
MONTH = 30*DAY
HALFYEAR = 6*MONTH
YEAR = 12*MONTH

# Files larger than this size will be stored in external files. Can be changed without affecting existing cache.
EXTERNAL_SIZE = 10*1024*1024


def _external_path(name: str) -> Path:
    dir = Path(settings.data_dir, 'cache')
    dir.mkdir(exist_ok=True)
    return dir / name


def store(key: str,
          data: bytes | Path,
          duration: int) -> None:
    """
    Args:
        key: Cache key
        data: Data to cache
        duration: Suggested cache duration in seconds. Cache duration is varied by up to 25%, to
                  avoid high load when cache entries all expire at roughly the same time.
    """
    with db.cache() as conn:
        # Vary cache duration so cached data doesn't expire all at once
        duration += random.randint(-duration // 4, duration // 4)

        external = False
        if isinstance(data, Path):
            if data.stat().st_size > EXTERNAL_SIZE:
                file_name = hashlib.blake2s(key.encode()).hexdigest()
                external_path = _external_path(file_name)
                log.info('copy %s to external cache file: %s', data.as_posix(), external_path)
                shutil.copyfile(data, external_path)
                data = file_name.encode()  # cached data becomes file name
                external = True
            else:
                data = data.read_bytes()
        else:
            if len(data) > EXTERNAL_SIZE:
                file_name = hashlib.blake2s(key.encode()).hexdigest()
                external_path = _external_path(file_name)
                log.info('write data to external file: %s', external_path)
                _external_path(file_name).write_bytes(data)
                data = file_name.encode()  # cached data becomes file name
                external = True

        expire_time = int(time.time()) + duration
        conn.execute("""
                     INSERT OR REPLACE INTO cache (key, data, expire_time, external)
                     VALUES (?, ?, ?, ?)
                     """, (key, data, expire_time, external))


def retrieve(key: str,
             return_expired: bool = True) -> bytes | None:
    """
    Retrieve object from cache
    Args:
        key: Cache key
        partial: Return partial data in the specified range (start, length)
        return_expired: Whether to return the object from cache even when expired, but not cleaned
                        up yet. Should be set to False for short lived cache objects.
    """
    with db.cache(read_only=True) as conn:
        row = conn.execute('SELECT data, expire_time, external FROM cache WHERE key=?',
                           (key,)).fetchone()

        if row is None:
            return None

        data, expire_time, external = row

        if not return_expired and expire_time < time.time():
            return None

        # Allow reading external cache files using standard retrieve(), but
        # since these files may be larger than memory, other methods should
        # be preferred instead.
        if external:
            external_path = _external_path(data.decode())
            log.warning('reading large external file into memory: %s', external_path.as_posix())
            data = external_path.read_bytes()

        return data


def retrieve_response(key: str,
                      mimetype: str,
                      return_expired: bool = True) -> Response | None:
    with db.cache(read_only=True) as conn:
        row = conn.execute('SELECT data, expire_time, external FROM cache WHERE key=?',
                           (key,)).fetchone()

        if row is None:
            return None

        data, expire_time, external = row

        if not return_expired and expire_time < time.time():
            return None

        if external:
            log.info('returning response using send_file')
            external_path = _external_path(data.decode())
            return send_file(external_path, mimetype)

        log.info('not an external file, returning full data in response')
        return Response(data, mimetype=mimetype)


def cleanup() -> None:
    """
    Remove any cache entries that are beyond their expire time.
    """
    # TODO clean up external cache entries
    with db.cache() as conn:
        count = conn.execute('DELETE FROM cache WHERE expire_time < ? AND external = false',
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
