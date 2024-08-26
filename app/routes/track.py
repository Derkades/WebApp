import logging
from datetime import datetime, timezone

from flask import Blueprint, Response, abort, request

from app import auth, db, image, music, scanner, settings
from app.image import ImageFormat
from app.music import AudioType, Track
from app.jsonw import json_response

log = logging.getLogger('app.routes.track')
bp = Blueprint('track', __name__, url_prefix='/track')


@bp.route('/choose', methods=['POST'])
def route_track():
    """
    Choose random track from the provided playlist directory.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        dir_name = request.json['playlist']
        playlist = music.playlist(conn, dir_name)
        require_metadata = request.json['require_metadata'] if 'require_metadata' in request.json else False
        if 'tag_mode' in request.args: # TODO move tags from args to json body
            tag_mode = request.json['tag_mode']
            assert tag_mode in {'allow', 'deny'}
            tags = request.json['tags'].split(';')
            chosen_track = playlist.choose_track(user, require_metadata=require_metadata, tag_mode=tag_mode, tags=tags)
        else:
            chosen_track = playlist.choose_track(user, require_metadata=require_metadata)

        if chosen_track is None:
            return Response('no track found', 404, content_type='text/plain')

        return chosen_track.info_dict()


@bp.route('/info')
def route_info():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, request.args['path'])
        return track.info_dict()


@bp.route('/audio')
def route_audio():
    """
    Get transcoded audio for the given track path.
    """
    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            path = request.args['path']
            music_data, = conn.execute('SELECT music_data FROM content WHERE path=?',
                                       (path,))
            return Response(music_data, content_type='audio/webm')

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, request.args['path'])

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


@bp.route('/album_cover')
def route_album_cover() -> Response:
    """
    Get album cover image for the provided track path.
    """
    # TODO Album title and album artist as parameters, instead of track path

    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            path = request.args['path']
            cover_data, = conn.execute('SELECT cover_data FROM content WHERE path=?',
                                       (path,))
            return Response(cover_data, content_type='image/webp')

    meme = 'meme' in request.args and bool(int(request.args['meme']))

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, request.args['path'])

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
    return response


@bp.route('/lyrics')
def route_lyrics():
    """
    Get lyrics for the provided track path.
    """
    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            path = request.args['path']
            lyrics_json, = conn.execute('SELECT lyrics_json FROM content WHERE path=?',
                                        (path,))
            return Response(lyrics_json, content_type='application/json')

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        track = Track.by_relpath(conn, request.args['path'])
        meta = track.metadata()

    if meta.lyrics:
        log.info('using lyrics from metadata')
        return {'found': True,
                'source': None,
                'html': meta.lyrics.replace('\n', '<br>')}

    from app import genius

    lyrics = genius.get_lyrics(meta.lyrics_search_query())
    if lyrics is None:
        return {'found': False}

    return {
        'found': True,
        'source': lyrics.source_url,
        'html': lyrics.lyrics_html,
    }


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
        result = conn.execute('SELECT path FROM track_fts WHERE track_fts MATCH ? ORDER BY rank LIMIT 20', (query,))
        tracks = [Track.by_relpath(conn, row[0]) for row in result]
        return {'tracks': [track.info_dict() for track in tracks]}


@bp.route('/tags')
def route_tags():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        # TODO make case insensitive, or is it already?
        result = conn.execute('SELECT DISTINCT tag FROM track_tag ORDER BY tag');
        tags = [row[0] for row in result]

    return tags


@bp.route('/update_metadata', methods=['POST'])
def route_update_metadata():
    """
    Endpoint to update track metadata
    """
    payload = request.json
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(payload['csrf'])

        track = Track.by_relpath(conn, payload['path'])
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
        scanner.scan_tracks(conn, track.playlist)

    return Response(None, 200)
