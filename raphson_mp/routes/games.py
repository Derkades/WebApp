from sqlite3 import Connection
from flask import Blueprint, render_template

from raphson_mp import db
from raphson_mp.auth import User
from raphson_mp.decorators import route

bp = Blueprint('games', __name__, url_prefix='/games')


@route(bp, '/guess', redirect_to_login=True)
def route_guess(_conn: Connection, user: User):
    return render_template('games_guess.jinja2')


@route(bp, '/chairs', redirect_to_login=True)
def route_chairs(_conn: Connection, user: User):
    return render_template('games_chairs.jinja2')
