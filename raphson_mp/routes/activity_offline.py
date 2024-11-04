from flask import Blueprint, Response, request

from raphson_mp import db

bp = Blueprint('activity', __name__, url_prefix='/activity')

@bp.route('/now_playing', methods=['POST'])
def route_now_playing():
    return Response(None, 200)

@bp.route('/played', methods=['POST'])
def route_played():
    with db.offline() as conn:
        track = request.json['track']
        timestamp = request.json['timestamp']
        conn.execute('INSERT INTO history VALUES (?, ?)',
                        (timestamp, track))
    return Response(None, 200)
