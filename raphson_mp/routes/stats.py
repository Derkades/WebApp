from sqlite3 import Connection
from flask import Blueprint, render_template, request

from raphson_mp import charts, db, jsonw
from raphson_mp.auth import User
from raphson_mp.charts import StatsPeriod
from raphson_mp.decorators import route

bp = Blueprint('stats', __name__, url_prefix='/stats')


@route(bp, '', redirect_to_login=True)
def route_stats(_conn: Connection, _user: User):
    return render_template('stats.jinja2')


@route(bp, '/data')
def route_stats_data(_conn: Connection, _user: User):
    period = StatsPeriod.from_str(request.args['period'])
    data = charts.get_data(period)
    return jsonw.json_response(data)
