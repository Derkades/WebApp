from collections.abc import Iterator
import logging
from sqlite3 import Connection
import tempfile
from pathlib import Path
from typing import cast

from flask import (Blueprint, Response, abort, render_template, request,
                   send_file)

from raphson_mp import auth, db, downloader, music, scanner
from raphson_mp.decorators import route
from raphson_mp.auth import User

log = logging.getLogger(__name__)
bp = Blueprint('download', __name__, url_prefix='/download')


@route(bp, '', redirect_to_login=True)
def route_download(conn: Connection, user: User):
    """Download page"""
    playlists = [(playlist.name, playlist.write)
                     for playlist in music.user_playlists(conn, user.user_id, all_writable=user.admin)]

    return render_template('download.jinja2',
                           primary_playlist=user.primary_playlist,
                           playlists=playlists)


@route(bp, '/search', methods=['POST'])
def route_search():
    """Search using yt-dlp"""
    query =cast(str, request.json['query'])
    return {'results': downloader.search(query)}


@route(bp, '/ytdl', methods=['POST'])
def route_ytdl(conn: Connection, user: User):
    """
    Use yt-dlp to download the provided URL to a playlist directory
    """
    directory: str = cast(str, request.json['directory'])
    url: str = cast(str, request.json['url'])

    playlist = music.playlist(conn, directory)
    if not playlist.has_write_permission(user):
        abort(403, 'No write permission for this playlist')

    log.info('ytdl %s %s', directory, url)

    # Release database connection during download

    def generate() -> Iterator[str]:
        status_code = yield from downloader.download(playlist.path, url)
        if status_code == 0:
            yield 'Scanning playlists...\n'
            with db.connect() as writable_conn:
                playlist2 = music.playlist(conn, directory)
                scanner.scan_tracks(writable_conn, playlist2.name)
            yield 'Done!'
        else:
            yield f'Failed with status code {status_code}'

    return Response(generate(), content_type='text/plain')


@route(bp, '/ephemeral')
def route_ephemeral():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        for _log in downloader.download(temp_path, request.args['url']):
            pass
        response = send_file(next(temp_path.iterdir()))
        return response
