
import logging
from sqlite3 import Connection
from typing import cast

from flask import Blueprint, Response, request

from raphson_mp import db, scanner
from raphson_mp.auth import User
from raphson_mp.decorators import route
from raphson_mp.jsonw import json_response
from raphson_mp.music import Track

log = logging.getLogger(__name__)
bp = Blueprint('tracks', __name__, url_prefix='/tracks')


@route(bp, '/filter')
def route_filter(conn: Connection, _user: User):
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
    tracks = cast(list[Track], [Track.by_relpath(conn, row[0]) for row in result])

    return json_response({'tracks': [track.info_dict() for track in tracks]}, last_modified=last_modified)


@route(bp, '/search')
def route_search(conn: Connection, _user: User):
    query = request.args['query']
    query = query.replace('"', '""')
    query = '"' + query.replace(' ', '" OR "') + '"'
    log.info('search: %s', query)
    result = conn.execute('SELECT path FROM track_fts WHERE track_fts MATCH ? ORDER BY rank LIMIT 25', (query,))
    tracks = cast(list[Track], [Track.by_relpath(conn, row[0]) for row in result])
    albums = [{'album': row[0], 'artist': row[1]}
                for row in conn.execute('SELECT DISTINCT album, album_artist FROM track_fts WHERE album MATCH ? ORDER BY rank LIMIT 10', (query,))]
    return {'tracks': [track.info_dict() for track in tracks], 'albums': albums}


@route(bp, '/tags')
def route_tags(conn: Connection, _user: User):
    result = conn.execute('SELECT DISTINCT tag FROM track_tag ORDER BY tag')
    tags = [row[0] for row in result]
    return tags
