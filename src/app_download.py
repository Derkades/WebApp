from flask import Blueprint, render_template, request

import auth
import db
import downloader
import music

bp = Blueprint('download', __name__, url_prefix='/download')


@bp.route('/search', methods=['POST'])
def route_search():
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        query = request.json['query']
        results = downloader.search(query)

    return {'results': results}


@bp.route('/')
def route_download():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        playlists = [(playlist.name, playlist.write)
                     for playlist in music.user_playlists(conn, user.user_id, all_writable=user.admin)]

    return render_template('download.jinja2',
                           csrf_token=csrf_token,
                           primary_playlist=user.primary_playlist,
                           playlists=playlists)
