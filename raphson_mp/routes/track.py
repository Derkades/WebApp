import logging

from flask import Blueprint, Response, abort, request

from raphson_mp import auth, db, image, music, scanner, settings
from raphson_mp.image import ImageFormat
from raphson_mp.jsonw import json_response
from raphson_mp.music import AudioType, Track

log = logging.getLogger(__name__)
bp = Blueprint('track', __name__, url_prefix='/track')


@bp.route('/<path:path>/info')
def route_info(path):
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, path)
        return track.info_dict()


@bp.route('/<path:path>/audio')
def route_audio(path):
    """
    Get transcoded audio for the given track path.
    """
    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            music_data, = conn.execute('SELECT music_data FROM content WHERE path=?',
                                       (path,))
            return Response(music_data, content_type='audio/webm')

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, path)

    if track is None:
        abort(404, 'Track does not exist')

    last_modified = track.mtime_dt
    if request.if_modified_since and last_modified <= request.if_modified_since:
        return Response(None, 304)

    type_str = request.args['type']
    if type_str == 'webm_opus_high':
        audio_type = AudioType.WEBM_OPUS_HIGH
        media_type = 'audio/webm'
    elif type_str == 'webm_opus_low':
        audio_type = AudioType.WEBM_OPUS_LOW
        media_type = 'audio/webm'
    elif type_str == 'mp4_aac':
        audio_type = AudioType.MP4_AAC
        media_type = 'audio/mp4'
    elif type_str == 'mp3_with_metadata':
        audio_type = AudioType.MP3_WITH_METADATA
        media_type = 'audio/mp3'
    else:
        raise ValueError(type_str)

    audio = track.transcoded_audio(audio_type)
    response = Response(audio, content_type=media_type)
    response.last_modified = last_modified
    response.cache_control.no_cache = True  # always revalidate cache
    response.accept_ranges = 'bytes'  # Workaround for Chromium bug https://stackoverflow.com/a/65804889
    if audio_type == AudioType.MP3_WITH_METADATA:
        mp3_name = track.metadata().filename_title()
        response.headers['Content-Disposition'] = f'attachment; filename="{mp3_name}"'
    return response


@bp.route('/<path:path>/cover')
def route_album_cover(path) -> Response:
    """
    Get album cover image for the provided track path.
    """
    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            cover_data, = conn.execute('SELECT cover_data FROM content WHERE path=?', (path,))
            return Response(cover_data, content_type='image/webp')

    meme = 'meme' in request.args and bool(int(request.args['meme']))

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, path)

        last_modified = track.mtime_dt
        if request.if_modified_since and last_modified <= request.if_modified_since:
            return Response(None, 304)

        quality_str = request.args['quality']
        if quality_str == 'high':
            quality = image.QUALITY_HIGH
        elif quality_str == 'low':
            quality = image.QUALITY_LOW
        else:
            raise ValueError('invalid quality')

        image_bytes = track.get_cover(meme, quality, ImageFormat.WEBP)

    response = Response(image_bytes, content_type='image/webp')
    response.last_modified = last_modified
    response.cache_control.no_cache = True  # always revalidate cache
    return response


@bp.route('/<path:path>/lyrics')
def route_lyrics(path):
    """
    Get lyrics for the provided track path.
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        track = Track.by_relpath(conn, path)
        lyrics = track.lyrics()
        if lyrics:
            return {'lyrics': lyrics.lyrics,
                    'source_url': lyrics.source_url}
        else:
            return {'lyrics': False}


@bp.route('/<path:path>/update_metadata', methods=['POST'])
def route_update_metadata(path):
    """
    Endpoint to update track metadata
    """
    payload = request.json
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        track = Track.by_relpath(conn, path)
        assert track is not None

        playlist = music.playlist(conn, track.playlist)
        if not playlist.has_write_permission(user):
            return Response('No write permission for this playlist', 403, content_type='text/plain')

        meta = track.metadata()

    meta.title = payload['title']
    meta.album = payload['album']
    meta.artists = payload['artists']
    meta.album_artist = payload['album_artist']
    meta.tags = payload['tags']
    meta.year = payload['year']
    track.write_metadata(meta)

    with db.connect() as conn:
        scanner.scan_track(conn, track.playlist, track.path, track.relpath)

    return Response(None, 200)


@bp.route('/filter')
def route_filter():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        last_modified = scanner.last_change(conn, request.args['playlist'] if 'playlist' in request.args else None)

        if request.if_modified_since and last_modified <= request.if_modified_since:
            return Response(None, 304)  # Not Modified

        query = 'SELECT path FROM track WHERE true'
        params = []
        if 'playlist' in request.args:
            query += ' AND playlist = ?'
            params.append(request.args['playlist'])

        if 'artist' in request.args:
            query += ' AND EXISTS(SELECT artist FROM track_artist WHERE track = path AND artist = ?)'
            params.append(request.args['artist'])

        if 'album_artist' in request.args:
            query += ' AND album_artist = ?'
            params.append(request.args['album_artist'])

        if 'album' in request.args:
            query += ' AND album = ?'
            params.append(request.args['album'])

        if 'has_metadata' in request.args and request.args['has_metadata'] == '1':
            # Has at least metadata for: title, album, album artist, artists
            query += ' AND title NOT NULL AND album NOT NULL AND album_artist NOT NULL AND EXISTS(SELECT artist FROM track_artist WHERE track = path)'

        if 'tag' in request.args:
            query += ' AND EXISTS(SELECT tag FROM track_tag WHERE track = path AND tag = ?)'
            params.append(request.args['tag'])

        query += ' LIMIT 5000'
        result = conn.execute(query, params)
        tracks = [Track.by_relpath(conn, row[0]) for row in result]

        return json_response({'tracks': [track.info_dict() for track in tracks]}, last_modified=last_modified)


@bp.route('/search')
def route_search():
    query = request.args['query']
    # TODO ensure valid FTS syntax, perhaps remove non-alphanumeric characters?
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        query = query.replace('"', '""')
        query = '"' + query.replace(' ', '" "') + '"'
        log.info('search: %s', query)
        result = conn.execute('SELECT path FROM track_fts WHERE track_fts MATCH ? ORDER BY rank LIMIT 25', (query,))
        tracks = [Track.by_relpath(conn, row[0]) for row in result]
        albums = [{'album': row[0], 'artist': row[1]}
                  for row in conn.execute('SELECT DISTINCT album, album_artist FROM track_fts WHERE album MATCH ? ORDER BY rank LIMIT 10', (query,))]
        return {'tracks': [track.info_dict() for track in tracks], 'albums': albums}


@bp.route('/tags')
def route_tags():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        # TODO make case insensitive, or is it already?
        result = conn.execute('SELECT DISTINCT tag FROM track_tag ORDER BY tag');
        tags = [row[0] for row in result]

    return tags
