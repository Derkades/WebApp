from sqlite3 import Connection
from typing import cast
from flask import Blueprint, Response, request

from raphson_mp import db
from raphson_mp.auth import User
from raphson_mp.decorators import route

bp = Blueprint('activity', __name__, url_prefix='/activity')

@route(bp, '/now_playing', methods=['POST'], public=True)
def route_now_playing():
    return Response(None, 200)

@route(bp, '/played', methods=['POST'], public=True)
def route_played():
    with db.offline() as conn:
        track = cast(str, request.json['track'])
        timestamp = cast(int, request.json['timestamp'])
        conn.execute('INSERT INTO history VALUES (?, ?)', (timestamp, track))
    return Response(None, 200)
