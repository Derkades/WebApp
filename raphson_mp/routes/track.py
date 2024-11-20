import logging
from pathlib import Path
from sqlite3 import Connection
import subprocess
import time
from tempfile import NamedTemporaryFile

from flask import Blueprint, Response, abort, request, send_file

from raphson_mp import (acoustid, cache, db, image, jsonw, lyrics, music,
                        musicbrainz, scanner, settings)
from raphson_mp.auth import User
from raphson_mp.decorators import route
from raphson_mp.image import ImageFormat
from raphson_mp.lyrics import PlainLyrics, TimeSyncedLyrics
from raphson_mp.music import AudioType, Track

log = logging.getLogger(__name__)
bp = Blueprint('track', __name__, url_prefix='/track')

def _track(conn: Connection, relpath: str) -> Track:
    track = Track.by_relpath(conn, relpath)
    if track is None:
        abort(404, 'track not found')
    return track


@route(bp, '/<path:relpath>/info')
def route_info(conn: Connection, _user: User, relpath: str):
    track = _track(conn, relpath)
    return track.info_dict()


@route(bp, '/<path:relpath>/video')
def route_raw(conn: Connection, _user: User, relpath: str):
    """
    Return video stream
    """
    track = _track(conn, relpath)
    meta = track.metadata()

    if meta.video == 'vp9':
        output_format = 'webm'
        output_media_type = 'video/webm'
    elif meta.video == 'h264':
        output_format = 'mp4'
        output_media_type = 'video/mp4'
    else:
        abort(400, 'file has no suitable video stream')

    cache_key: str = f'video{track.relpath}{track.mtime}'

    response = cache.retrieve_response(cache_key, output_media_type)

    if not response:
        with NamedTemporaryFile() as tempfile:
            subprocess.check_call(['ffmpeg', *settings.ffmpeg_flags(), '-y', '-i', track.path.as_posix(), '-c:v', 'copy', '-map', '0:v', '-f', output_format, tempfile.name], shell=False)
            cache.store(cache_key, Path(tempfile.name), cache.MONTH)
        response = cache.retrieve_response(cache_key, output_media_type)
        if not response:
            raise ValueError()

    return response


@route(bp, '/<path:relpath>/audio')
def route_audio(conn: Connection, _user: User, relpath: str):
    """
    Get transcoded audio for the given track path.
    """
    track = _track(conn, relpath)

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


@route(bp, '/<path:relpath>/cover')
def route_album_cover(conn: Connection, _user: User, relpath: str) -> Response:
    """
    Get album cover image for the provided track path.
    """
    track = _track(conn, relpath)

    meme = 'meme' in request.args and bool(int(request.args['meme']))

    if request.args['quality'] == 'high':
        quality = image.QUALITY_HIGH
    elif request.args['quality'] == 'low':
        quality = image.QUALITY_LOW
    else:
        raise ValueError('invalid quality')

    last_modified = track.mtime_dt
    if request.if_modified_since and last_modified <= request.if_modified_since:
        return Response(None, 304)

    image_bytes = track.get_cover(meme, quality, ImageFormat.WEBP)

    response = Response(image_bytes, content_type='image/webp')
    response.last_modified = last_modified
    response.cache_control.no_cache = True  # always revalidate cache
    return response


# TODO remove lyrics2 when offline mode clients have had time to update
@route(bp, ['/<path:path>/lyrics', '/<path:path>/lyrics2'])
def route_lyrics(conn: Connection, _user: User, path: str):
    """
    Get lyrics for the provided track path.
    """
    track = _track(conn, path)

    if request.if_modified_since and track.mtime_dt <= request.if_modified_since:
        return Response(None, 304)

    lyr = track.lyrics()

    if 'type' in request.args:
        if request.args['type'] == 'plain' and isinstance(lyr, TimeSyncedLyrics):
            lyr = lyr.to_plain()
        elif request.args['type'] == 'synced' and isinstance(lyr, PlainLyrics):
            lyr = None

    return jsonw.json_response(lyrics.to_dict(lyr), last_modified=track.mtime)


@route(bp, '/<path:relpath>/update_metadata', methods=['POST'])
def route_update_metadata(conn: Connection, user: User, relpath: str):
    """
    Endpoint to update track metadata
    """
    track = _track(conn, relpath)

    playlist = music.playlist(conn, track.playlist)
    if not playlist.has_write_permission(user):
        return Response('No write permission for this playlist', 403, content_type='text/plain')

    meta = track.metadata()

    meta.title = request.json['title']
    meta.album = request.json['album']
    meta.artists = request.json['artists']
    meta.album_artist = request.json['album_artist']
    meta.tags = request.json['tags']
    meta.year = request.json['year']

    with db.connect() as writable_conn:
        track.conn = writable_conn
        track.write_metadata(meta)
        scanner.scan_track(writable_conn, track.playlist, track.path, track.relpath)

    return Response(None, 200)


@route(bp, '/<path:relpath>/acoustid', methods=['GET'])
def route_acoustid(conn: Connection, _user: User, relpath: str):
    track = _track(conn, relpath)
    fp = acoustid.get_fingerprint(track.path)
    known_ids: set[str] = set()
    meta_list: list[musicbrainz.MBMeta] = []
    for recording in acoustid.lookup(fp):
        log.info('found recording: %s', recording)
        for meta in musicbrainz.get_recording_metadata(recording):
            if meta.id in known_ids:
                continue
            log.info('found possible metadata: %s', meta)
            meta_list.append(meta)
            known_ids.add(meta.id)

        if len(meta_list) > 0:
            break

        time.sleep(2) # crude way of avoiding rate limits

    return meta_list


# TODO remove legacy compatibility endpoints when clients (especially offline sync) have had time to update.

@bp.route('/filter')  # pyright: ignore[reportArgumentType]
def route_filter():
    from raphson_mp.routes.tracks import route_filter as compat
    return compat()


@bp.route('/search')  # pyright: ignore[reportArgumentType]
def route_search():
    from raphson_mp.routes.tracks import route_search as compat
    return compat()


@bp.route('/tags')  # pyright: ignore[reportArgumentType]
def route_tags():
    from raphson_mp.routes.tracks import route_tags as compat
    return compat()
