from flask import Blueprint, Response, redirect, render_template, request

from raphson_mp import auth, db
from raphson_mp.music import Track

bp = Blueprint('dislikes', __name__, url_prefix='/dislikes')


@bp.route('/add', methods=['POST'])
def route_add():
    """Used by music player"""
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)
        track = request.json['track']
        conn.execute('INSERT OR IGNORE INTO dislikes (user, track) VALUES (?, ?)',
                     (user.user_id, track))
    return Response(None, 200)


@bp.route('/remove', methods=['POST'])
def route_remove():
    """Used by form on dislikes page"""
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)
        conn.execute('DELETE FROM dislikes WHERE user=? AND track=?',
                     (user.user_id, request.form['track']))

    return redirect('/dislikes', code=303)


@bp.route('')
def route_dislikes():
    """
    Page showing a table with disliked tracks, with buttons to undo disliking each trach.
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
        csrf_token = user.get_csrf()
        rows = conn.execute('''
                            SELECT playlist, track
                            FROM dislikes JOIN track on dislikes.track = track.path
                            WHERE user=?
                            ''', (user.user_id,)).fetchall()
        tracks = [{'path': path,
                   'playlist': playlist,
                   'title': Track.by_relpath(conn, path).metadata().display_title()}
                  for playlist, path in rows]

    return render_template('dislikes.jinja2',
                           csrf_token=csrf_token,
                           tracks=tracks)


@bp.route('/json')
def route_json():
    """
    Return disliked track paths in json format, for offline mode sync
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        rows = conn.execute('SELECT track FROM dislikes WHERE user=?',
                            (user.user_id,)).fetchall()

    return {'tracks': [row[0] for row in rows]}
