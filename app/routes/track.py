import logging
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, Response, abort, request

from app import auth, db, image, jsonw, music, scanner, settings
from app.image import ImageFormat
from app.metadata import sort_artists
from app.music import AudioType, Track

log = logging.getLogger('app.routes.track')
bp = Blueprint('track', __name__, url_prefix='/track')


def track_info_dict(track: Track):
    meta = track.metadata()
    return {
        'playlist': track.playlist,
        'path': track.relpath,
        'mtime': track.mtime,
        'duration': meta.duration,
        'title': meta.title,
        'album': meta.album,
        'album_artist': meta.album_artist,
        'year': meta.year,
        'artists': meta.artists,
        'tags': meta.tags,
    }


@bp.route('/choose', methods=['POST'])
def route_track():
    """
    Choose random track from the provided playlist directory.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        dir_name = request.json['playlist_dir']
        playlist = music.playlist(conn, dir_name)
        if 'tag_mode' in request.args:
            tag_mode = request.json['tag_mode']
            assert tag_mode in {'allow', 'deny'}
            tags = request.json['tags'].split(';')
            chosen_track = playlist.choose_track(user, tag_mode=tag_mode, tags=tags)
        else:
            chosen_track = playlist.choose_track(user)

        return track_info_dict(chosen_track)


@bp.route('/info')
def route_info():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, request.args['path'])
        return track_info_dict(track)


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

    parsed_mtime = datetime.fromtimestamp(track.mtime, timezone.utc)
    if request.if_modified_since and parsed_mtime <= request.if_modified_since:
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
    response.last_modified = parsed_mtime
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

        quality_str = request.args['quality']
        if quality_str == 'high':
            quality = image.QUALITY_HIGH
        elif quality_str == 'low':
            quality = image.QUALITY_LOW
        else:
            raise ValueError('invalid quality')

        image_bytes = track.get_cover(meme, quality, ImageFormat.WEBP)

    return Response(image_bytes, content_type='image/webp')


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


@bp.route('/list')
def route_list():
    """Return list of playlists and tracks"""
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)

        timestamp_row = conn.execute('''
                                     SELECT timestamp FROM scanner_log
                                     ORDER BY id DESC
                                     LIMIT 1
                                     ''').fetchone()
        if timestamp_row:
            last_modified = datetime.fromtimestamp(timestamp_row[0], timezone.utc)
        else:
            last_modified = datetime.now(timezone.utc)

        if request.if_modified_since and last_modified <= request.if_modified_since:
            log.info('Last modified before If-Modified-Since header')
            return Response(None, 304)  # Not Modified

        user_playlists = music.user_playlists(conn, user.user_id, all_writable=user.admin)

        playlist_response: list[dict[str, Any]] = []

        for playlist in user_playlists:
            if playlist.track_count == 0:
                continue

            playlist_json = {
                'name': playlist.name,
                'track_count': playlist.track_count,
                'favorite': playlist.favorite,
                'write': playlist.write,
                'tracks': [],
            }
            playlist_response.append(playlist_json)

            track_rows = conn.execute('''
                                      SELECT path, mtime, duration, title, album, album_artist, year
                                      FROM track
                                      WHERE playlist=?
                                      ''', (playlist.name,)).fetchall()

            for relpath, mtime, duration, title, album, album_artist, year in track_rows:
                track_json = {
                    'path': relpath,
                    'mtime': mtime,
                    'duration': duration,
                    'title': title,
                    'album': album,
                    'album_artist': album_artist,
                    'year': year,
                    'artists': None,
                    'tags': [],
                }
                playlist_json['tracks'].append(track_json)

                artist_rows = conn.execute('SELECT artist FROM track_artist WHERE track=?',
                                           (relpath,)).fetchall()
                if artist_rows:
                    track_json['artists'] = sort_artists([row[0] for row in artist_rows], album_artist)

                tag_rows = conn.execute('SELECT tag FROM track_tag WHERE track=?', (relpath,))
                track_json['tags'] = [tag for tag, in tag_rows]

    return jsonw.json_response({'playlists': playlist_response}, last_modified=last_modified)


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

    meta.title = payload['metadata']['title']
    meta.album = payload['metadata']['album']
    meta.artists = payload['metadata']['artists']
    meta.album_artist = payload['metadata']['album_artist']
    meta.tags = payload['metadata']['tags']
    meta.year = payload['metadata']['year']
    track.write_metadata(meta)

    with db.connect() as conn:
        scanner.scan_tracks(conn, track.playlist)

    return Response(None, 200)
