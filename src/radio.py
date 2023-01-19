from dataclasses import dataclass
import logging
from datetime import datetime
from sqlite3 import Connection
import random

import db
from music import Track
import music
from metadata import Metadata
import settings


log = logging.getLogger('app.radio')


@dataclass
class RadioTrack:
    track: Track
    meta: Metadata
    start_time: int
    duration: int


def _choose_track(conn: Connection, previous_playlist = None) -> Track:
    playlist_candidates = [p for p in settings.radio_playlists if p != previous_playlist]
    playlist_name = random.choice(playlist_candidates)

    playlist = music.playlist(conn, playlist_name)
    track = playlist.choose_track(None, None)
    return track


def get_current_track(conn: Connection) -> RadioTrack:
    current_time = int(datetime.utcnow().timestamp() * 1000)

    last_track_info = conn.execute('''
                                    SELECT track.path, radio_track.start_time, track.duration
                                    FROM radio_track JOIN track ON radio_track.track = track.path
                                    WHERE start_time <= ? AND start_time + duration*1000 > ?
                                    ORDER BY start_time ASC
                                    LIMIT 1
                                    ''',
                                    (current_time, current_time)).fetchone()

    # Normally when the radio is being actively listened to, a track will
    # have already been chosen. If this not the case, choose a track and
    # start it at a random point in time, to make it feel to the user
    # like the radio was playing continuously.

    if last_track_info is None:
        log.info('No current song, choose track starting at random time')
        current_time = int(datetime.utcnow().timestamp() * 1000)
        track = _choose_track(conn)
        meta = track.metadata()
        start_time = current_time - int((meta.duration * 1000) * random.random())
        conn.execute('INSERT INTO radio_track (track, start_time) VALUES (?, ?)',
                        (track.relpath, start_time))
        return RadioTrack(track, meta, start_time, meta.duration)

    (track_path, start_time, duration) = last_track_info

    log.info('Return current track')

    # Return current song from database
    track = Track.by_relpath(conn, track_path)
    meta = track.metadata()
    return RadioTrack(track, meta, start_time, duration)


def get_next_track(conn: Connection) -> RadioTrack:
    current_time = int(datetime.utcnow().timestamp() * 1000)

    current_track_info = conn.execute('''
                                        SELECT radio_track.start_time + track.duration*1000 AS end_time, track.playlist
                                        FROM radio_track JOIN track ON radio_track.track = track.path
                                        WHERE radio_track.start_time < ? AND end_time > ?
                                        ORDER BY radio_track.start_time ASC
                                        LIMIT 1
                                        ''',
                                        (current_time, current_time)).fetchone()

    next_track_info = conn.execute('''
                                    SELECT track.path, radio_track.start_time, track.duration
                                    FROM radio_track JOIN track ON radio_track.track = track.path
                                    WHERE radio_track.start_time >= ?
                                    ORDER BY radio_track.start_time ASC
                                    LIMIT 1
                                    ''',
                                    (current_time,)).fetchone()

    if next_track_info is None:
        log.info('Choose next track')

        if current_track_info is None:
            raise ValueError('Cannot choose next track when current track has not been chosen')

        (current_track_end_time, current_track_playlist) = current_track_info

        # Choose next track starting right after current track
        track = _choose_track(conn, previous_playlist=current_track_playlist)
        meta = track.metadata()
        conn.execute('INSERT INTO radio_track (track, start_time) VALUES (?, ?)',
                        (track.relpath, current_track_end_time))
        return RadioTrack(track, meta, current_track_end_time, meta.duration)

    log.info('Returning already chosen next track')
    (track_path, start_time, duration) = next_track_info
    track = Track.by_relpath(conn, track_path)
    return RadioTrack(track, track.metadata(), start_time, duration)
