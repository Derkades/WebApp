import logging
import subprocess
import time
from tempfile import NamedTemporaryFile

from flask import Blueprint, Response, abort, request, send_file
from flask.typing import TemplateContextProcessorCallable

from raphson_mp import (acoustid, auth, db, image, jsonw, lyrics, music,
                        musicbrainz, scanner, settings)
from raphson_mp.image import ImageFormat
from raphson_mp.lyrics import TimeSyncedLyrics
from raphson_mp.music import AudioType, Track

log = logging.getLogger(__name__)
bp = Blueprint('track', __name__, url_prefix='/track')


@bp.route('/<path:path>/info')
def route_info(path: str):
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, path)
        if track is None:
            abort(404, 'track not found')
        return track.info_dict()


@bp.route('/<path:path>/video')
def route_raw(path: str):
    """
    Return video stream
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, path)
        if track is None:
            abort(404, 'track not found')

        meta = track.metadata()

        if meta.video == 'vp9':
            output_format = 'webm'
            output_media_type = 'video/webm'
        elif meta.video == 'h264':
            output_format = 'mp4'
            output_media_type = 'video/mp4'
        else:
            abort(400, 'file has no suitable video stream')

        with NamedTemporaryFile() as tempfile:
            subprocess.check_call(['ffmpeg', *settings.ffmpeg_flags(), '-y', '-i', track.path.as_posix(), '-c:v', 'copy', '-map', '0:v', '-f', output_format, tempfile.name], shell=False)
            return send_file(tempfile.name, mimetype=output_media_type)


@bp.route('/<path:path>/audio')
def route_audio(path: str):
    """
    Get transcoded audio for the given track path.
    """
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
def route_album_cover(path: str) -> Response:
    """
    Get album cover image for the provided track path.
    """
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


@bp.route('/<path:path>/lyrics')
def route_lyrics(path: str):
    """
    Get lyrics for the provided track path.
    Legacy lyrics endpoint for compatibility, re-implemented using new lyrics system
    DEPRECATED
    """
    # TODO remove this endpoint
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        track = Track.by_relpath(conn, path)
        lyr = track.lyrics()
        if lyr is None:
            return {'lyrics': None}
        elif isinstance(lyr, TimeSyncedLyrics):
            lyr = lyr.to_plain()

        return {'lyrics': lyr.text,
                'source_url': lyr.source}


@bp.route('/<path:path>/lyrics2')
def route_lyrics2(path: str):
    """
    Get lyrics for the provided track path.
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        track = Track.by_relpath(conn, path)

        if track is None:
            return abort(404, 'track not found')

        if request.if_modified_since and track.mtime_dt <= request.if_modified_since:
            return Response(None, 304)

        lyr = track.lyrics()

        return jsonw.json_response(lyrics.to_dict(lyr), last_modified=track.mtime)


@bp.route('/<path:path>/update_metadata', methods=['POST'])
def route_update_metadata(path: str):
    """
    Endpoint to update track metadata
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        track = Track.by_relpath(conn, path)
        assert track is not None

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
    track.write_metadata(meta)

    with db.connect() as conn:
        scanner.scan_track(conn, track.playlist, track.path, track.relpath)

    return Response(None, 200)


@bp.route('/<path:relpath>/acoustid', methods=['GET'])
def route_acoustid(relpath: str):
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, relpath)
        if track is None:
            abort(404, 'track not found')
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

@bp.route('/filter')
def route_filter():
    from raphson_mp.routes.tracks import route_filter as compat
    return compat()


@bp.route('/search')
def route_search():
    from raphson_mp.routes.tracks import route_search as compat
    return compat()


@bp.route('/tags')
def route_tags():
    from raphson_mp.routes.tracks import route_tags as compat
    return compat()
