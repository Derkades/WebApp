from pathlib import Path
import hashlib
import os
import settings

class CacheObject:

    def __init__(self, path: Path):
        self.path = path

    def exists(self) -> bool:
        if not self.path.exists():
            return False
        if os.stat(self.path).st_size == 0:
            return False
        return True

    def store(self, data: bytes):
        with open(self.path, 'wb') as f:
            f.write(data)
            f.truncate(len(data))

    def retrieve(self) -> bytes:
        with open(self.path, 'rb') as f:
            return f.read()


def get(cache_type: str, name: str) -> CacheObject:
    digest = hashlib.sha256((cache_type + name).encode()).hexdigest()
    try:
        Path(settings.cache_dir, digest[:2]).mkdir()
    except FileExistsError:
        pass
    path = Path(settings.cache_dir, digest[:2], digest[2:])
    return CacheObject(path)
