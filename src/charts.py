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


def chart(chart_type: str, title: str, categories: list[str], series_dict: dict, stack=False):
    """
    Create chart json expected by javascript in stats.jinja2
    Args:
        chart_type: Chart type, see stats.jinja2 for accepted values
        title: Chart type
        categories: List of category names (names for each value column)
        series_dict: Dict with series name as key and data points as values (must be same length as categories)
    """
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
        },
        'data': {
            'categories': categories,
            'series': [{'name': name, 'data': data} for name, data in series_dict.items()],
        }
    }


def data_from_rows(series_name: str, rows: list[tuple[str, int]]):
    """
    Args:
        series_name: Name for single series (single color in chart)
        rows: Table rows as returned by sqlite .fetchall() for query:
              SELECT column, COUNT(*) GROUP BY column
    Returns: series_dict for chart() function
    """
    return [row[0] for row in rows], {series_name: [row[1] for row in rows]}


def data_from_counter(series_name: str, counter: Counter):
    """
    Args:
        series_name: Name for single series (single color in chart)
        counter: Counter
    Returns: series_dict for chart() function
    """
    return data_from_rows(series_name, counter.most_common(COUNTER_AMOUNT))


def chart_last_chosen(conn: Connection):
    """
    Last chosen chart
    """
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

    return chart('bar',
                 _('When tracks were last chosen by algorithm'),
                 [_('Today'), _('This week'), _('This month'), _('Long ago'), _('Never')],
                 {_('Number of tracks'): counts})

def charts_playlists(conn: Connection):
    """
    Playlist related charts
    """
    counts = conn.execute('SELECT playlist, COUNT(*) FROM track GROUP BY playlist ORDER BY COUNT(*) DESC').fetchall()
    totals = conn.execute('SELECT playlist, SUM(duration)/60 FROM track GROUP BY playlist ORDER BY SUM(duration) DESC').fetchall()
    means = conn.execute('SELECT playlist, AVG(duration)/60 FROM track GROUP BY playlist ORDER BY AVG(duration) DESC').fetchall()
    return [chart('column', _('Number of tracks in playlists'), *data_from_rows(_('Number of tracks'), counts)),
            chart('column', _('Mean duration of tracks in playlists'), *data_from_rows(_('Track duration'), means)),
            chart('column', _('Total duration of tracks in playlists'), *data_from_rows(_('Track duration'), totals))]


def chart_track_year(conn: Connection):
    """
    Track release year chart
    """
    min_year, max_year = conn.execute('SELECT MAX(1950, MIN(year)), MIN(2030, MAX(year)) FROM track').fetchone()

    data = {}
    for playlist, in conn.execute('SELECT path FROM playlist').fetchall():
        data[playlist] = [0] * (max_year - min_year + 1)

    rows = conn.execute('''SELECT playlist, year, COUNT(year)
                           FROM track
                           WHERE year IS NOT NULL
                           GROUP BY playlist, year
                           ORDER BY year ASC''').fetchall()
    for playlist, year, count in rows:
        if year < min_year or year > max_year:
            continue
        data[playlist][year - min_year] = count

    return chart('column',
                 _('Track release year distribution'),
                 list(range(min_year, max_year+1)),
                 data,
                 stack=True)


def charts_history(conn: Connection, period: StatsPeriod):
    """
    Playback history related charts
    """
    after_timestamp = int(time.time()) - period.value

    min_time, max_time = conn.execute('SELECT MIN(timestamp), MAX(timestamp) FROM history WHERE timestamp > ?',
                                      (after_timestamp,)).fetchone()
    # If no tracks are played in the specified period
    if min_time is None:
        return []

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

    charts = [
        chart('bar', _('Most active users'), *data_from_counter(_('Tracks played'), user_counter)),
        chart('bar', _('Most played playlists'), playlists, playlists_counts, stack=True),
        chart('bar', _('Most played tracks'), *data_from_counter(_('Times played'), track_counter)),
        chart('bar', _('Most played artists'), *data_from_counter(_('Times played'), artist_counter)),
        chart('bar', _('Most played albums'), *data_from_counter(_('Times played'), album_counter)),
        chart('column', _('Time of day'), [f'{i:02}:00' for i in range(0, 24)], time_of_day, stack=True),
        chart('column', _('Day of week'),
              [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday')],
              day_of_week, stack=True),
        chart('line', _('Historic play count'),
              [(min_day + timedelta(days=i)).isoformat() for i in range(0, num_days + 1)], day_counts, stack=True)
    ]

    return charts


def get_data(period: StatsPeriod):
    """
    Generate charts as json data for stats.jinja2
    """
    with db.connect(read_only=True) as conn:
        data = [*charts_history(conn, period),
                *charts_playlists(conn),
                chart_track_year(conn),
                chart_last_chosen(conn)]

    return data
