from flask import Blueprint, Response, request

from app import news

bp = Blueprint('news', __name__, url_prefix='/news')


@bp.route('/audio')
def audio():
    provider = request.args['provider']
    audio_bytes = news.get_audio(provider)
    return Response(audio_bytes, mimetype='audio/webm')
