import shutil
import subprocess
import tempfile

import requests
from flask import Blueprint, Response, abort, request

from raphson_mp import settings

bp = Blueprint('news', __name__, url_prefix='/news')


@bp.route('/audio')
def audio():
    with tempfile.NamedTemporaryFile() as temp_input, tempfile.NamedTemporaryFile() as temp_output:

        # Download wave audio to temp file
        with requests.get(settings.news_server + '/news.wav', timeout=10, stream=True) as response:
            # News is only kept in temporary storage, if the news service has just
            # started it won't have news cached yet.
            if response.status_code == 503:
                abort(503)

            response.raise_for_status()
            shutil.copyfileobj(response.raw, temp_input)

        # Transcode wave PCM audio to opus
        command = ['ffmpeg',
                   '-y',  # overwriting file is required, because the created temp file already exists
                   '-hide_banner',
                   '-nostats',
                   '-loglevel', settings.ffmpeg_log_level,
                   '-i', temp_input.name,
                   '-f', 'webm',
                   '-c:a', 'libopus',
                   '-b:a', '64k',
                   '-vbr', 'on',
                   '-filter:a', settings.loudnorm_filter,
                   temp_output.name]

        subprocess.check_call(command, shell=False)
        audio_bytes = temp_output.read()

    return Response(audio_bytes, mimetype='audio/webm')
