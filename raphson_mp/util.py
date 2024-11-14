import difflib
import logging
from collections.abc import Iterator
from io import IOBase
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import override
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

    @override
    def close(self):
        super().close()
        self.queue.put(None)

    @override
    def readable(self):
        return False

    @override
    def seekable(self):
        return False

    @override
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


def str_match(a: str, b: str) -> bool:
    if a == b:
        return True

    a = a.lower()
    b = b.lower()

    if a == b:
        return True

    diff = difflib.SequenceMatcher(None, a, b)
    # real_quick_ratio() provides an upper bound on quick_ratio(), which provides an upper bound on ratio()
    # ratio() is expensive so we must avoid it when possible
    return diff.real_quick_ratio() > 0.8 and diff.quick_ratio() > 0.8 and diff.ratio() > 0.8


def substr_keyword(text: str, start: str, end: str):
    start_i = text.index(start) + len(start)
    end_i = start_i + text[start_i:].index(end)
    return text[start_i:end_i]
