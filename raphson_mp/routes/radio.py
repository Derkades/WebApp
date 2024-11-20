from sqlite3 import Connection
from flask import Blueprint, render_template

from raphson_mp import db, radio
from raphson_mp.auth import User
from raphson_mp.decorators import route

bp = Blueprint('radio', __name__, url_prefix='/radio')


@route(bp, '/info')
def route_info(conn: Connection, _user: User):
    """
    Endpoint that returns information about the current and next radio track
    """
    current_track = radio.get_current_track(conn)
    next_track = radio.get_next_track(conn)

    return {
        'current': current_track.track.info_dict(),
        'current_time': current_track.start_time,
        'next': next_track.track.info_dict(),
        'next_time': next_track.start_time,
    }


@route(bp, '', redirect_to_login=True)
def route_radio_home(_conn: Connection, _user: User):
    return render_template('radio.jinja2')
