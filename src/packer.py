from pathlib import Path

import settings


class PackedAsset:

    path: Path
    content: bytes

    def __init__(self, path: Path):
        self.path = path
        self.pack()

    def pack(self) -> None:
        self.content = b''
        for path in sorted(self.path.iterdir()):
            with open(path, 'rb') as file:
                self.content += file.read()

    def get_bytes(self) -> bytes:
        if settings.dev:
            # During development, assets might change while the app is running
            self.pack()

        return self.content
