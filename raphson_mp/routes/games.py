from flask import Blueprint, render_template

from raphson_mp import auth, db

bp = Blueprint('games', __name__, url_prefix='/games')


@bp.route('/guess')
def route_guess():
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
    return render_template('games_guess.jinja2',
                           csrf_token=user.get_csrf())


@bp.route('/chairs')
def route_chairs():
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
    return render_template('games_chairs.jinja2',
                           csrf_token=user.get_csrf())
