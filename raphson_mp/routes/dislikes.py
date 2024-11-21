from sqlite3 import Connection
from typing import cast
from flask import Blueprint, Response, redirect, render_template, request

from raphson_mp import auth, db
from raphson_mp.decorators import route
from raphson_mp.music import Track
from raphson_mp.auth import User

bp = Blueprint('dislikes', __name__, url_prefix='/dislikes')


@route(bp, '/add', methods=['POST'], write=True)
def route_add(conn: Connection, user: User):
    """Used by music player"""
    track_path = cast(str, request.json['track'])
    conn.execute('INSERT OR IGNORE INTO dislikes (user, track) VALUES (?, ?)',
                    (user.user_id, track_path))
    return Response(None, 200)


@route(bp, '/remove', methods=['POST'], write=True)
def route_remove(conn: Connection, user: User):
    """Used by form on dislikes page"""
    conn.execute('DELETE FROM dislikes WHERE user=? AND track=?',
                    (user.user_id, request.form['track']))
    return redirect('/dislikes', code=303)


@route(bp, '')
def route_dislikes(conn: Connection, user: User):
    """
    Page showing a table with disliked tracks, with buttons to undo disliking each trach.
    """
    rows = conn.execute('''
                        SELECT playlist, track
                        FROM dislikes JOIN track on dislikes.track = track.path
                        WHERE user=?
                        ''', (user.user_id,)).fetchall()
    tracks = [{'path': path,
                'playlist': playlist,
                'title': cast(Track, Track.by_relpath(conn, path)).metadata().display_title()}
                for playlist, path in rows]

    return render_template('dislikes.jinja2',
                           tracks=tracks)


@route(bp, '/json')
def route_json(conn: Connection, user: User):
    """
    Return disliked track paths in json format, for offline mode sync
    """
    rows = conn.execute('SELECT track FROM dislikes WHERE user=?',
                            (user.user_id,)).fetchall()

    return {'tracks': [row[0] for row in rows]}
