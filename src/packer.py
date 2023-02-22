from pathlib import Path

import settings


def pack(path: Path) -> bytes:
    if not settings.dev:
        raise Exception('Python asset packer must only be used during development')

    content = b''
    for path in sorted(path.iterdir()):
        with open(path, 'rb') as file:
            content += file.read()
    return content
