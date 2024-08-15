from flask import Blueprint, render_template
from app import db, auth

bp = Blueprint('games', __name__, url_prefix='/games')


@bp.route('/guess')
def route_guess():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
    return render_template('games_guess.jinja2')
