from typing import Optional
from pathlib import Path
import hashlib
import logging
import json

import settings

log = logging.getLogger('app.cache')

class CacheObject:

    def __init__(self, cache_id: str, data_path: Path, checksum_path: Path):
        self.cache_id = cache_id
        self.data_path = data_path
        self.checksum_path = checksum_path

    def store(self, data: bytes):
        """
        Store data to cache file, also update checksum file
        """
        with open(self.data_path, 'wb') as data_file:
            data_file.truncate(len(data))
            data_file.write(data)

        checksum = hashlib.sha256(data).digest()
        with open(self.checksum_path, 'wb') as checksum_file:
            checksum_file.write(checksum)


    def store_json(self, data):
        """
        Dump object as json, encode as utf-8 and then use store()
        """
        self.store(json.dumps(data).encode())

    def retrieve(self) -> Optional[bytes]:
        """
        Retrieve data from cache file. Returns None if cache file does not exist
        or checksum doesn't match (file is corrupt)
        """
        if not self.data_path.exists():
            return None

        with open(self.data_path, 'rb') as f:
            data = f.read()

        if not self.check_checksum(data):
            log.warning('Checksum mismatch! Deleting cache file')
            self.data_path.unlink()
            try:
                self.checksum_path.unlink()
            except FileNotFoundError:
                pass
            return None

        return data

    def retrieve_json(self):
        """
        Retrieve bytes, if exists decode and return object
        """
        data = self.retrieve()
        if data is None:
            return None
        else:
            return json.loads(data.decode())

    def get_checksum(self) -> bytes:
        """
        Compute checksum from file data
        """
        with open(self.data_path, 'rb',) as data_file:
            return hashlib.sha256(data_file.read()).digest()

    def update_checksum(self) -> None:
        """
        Calculate checksum from data file and write it to checksum file. To be used when
        manually writing to the file, instead of using store()
        """
        checksum: bytes = self.get_checksum()
        with open(self.checksum_path, 'wb') as checksum_file:
            checksum_file.write(checksum)

    def check_checksum(self, data: bytes) -> bool:
        """
        Calculate checksum for given data, and verify that it matches the checksum file
        """
        if not self.checksum_path.exists():
            return False

        with open(self.checksum_path, 'rb') as checksum_file:
            expected_checksum = checksum_file.read()

        actual_checksum = hashlib.sha256(data).digest()
        return actual_checksum == expected_checksum


def _digest(inp: str) -> str:
    return hashlib.sha256(inp.encode()).hexdigest()


def _mkparent(path: Path) -> None:
    try:
        path.parent.mkdir()
    except FileExistsError:
        pass


def _path(hex_digest: str) -> Path:
    return Path(settings.cache_dir, hex_digest[:2], hex_digest[2:])


def get(cache_type: str, name: str) -> CacheObject:
    """
    Get CacheObject instance by name
    """
    cache_id = cache_type + name
    data_digest = _digest(cache_id + 'data')
    checksum_digest = _digest(cache_id + 'checksum')
    data_path = _path(data_digest)
    checksum_path = _path(checksum_digest)
    _mkparent(data_path)
    _mkparent(checksum_path)
    return CacheObject(cache_id, data_path, checksum_path)
