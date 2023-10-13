from enum import Enum, unique
from collections import Counter
from datetime import datetime, date, timedelta
import time
from sqlite3 import Connection

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


# https://github.com/nhn/tui.chart/blob/main/docs/en/common-theme.md
THEME = {
    'chart': {
        'backgroundColor': 'transparent',
    },
    'title': {
        'color': 'white',
    },
    'xAxis': {
        'title': {
            'color': 'white',
        },
        'label': {
            'color': 'white',
        },
        'color': 'white',
    },
    'yAxis': {
        'title': {
            'color': 'white',
        },
        'label': {
            'color': 'white',
        },
        'color': 'white',
    },
    'legend': {
        'label': {
            'color': 'white',
        }
    },
    'plot': {
        'vertical': {
            'lineColor': 'transparent',
        },
        'horizontal': {
            'lineColor': 'transparent',
        }
    }
}


def chart(chart_type, title, categories, series_dict: dict, stack=False):
    return {
        'type': chart_type,
        'options': {
            'series': {
                'stack': stack,
            },
            'chart': {
                'title': title,
                'width': 'auto',
                'height': 'auto',
            },
            'theme': THEME,
        },
        'data': {
            'categories': categories,
            'series': [{'name': name, 'data': data} for name, data in series_dict.items()],
        }
    }


def bar_chart(title, categories, series_dict: dict, vertical=False, **kwargs):
    return chart('column' if vertical else 'bar', title, categories, series_dict, **kwargs)


def rows_to_column_chart(rows: list[tuple[str, int]], title: str, series_name: str, vertical=False):
    return bar_chart(title, [row[0] for row in rows], {series_name: [row[1] for row in rows]}, vertical)


def counter_to_column_chart(counter: Counter, title: str, series_name: str, vertical=False):
    return rows_to_column_chart(counter.most_common(COUNTER_AMOUNT), title, series_name, vertical)


def chart_last_chosen(conn: Connection):
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

    return bar_chart(_('Last chosen'),
                    [_('Today'), _('This week'), _('This month'), _('Long ago'), _('Never')],
                    {_('Number of tracks'): counts})


def chart_playlist_track_count(conn: Connection):
    rows = conn.execute('SELECT playlist, COUNT(*) FROM track GROUP BY playlist ORDER BY COUNT(*) DESC').fetchall()
    return rows_to_column_chart(rows, _('Number of tracks in playlists'), _('Number of tracks'))


def chart_playlist_track_duration_total(conn: Connection):
    rows = conn.execute('SELECT playlist, SUM(duration)/60 FROM track GROUP BY playlist ORDER BY SUM(duration) DESC').fetchall()
    return rows_to_column_chart(rows, _('Total duration of tracks in playlists'), _('Track duration'))


def chart_playlist_track_duration_mean(conn: Connection):
    rows = conn.execute('SELECT playlist, AVG(duration)/60 FROM track GROUP BY playlist ORDER BY AVG(duration) DESC').fetchall()
    return rows_to_column_chart(rows, _('Mean duration of tracks in playlists'), _('Track duration'))


def chart_track_year(conn: Connection):
    min_year, max_year = conn.execute('SELECT MAX(1950, MIN(year)), MIN(2030, MAX(year)) FROM track').fetchone()

    data = {}
    for playlist, in conn.execute('SELECT path FROM playlist').fetchall():
        data[playlist] = [0] * (max_year - min_year + 1)

    rows = conn.execute('SELECT playlist, year, COUNT(year) FROM track WHERE year IS NOT NULL GROUP BY playlist, year ORDER BY year ASC').fetchall()
    for playlist, year, count in rows:
        if year < min_year or year > max_year:
            continue
        data[playlist][year - min_year] = count

    return bar_chart(_('Track release year distribution'),
                    list(range(min_year, max_year+1)),
                    data,
                    vertical=True,
                    stack=True)


def charts_history(conn: Connection, period: StatsPeriod):
    after_timestamp = int(time.time()) - period.value

    min_time, max_time = conn.execute('SELECT MIN(timestamp), MAX(timestamp) FROM history WHERE timestamp > ?',
                                      (after_timestamp,)).fetchone()
    min_day = date.fromtimestamp(min_time)
    num_days = (date.fromtimestamp(max_time) - min_day).days + 1

    time_of_day: dict[str, list[int]] = {}
    day_of_week: dict[str, list[int]] = {}
    day_counts: dict[str, list[int]] = {}

    playlists: list[str] = [row[0] for row in conn.execute('SELECT DISTINCT playlist FROM history WHERE timestamp > ?', (after_timestamp,))]
    playlists_counts: dict[str, list[int]] = {}

    for username, in conn.execute('''SELECT DISTINCT user.username
                                     FROM history JOIN user ON history.user = user.id
                                     WHERE timestamp > ?''', (after_timestamp,)):
        time_of_day[username] = [0] * 24
        day_of_week[username] = [0] * 7
        day_counts[username] = [0] * num_days

        playlists_counts[username] = [0] * len(playlists)

    result = conn.execute('''
                          SELECT timestamp, user.username, user.nickname, history.track, history.playlist
                          FROM history
                              JOIN user ON history.user = user.id
                          WHERE timestamp > ?
                          ORDER BY timestamp ASC
                          ''', (after_timestamp,))

    playlist_counter: Counter[str] = Counter()
    user_counter: Counter[str] = Counter()
    artist_counter: Counter[str] = Counter()
    track_counter: Counter[str] = Counter()
    album_counter: Counter[str] = Counter()

    for timestamp, username, nickname, relpath, playlist in result:
        playlist_counter.update((playlist,))
        user_counter.update((nickname if nickname else username,))

        dt = datetime.fromtimestamp(timestamp)
        time_of_day[username][dt.hour] += 1
        day_of_week[username][dt.weekday()] += 1
        day_counts[username][(dt.date() - min_day).days] += 1

        playlists_counts[username][playlists.index(playlist)] += 1

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
        'top-users': counter_to_column_chart(user_counter, _('Most active users'), _('Times played')),
        'top-tracks': counter_to_column_chart(track_counter, _('Most played tracks'), _('Times played')),
        'top-artists': counter_to_column_chart(artist_counter, _('Most played artists'), _('Times played')),
        'top-albums': counter_to_column_chart(album_counter, _('Most played albums'), _('Times played')),
    }

    charts['top-playlists'] = bar_chart(_('Top playlists'),
                                        playlists,
                                        playlists_counts,
                                        stack=True)

    charts['time-of-day'] = bar_chart(_('Time of day'),
                                      [f'{i:02}:00' for i in range(0, 24)],
                                      time_of_day,
                                      stack=True,
                                      vertical=True)

    charts['day-of-week'] = bar_chart(_('Day of week'),
                                      [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday')],
                                      day_of_week,
                                      stack=True,
                                      vertical=True)

    charts['historic-play-count'] = chart('line',
                                          _('Historic play count'),
                                      [(min_day + timedelta(days=i)).isoformat() for i in range(0, num_days + 1)],
                                      day_counts,
                                      stack=True)

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
