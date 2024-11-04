from flask import Blueprint, Response, abort, request

from raphson_mp import auth, db, image, jsonw, lyrics, settings
from raphson_mp.image import ImageFormat
from raphson_mp.lyrics import PlainLyrics
from raphson_mp.music import Track

bp = Blueprint('track', __name__, url_prefix='/track')

@bp.route('/<path:path>/info')
def route_info(path: str):
    with db.connect(read_only=True) as conn:
        track = Track.by_relpath(conn, path)
        if track is None:
            abort(404, 'track not found')
        return track.info_dict()


@bp.route('/<path:path>/audio')
def route_audio(path: str):
    with db.offline(read_only=True) as conn:
        music_data: bytes = conn.execute('SELECT music_data FROM content WHERE path=?', (path,)).fetchone()[0]
        return Response(music_data, content_type='audio/webm')


@bp.route('/<path:path>/cover')
def route_album_cover(path: str) -> Response:
    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            cover_data: bytes = conn.execute('SELECT cover_data FROM content WHERE path=?', (path,)).fetchone()[0]
            return Response(cover_data, content_type='image/webp')

    meme = 'meme' in request.args and bool(int(request.args['meme']))

    if request.args['quality'] == 'high':
        quality = image.QUALITY_HIGH
    elif request.args['quality'] == 'low':
        quality = image.QUALITY_LOW
    else:
        raise ValueError('invalid quality')

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, path)
        if track is None:
            abort(404, 'track not found')

        last_modified = track.mtime_dt
        if request.if_modified_since and last_modified <= request.if_modified_since:
            return Response(None, 304)

        image_bytes = track.get_cover(meme, quality, ImageFormat.WEBP)

    response = Response(image_bytes, content_type='image/webp')
    response.last_modified = last_modified
    response.cache_control.no_cache = True  # always revalidate cache
    return response


@bp.route('/<path:path>/lyrics2')
def route_lyrics2(path: str):
    """
    Get lyrics for the provided track path.
    """
    with db.offline(read_only=True) as conn:
        lyrics_json_str: str = conn.execute('SELECT lyrics_json FROM content WHERE path=?', (path,)).fetchone()[0]
        lyrics_json = jsonw.from_json(lyrics_json_str)
        if 'found' in lyrics_json and lyrics_json['found']:
            # Legacy HTML lyrics, best effort conversion from HTML to plain text
            import html
            lyr = PlainLyrics(lyrics_json['source'], html.unescape(lyrics_json['html'].replace('<br>', '\n')))
        elif 'lyrics' in lyrics_json and 'source_url' in lyrics_json and lyrics_json['lyrics'] is not None and lyrics_json['source_url'] is not None:
            # Legacy plaintext lyrics
            lyr = PlainLyrics(lyrics_json['source_url'], lyrics_json['lyrics'])
        elif 'type' in lyrics_json:
            # Modern lyrics
            lyr = lyrics.from_dict(lyrics_json)
        else:
            lyr = None
        return lyrics.to_dict(lyr)
