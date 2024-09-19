import logging
from threading import Thread

from flask import Blueprint, Response, abort, render_template, request, send_file
from zipfile import ZipFile, ZIP_LZMA
from io import BytesIO, IOBase
from app import auth, db, music, scanner
from app.jsonw import to_json
from typing import Iterable, Iterator
import json
from queue import Queue
from dataclasses import dataclass

log = logging.getLogger('app.routes.export')
bp = Blueprint('export', __name__, url_prefix='/export')

def query_to_json(cursor, one=False):
    # Based on: https://stackoverflow.com/a/3287775
    r = [dict((cursor.description[i][0], value) \
               for i, value in enumerate(row)) for row in cursor.fetchall()]
    return (r[0] if r else None) if one else r


@dataclass
class ExportQuery:
    name: str
    query: str
    params: Iterable[str|int]
    one: bool


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


def generate_zip(queue_io: QueueIO, user_id: int):
    with db.connect(read_only=True) as conn:
        queries: list[ExportQuery] = [
            ExportQuery('user', 'SELECT * FROM user WHERE id = ?', (user_id,), True),
            ExportQuery('favorite_playlists', 'SELECT playlist FROM user_playlist_favorite WHERE user = ?', (user_id,), False),
            ExportQuery('sessions', 'SELECT creation_date, user_agent, remote_address, last_use FROM session WHERE user = ?', (user_id,), False),
            ExportQuery('history', 'SELECT id, timestamp, track, playlist, private FROM history WHERE user = ?', (user_id,), False),
            ExportQuery('dislikes', 'SELECT track FROM dislikes WHERE user = ?', (user_id,), False),
            ExportQuery('shares', 'SELECT share_code, track, create_timestamp FROM shares WHERE user = ?', (user_id,), False),
            ExportQuery('playlists', 'SELECT path FROM playlist', (), False),
            ExportQuery('tracks', 'SELECT * FROM track', (), False),
        ]

        with ZipFile(queue_io, 'w') as zf:
            for query in queries:
                json_str = json.dumps(query_to_json(conn.execute(query.query, query.params), query.one), indent=4)
                zf.writestr(query.name + '.json', json_str, compress_type=ZIP_LZMA)

        queue_io.close()


@bp.route('/data')
def data():
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)

    queue_io = QueueIO()
    Thread(target=generate_zip, args=(queue_io, user.user_id)).start()
    return Response(queue_io.iterator(), direct_passthrough=True, mimetype='application/zip')
