import logging
import tempfile
from pathlib import Path

from flask import (Blueprint, Response, abort, render_template, request,
                   send_file)

from raphson_mp import auth, cache, db, music, scanner

log = logging.getLogger(__name__)
bp = Blueprint('download', __name__, url_prefix='/download')


@bp.route('')
def route_download():
    """Download page"""
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        playlists = [(playlist.name, playlist.write)
                     for playlist in music.user_playlists(conn, user.user_id, all_writable=user.admin)]

    return render_template('download.jinja2',
                           csrf_token=csrf_token,
                           primary_playlist=user.primary_playlist,
                           playlists=playlists)


@bp.route('/search', methods=['POST'])
def route_search():
    """Search using yt-dlp"""
    from raphson_mp import downloader

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn, require_csrf=True)

        query = request.json['query']
        results = downloader.search(query)

    return {'results': results}


@bp.route('/ytdl', methods=['POST'])
def route_ytdl():
    """
    Use yt-dlp to download the provided URL to a playlist directory
    """
    from raphson_mp import downloader

    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        directory = request.json['directory']
        url = request.json['url']

        playlist = music.playlist(conn, directory)
        if not playlist.has_write_permission(user):
            abort(403, 'No write permission for this playlist')

        log.info('ytdl %s %s', directory, url)

    # Release database connection during download

    def generate():
        status_code = yield from downloader.download(playlist.path, url)
        if status_code == 0:
            yield 'Scanning playlists...\n'
            with db.connect() as conn:
                playlist2 = music.playlist(conn, directory)
                scanner.scan_tracks(conn, playlist2.name)
            yield 'Done!'
        else:
            yield f'Failed with status code {status_code}'

    return Response(generate(), content_type='text/plain')


@bp.route('/ephemeral')
def route_ephemeral():
    from raphson_mp import downloader

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            for _log in downloader.download(tempdir, request.args['url']):
                pass
            response = send_file(next(temp_path.iterdir()))
            return response
