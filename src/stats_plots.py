from enum import Enum, unique
from collections import Counter
from datetime import datetime
import time

from flask_babel import _

import db
from music import Track


# Number of entries to display in a plot, for counters
COUNTER_AMOUNT = 10


@unique
class StatsPeriod(Enum):
    DAY = 24*60*60
    WEEK = 7*DAY
    MONTH = 30*DAY
    YEAR = 365*DAY

    def translated_str(self):
        if self == StatsPeriod.DAY:
            return _('last day')
        elif self == StatsPeriod.WEEK:
            return _('last week')
        elif self == StatsPeriod.MONTH:
            return _('last month')
        elif self == StatsPeriod.YEAR:
            return _('last year')

        raise ValueError()

    @staticmethod
    def from_str(period: str):
        if period == 'day':
            return StatsPeriod.DAY
        elif period == 'week':
            return StatsPeriod.WEEK
        elif period == 'month':
            return StatsPeriod.MONTH
        elif period == 'year':
            return StatsPeriod.YEAR

        raise ValueError()


def simple_bar_chart(title, categories, series_name, series_data, vertical):
    return {
        'title': title,
        'type': 'column' if vertical else 'bar',
        'data': {
            'categories': categories,
            'series': [
                {
                    'name': series_name,
                    'data': series_data,
                }
            ]
        }
    }


def rows_to_column_chart(rows: list[tuple[str, int]], title: str, series_name: str, vertical=False):
    return simple_bar_chart(title, [row[0] for row in rows], series_name, [row[1] for row in rows], vertical)


def counter_to_column_chart(counter: Counter, title: str, series_name: str, vertical=False):
    return rows_to_column_chart(counter.most_common(COUNTER_AMOUNT), title, series_name, vertical)


def chart_last_chosen(conn):
    result = conn.execute('SELECT last_played FROM track')
    counts = [0, 0, 0, 0, 0]
    current = int(time.time())
    for (timestamp,) in result:
        if timestamp == 0:
            counts[4] += 1  # never
        if timestamp > current - 60*60*24:
            counts[0] += 1 # today
        elif timestamp > current - 60*60*24*7:
            counts[1] += 1 # this week
        elif timestamp > current - 60*60*24*30:
            counts[2] += 1 # this month
        else:
            counts[3] += 1 # long ago

    return simple_bar_chart(_('Last chosen'),
                               [_('Today'), _('This week'), _('This month'), _('Long ago'), _('Never')],
                               _('Number of tracks'),
                               counts,
                               False)


def chart_playlist_track_count(conn):
    rows = conn.execute('SELECT playlist, COUNT(*) FROM track GROUP BY playlist ORDER BY COUNT(*) DESC').fetchall()
    return rows_to_column_chart(rows, _('Number of tracks in playlists'), _('Number of tracks'))


def chart_playlist_track_duration_total(conn):
    rows = conn.execute('SELECT playlist, SUM(duration)/60 FROM track GROUP BY playlist ORDER BY SUM(duration) DESC').fetchall()
    return rows_to_column_chart(rows, _('Total duration of tracks in playlists'), _('Track duration'))


def chart_playlist_track_duration_mean(conn):
    rows = conn.execute('SELECT playlist, AVG(duration)/60 FROM track GROUP BY playlist ORDER BY AVG(duration) DESC').fetchall()
    return rows_to_column_chart(rows, _('Mean duration of tracks in playlists'), _('Track duration'))


def chart_track_year(conn):
    # TODO per playlist
    rows = conn.execute('SELECT year, COUNT(year) FROM track WHERE year IS NOT NULL GROUP BY year ORDER BY year ASC').fetchall()
    return rows_to_column_chart(rows, _('Track release year distribution'), _('Release year'), vertical=True)


def charts_history(conn, period: StatsPeriod):
    after_timestamp = int(time.time()) - period.value
    result = conn.execute('''
                          SELECT timestamp, user.username, user.nickname, history.track, history.playlist
                          FROM history
                              JOIN user ON history.user = user.id
                          WHERE timestamp > ?
                          ''', (after_timestamp,))

    playlist_counter: Counter[str] = Counter()
    user_counter: Counter[str] = Counter()
    time_of_day: list[int] = [0] * 24
    day_of_week: list[int] = [0] * 7
    artist_counter: Counter[str] = Counter()
    track_counter: Counter[str] = Counter()
    album_counter: Counter[str] = Counter()

    for timestamp, username, nickname, relpath, playlist in result:
        playlist_counter.update((playlist,))
        user_counter.update((nickname if nickname else username,))

        dt = datetime.fromtimestamp(timestamp)
        time_of_day[dt.hour] += 1
        day_of_week[dt.weekday()] += 1

        track = Track.by_relpath(conn, relpath)
        if track:
            meta = track.metadata()
            if meta.artists:
                artist_counter.update(meta.artists)
            if meta.album:
                album_counter.update((meta.album,))
            track_counter.update((meta.display_title(),))
        else:
            track_counter.update((relpath,))

    charts = {
        'top-playlists': counter_to_column_chart(playlist_counter, _('Top playlists'), _('Times played')),
        'top-users': counter_to_column_chart(user_counter, _('Most active users'), _('Times played')),
        'top-tracks': counter_to_column_chart(track_counter, _('Most played tracks'), _('Times played')),
        'top-artists': counter_to_column_chart(artist_counter, _('Most played artists'), _('Times played')),
        'top-albums': counter_to_column_chart(album_counter, _('Most played albums'), _('Times played')),
    }

    charts['time-of-day'] = simple_bar_chart(_('Time of day'),
                                             [f'{i:02}:00' for i in range(0, 24)],
                                             _('Tracks played'),
                                             time_of_day,
                                             vertical=True)

    charts['day-of-week'] = simple_bar_chart(_('Day of week'),
                                             [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday')],
                                             _('Tracks played'),
                                             day_of_week,
                                             vertical=True)

    return charts


def get_data(period: StatsPeriod):
    with db.connect(read_only=True) as conn:
        data = {
            **charts_history(conn, period),
            'last-played': chart_last_chosen(conn),
            'playlist-track-count': chart_playlist_track_count(conn),
            'playlist-track-duration-total': chart_playlist_track_duration_total(conn),
            'playlist-track-duration-mean': chart_playlist_track_duration_mean(conn),
            'track-year': chart_track_year(conn),
        }

    return data
