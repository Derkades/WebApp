from flask import Blueprint, Response, redirect, render_template, request

import auth
import db
import metadata

bp = Blueprint('dislikes', __name__, url_prefix='/dislikes')


@bp.route('/add', methods=['POST'])
def route_add():
    """Used by music player"""
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])
        track = request.json['track']
        conn.execute('INSERT OR IGNORE INTO never_play (user, track) VALUES (?, ?)',
                     (user.user_id, track))
    return Response(None, 200)


@bp.route('/remove', methods=['POST'])
def route_remove():
    """Used by form on dislikes page"""
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        conn.execute('DELETE FROM never_play WHERE user=? AND track=?',
                     (user.user_id, request.form['track']))

    return redirect('/dislikes')


@bp.route('/')
def route_dislikes():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
        csrf_token = user.get_csrf()
        rows = conn.execute('''
                            SELECT playlist, track
                            FROM never_play JOIN track on never_play.track = track.path
                            WHERE user=?
                            ''', (user.user_id,)).fetchall()
        tracks = [{'path': path,
                   'playlist': playlist,
                   'title': metadata.cached(conn, path).display_title()}
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
        rows = conn.execute('SELECT track FROM never_play WHERE user=?',
                            (user.user_id,)).fetchall()

    return {'tracks': [row[0] for row in rows]}
