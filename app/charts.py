import time
from collections import Counter
from datetime import date, datetime, timedelta
from enum import Enum, unique
from sqlite3 import Connection
from typing import Any, Iterable

from flask_babel import _

from app import db
from app.music import Track

ChartT = dict[str, Any]


# Number of entries to display in a plot, for counters
COUNTER_AMOUNT = 10


@unique
class StatsPeriod(Enum):
    DAY = 24*60*60
    WEEK = 7*DAY
    MONTH = 30*DAY
    YEAR = 365*DAY

    def translated_str(self) -> str:
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
    def from_str(period: str) -> 'StatsPeriod':
        if period == 'day':
            return StatsPeriod.DAY
        elif period == 'week':
            return StatsPeriod.WEEK
        elif period == 'month':
            return StatsPeriod.MONTH
        elif period == 'year':
            return StatsPeriod.YEAR

        raise ValueError()


def chart(title: str, ldata: Iterable[str], xdata: Iterable[str|int], series, horizontal):
    chart = {
        'title': {
            'text': title
        },
        'tooltip': {},
        'legend': {
            'orient': 'vertical',
            'right': 0,
            'top': 'center',
            'data': ldata
        },
        'xAxis': {},
        'yAxis': {},
        'series': series,
    }

    if horizontal:
        chart['xAxis']['type'] = 'value'
        chart['yAxis']['type'] = 'category'
        chart['yAxis']['data'] = xdata
        chart['yAxis']['inverse'] = True
    else:
        chart['xAxis']['type'] = 'category'
        chart['yAxis']['type'] = 'value'
        chart['xAxis']['data'] = xdata

    return chart

def bar(title: str, name: str, xdata: Iterable[str|int], ydata: Iterable[int], horizontal=False):
    return chart(title, [], xdata, {'name': name, 'type': 'bar', 'data': ydata}, horizontal)


def multibar(title: str, xdata: Iterable[str|int], ydata: dict[str, Iterable[int]], horizontal=False, stack=True):
    series = [{'name': name,
               'type': 'bar',
               'data': data}
              for name, data in ydata.items()]
    if stack:
        for item in series:
            item['stack'] = 'x'
    return chart(title, [name for name, _ in ydata.items()], xdata, series, horizontal)


def rows_to_xy(rows: list[tuple[str, int]]):
    """
    Args:
        series_name: Name for single series (single color in chart)
        rows: Table rows as returned by sqlite .fetchall() for query:
              SELECT column, COUNT(*) GROUP BY column
    Returns: series_dict for chart() function
    """
    return [row[0] for row in rows], [row[1] for row in rows]

def counter_to_xy(counter: Counter):
    return rows_to_xy(counter.most_common(COUNTER_AMOUNT))


def chart_last_chosen(conn: Connection):
    """
    Last chosen chart
    """
    result = conn.execute('SELECT last_chosen FROM track')
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

    return bar(_('When tracks were last chosen by algorithm'),
               _('Number of tracks'),
               [_('Today'), _('This week'), _('This month'), _('Long ago'), _('Never')],
               counts)

def charts_playlists(conn: Connection):
    """
    Playlist related charts
    """
    counts = conn.execute('SELECT playlist, COUNT(*) FROM track GROUP BY playlist ORDER BY COUNT(*) DESC').fetchall()
    totals = conn.execute('SELECT playlist, SUM(duration)/60 FROM track GROUP BY playlist ORDER BY SUM(duration) DESC').fetchall()
    means = conn.execute('SELECT playlist, AVG(duration)/60 FROM track GROUP BY playlist ORDER BY AVG(duration) DESC').fetchall()
    return [bar(_('Number of tracks in playlists'), _('Number of tracks'), *rows_to_xy(counts)),
            bar(_('Mean duration of tracks in playlists'), _('Track duration'), *rows_to_xy(means)),
            bar(_('Total duration of tracks in playlists'), _('Track duration'), *rows_to_xy(totals))]


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

    return multibar(_('Track release year distribution'),
                    [str(year) for year in range(min_year, max_year+1)],
                    data)


def to_usernames(usernames: str, counts: dict[int, list[int]]) -> dict[str, list[int]]:
    return {usernames[i]: values
            for i, (_user_id, values) in enumerate(counts.items())}


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

    playlists: list[str] = [row[0] for row in
                            conn.execute('SELECT DISTINCT playlist FROM history WHERE timestamp > ?', (after_timestamp,))]
    user_ids: list[int] = []
    usernames: list[str] = []
    for user_id, username, nickname in conn.execute('''
                                                    SELECT DISTINCT user, username, nickname
                                                    FROM history
                                                    JOIN user ON user.id = user
                                                    WHERE timestamp > ?
                                                    ''', (after_timestamp,)):
        user_ids.append(user_id)
        if nickname:
            usernames.append(nickname)
        elif username:
            usernames.append(username)
        else:
            usernames.append('[deleted user]')

    time_of_day: dict[int, list[int]] = {}
    day_of_week: dict[int, list[int]] = {}
    day_counts: dict[int, list[int]] = {}
    playlists_counts: dict[int, list[int]] = {} # playlist plays per user
    user_counts: dict[str, list[int]] = {} # user plays per playlist

    for user_id in user_ids:
        time_of_day[user_id] = [0] * 24
        day_of_week[user_id] = [0] * 7
        day_counts[user_id] = [0] * num_days

        playlists_counts[user_id] = [0] * len(playlists)

    for playlist in playlists:
        user_counts[playlist] = [0] * len(user_ids)

    result = conn.execute('''
                          SELECT timestamp, user, history.track, history.playlist
                          FROM history
                          WHERE timestamp > ?
                          ''', (after_timestamp,))

    artist_counter: Counter[str] = Counter()
    track_counter: Counter[str] = Counter()
    album_counter: Counter[str] = Counter()

    for timestamp, user_id, relpath, playlist in result:
        dt = datetime.fromtimestamp(timestamp)
        time_of_day[user_id][dt.hour] += 1
        day_of_week[user_id][dt.weekday()] += 1
        day_counts[user_id][(dt.date() - min_day).days] += 1

        playlists_counts[user_id][playlists.index(playlist)] += 1
        user_counts[playlist][user_ids.index(user_id)] += 1

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
        multibar(_('Most active users'), usernames, user_counts),
        multibar(_('Most played playlists'), playlists, to_usernames(usernames, playlists_counts)),
        bar(_('Most played tracks'), _('Times played'), *counter_to_xy(track_counter), horizontal=True),
        bar(_('Most played artists'), _('Times played'), *counter_to_xy(artist_counter), horizontal=True),
        bar(_('Most played albums'), _('Times played'), *counter_to_xy(album_counter), horizontal=True),
        multibar(_('Time of day'), [f'{i:02}:00' for i in range(0, 24)], to_usernames(usernames, time_of_day)),
        multibar(_('Day of week'),
                    [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday')],
                    to_usernames(usernames, day_of_week)),
        # chart('line', _('Historic play count'),
        #       [(min_day + timedelta(days=i)).isoformat() for i in range(0, num_days + 1)],
        #       to_usernames(usernames, day_counts), stack=True)
    ]

    return charts


def chart_unique_artists(conn: Connection):
    rows = conn.execute('''
                        SELECT playlist, COUNT(artist), COUNT(DISTINCT artist)
                        FROM track
                            INNER JOIN track_artist ON track.path = track_artist.track
                        GROUP BY playlist
                        ''')
    ratio_rows = [(playlist, artists / tracks) for playlist, tracks, artists in rows]
    ratio_rows = sorted(ratio_rows, key=lambda x: x[1])
    return bar(_('Artist diversity'), _('Ratio'), *rows_to_xy(ratio_rows))
def chart_popular_artists(conn: Connection):
    artists = [row[0] for row in conn.execute('SELECT artist FROM track_artist GROUP BY artist ORDER BY COUNT(artist) DESC LIMIT 10')]

    rows = conn.execute('''
                        SELECT playlist, artist, COUNT(artist)
                        FROM track INNER JOIN track_artist ON track.path = track_artist.track
                        WHERE artist IN (SELECT artist
                                         FROM track_artist
                                         GROUP BY artist
                                         ORDER BY COUNT(artist) DESC
                                         LIMIT 10)
                        GROUP BY artist, playlist
                        ''').fetchall()

    artist_counts: dict[str, list[int]] = {}

    for playlist, artist, artist_count in rows:
        if playlist not in artist_counts:
            artist_counts[playlist] = [0] * len(artists)

        artist_counts[playlist][artists.index(artist)] = artist_count

    return multibar(_('Popular artists'), artists, artist_counts, horizontal=True)


def get_data(period: StatsPeriod):
    """
    Generate charts as json data for stats.jinja2
    """
    with db.connect(read_only=True) as conn:
        data = [*charts_history(conn, period),
                *charts_playlists(conn),
                chart_track_year(conn),
                chart_last_chosen(conn),
                chart_unique_artists(conn),
                chart_popular_artists(conn)]

    return data
