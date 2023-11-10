from pathlib import Path

import settings


def pack(path: Path) -> bytes:
    """
    Combine all files in a directory into a single file
    """
    if not settings.dev:
        raise RuntimeError('Python asset packer must only be used during development')

    content = b''
    for path in sorted(path.iterdir()):
        content += path.read_bytes()
    return content
