from pathlib import Path


def pack(path: Path) -> bytes:
    """
    Combine all files in a directory into a single file
    """
    content = b''
    for path in sorted(path.iterdir()):
        content += path.read_bytes()
    return content
