from dataclasses import dataclass
from importlib.metadata import metadata
import logging
from datetime import datetime
from sqlite3 import Connection
import random

import db
from music import Track
from metadata import Metadata
import settings


log = logging.getLogger('app.radio')


@dataclass
class RadioTrack:
    track: Track
    meta: Metadata
    start_time: int
    duration: int


def _choose_track(conn: Connection) -> Track:
    # Select 20 random tracks, then choose track that was played longest ago
    query = """
            SELECT * FROM (
                SELECT track.path, last_played
                FROM track
                INNER JOIN track_persistent ON track.path = track_persistent.path
                [where_replaced_later]
                ORDER BY RANDOM()
                LIMIT 20
            ) ORDER BY last_played ASC LIMIT 1
            """

    if len(settings.radio_playlists) == 0:
        where = ''
        params = []
        log.warning('Radio playlists not configured, choosing from all playlists')
    else:
        where = 'WHERE track.playlist IN (' + ','.join(['?'] * len(settings.radio_playlists)) + ')'
        params = settings.radio_playlists
    query = query.replace('[where_replaced_later]', where)

    track, last_played = conn.execute(query, params).fetchone()

    current_timestamp = int(datetime.now().timestamp())
    if last_played == 0:
        log.info('Chosen track: %s (never played)', track)
    else:
        hours_ago = (current_timestamp - last_played) / 3600
        log.info('Chosen track: %s (last played %.2f hours ago)', track, hours_ago)

    conn.execute('UPDATE track_persistent SET last_played = ? WHERE path=?', (current_timestamp, track))

    return Track.by_relpath(track)


def _choose_new_track(conn: Connection):
    """
    Choose new track starting at random point in time
    """
    current_time = int(datetime.now().timestamp())
    track = _choose_track(conn)
    meta = track.metadata()
    start_time = int(current_time - (meta.duration - meta.duration / 4) * random.random())
    conn.execute('INSERT INTO radio_tracks (track_path, start_time, duration) VALUES (?, ?, ?)',
                    (track.relpath, start_time, meta.duration))
    return RadioTrack(track, meta, start_time, meta.duration)


def get_current_track() -> RadioTrack:
    with db.music() as conn:
        current_time = int(datetime.now().timestamp())

        last_track_info = conn.execute('''
                                       SELECT track_path, start_time, duration
                                       FROM radio_tracks
                                       WHERE start_time <= ? AND start_time + duration > ?
                                       ORDER BY start_time ASC
                                       LIMIT 1
                                       ''',
                                       (current_time, current_time)).fetchone()

        # Normally when the radio is being actively listened to, a track will
        # have already been chosen. If this not the case, choose a track and
        # start it at a random point in time, to make it feel to the user
        # like the radio was playing continously.

        if last_track_info is None:
            log.info('No current song, choose track starting at random time')
            return _choose_new_track(conn)

        (track_path, start_time, duration) = last_track_info

        log.info('Return current track')

        # Return current song from database
        track = Track.by_relpath(track_path)
        meta = track.metadata()
        return RadioTrack(track, meta, start_time, duration)


def get_next_track() -> RadioTrack:
    with db.music() as conn:
        current_time = int(datetime.now().timestamp())

        current_track_info = conn.execute('''
                                          SELECT start_time + duration AS end_time
                                          FROM radio_tracks
                                          WHERE start_time < ? AND end_time > ?
                                          ORDER BY start_time ASC
                                          LIMIT 1
                                          ''',
                                          (current_time, current_time)).fetchone()

        next_track_info = conn.execute('''
                                       SELECT track_path, start_time, duration
                                       FROM radio_tracks
                                       WHERE start_time >= ?
                                       ORDER BY start_time ASC
                                       LIMIT 1
                                       ''',
                                       (current_time,)).fetchone()

        if next_track_info is None:
            log.info('Choose next track')

            if current_track_info is None:
                raise ValueError('Cannot choose next track when current track has not been chosen')

            (current_track_end_time,) = current_track_info

            # Choose next track starting right after current track
            track = _choose_track(conn)
            meta = track.metadata()
            conn.execute('INSERT INTO radio_tracks (track_path, start_time, duration) VALUES (?, ?, ?)',
                            (track.relpath, current_track_end_time, meta.duration))
            return RadioTrack(track, meta, current_track_end_time, meta.duration)

        log.info('Returning already chosen next track')
        (track_path, start_time, duration) = next_track_info
        track = Track.by_relpath(track_path)
        return RadioTrack(track, track.metadata(), start_time, duration)
