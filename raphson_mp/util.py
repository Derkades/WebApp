import logging
from io import IOBase
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Iterator
from zipfile import ZipFile

from flask import Response, request

log = logging.getLogger(__name__)


def check_filename(name: str) -> None:
    """
    Ensure file name is valid, if not raise ValueError
    """
    if '/' in name or name == '.' or name == '..':
        raise ValueError('illegal name')


def is_mobile() -> bool:
    """
    Checks whether User-Agent looks like a mobile device (Android or iOS)
    """
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Android' in user_agent or 'iOS' in user_agent:
            return True
    return False


class QueueIO(IOBase):
    queue: Queue[bytes|None]

    def __init__(self) -> None:
        self.queue = Queue(maxsize=32)

    def close(self):
        super().close()
        self.queue.put(None)

    def readable():
        return False

    def seekable():
        return False

    def write(self, data: bytes):
        self.queue.put(data)
        return len(data)

    def iterator(self) -> Iterator[bytes]:
        while True:
            data = self.queue.get(True)
            if data is None:
                return

            yield data


def _send_directory(queue_io: QueueIO, path: Path):
    with ZipFile(queue_io, 'w') as zf:
        for subpath in path.glob('**/*'):
            zf.write(subpath, arcname=subpath.relative_to(path))

    queue_io.close()

def send_directory(path: Path):
    """
    Flask response sending directory contents as ZipFile
    """
    if not path.is_dir():
        raise NotADirectoryError(path)
    queue_io = QueueIO()
    Thread(target=_send_directory, args=(queue_io, path)).start()
    response = Response(queue_io.iterator(), direct_passthrough=True, mimetype='application/zip')
    response.headers['Content-Disposition'] = f'attachment; filename="{path.name}.zip"'
    return response
