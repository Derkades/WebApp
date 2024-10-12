from flask import Blueprint, render_template, request

from raphson_mp import auth, charts, db, jsonw
from raphson_mp.charts import StatsPeriod

bp = Blueprint('stats', __name__, url_prefix='/stats')


@bp.route('')
def route_stats():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

    return render_template('stats.jinja2')


@bp.route('/data')
def route_stats_data():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        period = StatsPeriod.from_str(request.args['period'])

    data = charts.get_data(period)
    return jsonw.json_response(data)
