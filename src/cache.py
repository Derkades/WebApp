from typing import Optional
from pathlib import Path
import hashlib
import os
import logging
import random

import settings

log = logging.getLogger('app.cache')

class CacheObject:

    def __init__(self, data_path: Path, checksum_path: Optional[Path]):
        self.data_path = data_path
        self.checksum_path = checksum_path

    def store(self, data: bytes):
        """
        Store data to cache file, also update checksum file
        """
        with open(self.data_path, 'wb') as data_file:
            data_file.truncate(len(data))
            data_file.write(data)

        if self.checksum_path is not None:
            checksum = hashlib.sha256(data).digest()
            with open(self.checksum_path, 'wb') as checksum_file:
                checksum_file.write(checksum)


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
            if self.checksum_path is not None:
                try:
                    self.checksum_path.unlink()
                except FileNotFoundError:
                    pass
            return None

        return data

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
        if self.checksum_path is not None:
            checksum: bytes = self.get_checksum()
            with open(self.checksum_path, 'wb') as checksum_file:
                checksum_file.write(checksum)

    def check_checksum(self, data: bytes) -> bool:
        """
        Calculate checksum for given data, and verify that it matches the checksum file
        """
        if self.checksum_path is None:
            # Legacy cache file without checksum file
            # Assume it's fine if file size is non-zero
            return os.stat(self.data_path).st_size > 0

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
    legacy_digest = _digest(cache_type + name)
    legacy_path = _path(legacy_digest)
    if legacy_path.exists():
        log.info('Legacy cache file %s-%s: %s', cache_type, name, legacy_path.as_posix())
        if random.random() > 0.1:
            return CacheObject(legacy_path, None)
        else:
            log.info('Deleting legacy cache file')
            legacy_path.unlink()

    data_digest = _digest(cache_type + name + 'data')
    checksum_digest = _digest(cache_type + name + 'checksum')
    data_path = _path(data_digest)
    checksum_path = _path(checksum_digest)
    _mkparent(data_path)
    _mkparent(checksum_path)
    return CacheObject(data_path, checksum_path)
