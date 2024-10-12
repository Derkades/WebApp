from flask import Blueprint, render_template

from raphson_mp import auth, db, radio

bp = Blueprint('radio', __name__, url_prefix='/radio')


@bp.route('/info')
def route_info():
    """
    Endpoint that returns information about the current and next radio track
    """
    with db.connect() as conn:
        auth.verify_auth_cookie(conn)
        current_track = radio.get_current_track(conn)
        next_track = radio.get_next_track(conn)

        return {
            'current': current_track.track.info_dict(),
            'current_time': current_track.start_time,
            'next': next_track.track.info_dict(),
            'next_time': next_track.start_time,
        }


@bp.route('')
def route_radio_home():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn, redirect_to_login=True)

    return render_template('radio.jinja2')
