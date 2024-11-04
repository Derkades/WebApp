
import logging

from flask import Blueprint, Response, request

from raphson_mp import auth, db, scanner
from raphson_mp.jsonw import json_response
from raphson_mp.music import Track

log = logging.getLogger(__name__)
bp = Blueprint('tracks', __name__, url_prefix='/tracks')


@bp.route('/filter')
def route_filter():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        last_modified = scanner.last_change(conn, request.args['playlist'] if 'playlist' in request.args else None)

        if request.if_modified_since and last_modified <= request.if_modified_since:
            return Response(None, 304)  # Not Modified

        query = 'SELECT path FROM track WHERE true'
        params: list[str] = []
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
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        query = query.replace('"', '""')
        query = '"' + query.replace(' ', '" OR "') + '"'
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
        result = conn.execute('SELECT DISTINCT tag FROM track_tag ORDER BY tag')
        tags = [row[0] for row in result]

    return tags
