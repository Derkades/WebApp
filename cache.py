from pathlib import Path
import hashlib
import os

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


class Cache:

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def get(self, cache_type: str, name: str) -> CacheObject:
        digest = hashlib.sha256((cache_type + name).encode()).hexdigest()
        try:
            Path(self.base_dir, digest[:2]).mkdir()
        except FileExistsError:
            pass
        path = Path(self.base_dir, digest[:2], digest[2:])
        return CacheObject(path)
