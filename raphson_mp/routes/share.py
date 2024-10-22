import os
import time
from base64 import b32encode

from flask import (Blueprint, Response, abort, render_template, request,
                   send_file)

from raphson_mp import auth, db, jsonw
from raphson_mp.image import QUALITY_HIGH, ImageFormat
from raphson_mp.lyrics import PlainLyrics, TimeSyncedLyrics
from raphson_mp.music import AudioType, Track

bp = Blueprint('share', __name__, url_prefix='/share')


def gen_share_code() -> str:
    """
    Generate new random share code
    """
    return b32encode(os.urandom(8)).decode().lower().rstrip('=')


def track_by_code(conn, code: str) -> Track:
    """
    Find track using a provided share code
    """
    row = conn.execute('SELECT track FROM shares WHERE share_code=?',
                           (code,)).fetchone()
    if row is None:
        abort(404, 'No share was found with the given code')

    return Track.by_relpath(conn, row[0])


@bp.route('/create', methods=["POST"])
def create():
    """
    Endpoint to create a share link, called from web music player.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        track = Track.by_relpath(conn, request.json['track'])
        if track is None:
            abort(400, 'track does not exist')

        code = gen_share_code()

        conn.execute('INSERT INTO shares (share_code, user, track, create_timestamp) VALUES (?, ?, ?, ?)',
                     (code, user.user_id, track.relpath, int(time.time())))

        return jsonw.json_response({'code': code})


@bp.route('/<code>/cover')
def cover(code):
    """
    Route providing a WEBP album cover image
    """
    with db.connect(read_only=True) as conn:
        track = track_by_code(conn, code)
        cover_bytes = track.get_cover(meme=False, img_quality=QUALITY_HIGH, img_format=ImageFormat.WEBP)

    return Response(cover_bytes, content_type='image/webp')


@bp.route('/<code>/audio')
def audio(code):
    """
    Route to stream opus audio.
    """
    with db.connect(read_only=True) as conn:
        track = track_by_code(conn, code)
        audio_bytes = track.transcoded_audio(AudioType.WEBM_OPUS_HIGH)

    return Response(audio_bytes, content_type='audio/webm')


@bp.route('/<code>/download/<file_format>')
def download(code, file_format):
    """
    Route to download an audio file.
    """
    with db.connect(read_only=True) as conn:
        track = track_by_code(conn, code)

        if file_format == 'original':
            response = send_file(track.path)
            response.headers['Content-Disposition'] = f'attachment; filename="{track.path.name}"'
        elif file_format == 'mp3':
            audio_bytes = track.transcoded_audio(AudioType.MP3_WITH_METADATA)
            response = Response(audio_bytes, content_type='audio/mp3')
            download_name = track.metadata().download_name() + '.mp3'
            response.headers['Content-Disposition'] = f'attachment; filename="{download_name}"'
        else:
            abort(400, 'Invalid format')

    return response


@bp.route('/<code>')
def show(code):
    """
    Web page displaying a shared track.
    """
    with db.connect(read_only=True) as conn:
        track = track_by_code(conn, code)

        shared_by, = conn.execute('''
                                  SELECT username
                                  FROM shares JOIN user ON shares.user = user.id
                                  WHERE share_code=?
                                  ''', (code,)).fetchone()

        lyrics = track.lyrics()
        meta = track.metadata()

        if lyrics is None:
            lyrics_text = None
        elif isinstance(lyrics, PlainLyrics):
            lyrics_text = lyrics.text
        elif isinstance(lyrics, TimeSyncedLyrics):
            lyrics_text = lyrics.to_plain().text
        else:
            raise ValueError(lyrics)

    return render_template('share.jinja2',
                           code=code,
                           shared_by=shared_by,
                           track=meta.display_title(),
                           lyrics=lyrics_text)
