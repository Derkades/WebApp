import time
from collections import Counter, deque
from datetime import datetime
from enum import Enum, unique
from sqlite3 import Connection
from typing import Any, Iterable, Optional

from flask_babel import _

from raphson_mp import db

ChartT = dict[str, Any]


# Number of entries to display in a plot, for counters
COUNTER_AMOUNT = 10


@unique
class StatsPeriod(Enum):
    DAY = 24*60*60
    WEEK = 7*DAY
    MONTH = 30*DAY
    YEAR = 365*DAY
    ALL = 0

    @property
    def after_timestamp(self):
        if self is StatsPeriod.ALL:
            return 0
        else:
            return int(time.time()) - self.value

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
        elif period == 'all':
            return StatsPeriod.ALL

        raise ValueError()


def chart(title: str, ldata: Iterable[str], xdata: Optional[Iterable[str|int]], ydata: Optional[Iterable[str|int]], series: list[object],
          all_labels = False, extra = {}):
    chart = {
        'title': {
            'text': title
        },
        'tooltip': {},
        'legend': {
            'orient': 'vertical',
            'right': 0,
            'top': 'center',
            'type': 'scroll',
            'data': ldata,
        },
        'xAxis': {
            'type': 'category' if xdata else 'value',
            'data': xdata,
        },
        'yAxis': {
            'type': 'category' if ydata else 'value',
            'data': ydata,
        },
        'series': series,
        **extra,
    }

    if ydata and not xdata:
        chart['yAxis']['inverse'] = True

    if all_labels:
        for axis in ('xAxis', 'yAxis'):
            chart[axis]['axisLabel'] = {'interval': 0}

    return chart


def chart_singleaxis(title: str, ldata: Iterable[str], axisdata: Iterable[str|int], series, horizontal):
    if horizontal:
        ydata = axisdata
        xdata = None
    else:
        xdata = axisdata
        ydata = None
    return chart(title, ldata, xdata, ydata, series)


def bar(title: str, name: str, axisdata: Iterable[str|int], seriesdata: Iterable[int], horizontal=False):
    return chart_singleaxis(title, [], axisdata, [{'name': name, 'type': 'bar', 'data': seriesdata}], horizontal)


def multibar(title: str, axisdata: Iterable[str|int], seriesdata: dict[str, Iterable[int]], horizontal=False, stack=True):
    series = [{'name': name,
               'type': 'bar',
               'data': data}
              for name, data in seriesdata.items()]
    if stack:
        for item in series:
            item['stack'] = 'x'
    return chart_singleaxis(title, [name for name, _ in seriesdata.items()], axisdata, series, horizontal)


def heatmap(title: str, name: str, xdata: Iterable[str|int], ydata: Iterable[str|int], seriesdata):
    series = [{'name': name,
               'type': 'heatmap',
               'data': seriesdata}]
    extra = {'visualMap': {'min': 0,
                           'max': max(item[2] for item in seriesdata) if len(seriesdata) else 0,
                           'orient': 'vertical',
                           'right': 0,
                           'top': 'center'}}
    return chart(title, [], xdata, ydata, series, all_labels=True, extra=extra)


def rows_to_xy(rows: list[tuple[str, int]]):
    """
    Args:
        series_name: Name for single series (single color in chart)
        rows: Table rows as returned by sqlite .fetchall() for query:
              SELECT column, COUNT(*) GROUP BY column
    Returns: series_dict for chart() function
    """
    return [row[0] for row in rows], [row[1] for row in rows]


def rows_to_xy_multi(rows: list[tuple[str, str, int]], case_sensitive=True, restore_case=False) -> tuple[list[str], dict[str, list[int]]]:
    """
    Convert rows
    [a1, b1, c1]
    [a1, b2, c2]
    [a2, b1, c3]
    to xdata: [a1, a2], ydata: {b1: [c1, c3], b2: [c2, 0]}
    Where a appears on the x axis, b appears in in the legend (is stacked), and c is data.
    """
    # Create list of a values, sorted by total b for all a
    a_list: list[str] = []
    a_counts: dict[str, int] = {} # for sorting
    for a, _b, c in rows:
        if not case_sensitive:
            a = a.lower()

        if a not in a_list:
            a_list.append(a)
            a_counts[a] = 0

        a_counts[a if case_sensitive else a.lower()] += c

    a_list = sorted(a_list, key=lambda a: -a_counts[a])

    ydata: dict[str, list[int]] = {}

    for a, b, c in rows:
        if b not in ydata:
            ydata[b] = [0] * len(a_list)
        a_index = a_list.index(a if case_sensitive else a.lower())
        ydata[b][a_index] = c

    if restore_case:
        # Restore original case
        for i, a in enumerate(a_list):
            for a2, _b, _c in rows:
                if a.lower() == a2.lower():
                    a_list[i] = a2
                    break

    return a_list, ydata


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
    for playlist, in conn.execute('SELECT playlist FROM track GROUP BY playlist ORDER BY COUNT(*) DESC LIMIT 15').fetchall():
        data[playlist] = [0] * (max_year - min_year + 1)

    rows = conn.execute('''SELECT playlist, year, COUNT(year)
                           FROM track
                           WHERE year IS NOT NULL
                           GROUP BY playlist, year
                           ORDER BY year ASC''').fetchall()
    for playlist, year, count in rows:
        if year < min_year or year > max_year or playlist not in data:
            continue
        data[playlist][year - min_year] = count

    return multibar(_('Track release year distribution'),
                    [str(year) for year in range(min_year, max_year+1)],
                    data)


def to_usernames(usernames: str, counts: dict[int, list[int]]) -> dict[str, list[int]]:
    return {usernames[i]: values
            for i, (_user_id, values) in enumerate(counts.items())}


def charts_history(conn: Connection, after_timestamp: int):
    """
    Playback history related charts
    """
    rows = conn.execute('''
                        SELECT username, playlist, COUNT(*)
                        FROM history JOIN user ON history.user = user.id
                        WHERE timestamp > ?
                        GROUP BY user, playlist
                        ''', (after_timestamp,)).fetchall()
    yield multibar(_('Active users'), *rows_to_xy_multi(rows))

    rows = [(b, a, c) for a, b, c in rows]
    yield multibar(_('Played playlists'), *rows_to_xy_multi(rows))

    rows = conn.execute('''
                        SELECT track, username, COUNT(*)
                        FROM history
                            JOIN user ON history.user = user.id
                        WHERE timestamp > ?
                            AND track IN (SELECT track
                                           FROM history
                                           WHERE timestamp > ?
                                           GROUP BY track
                                           ORDER BY COUNT(*) DESC
                                           LIMIT 10)
                        GROUP BY track, username
                        ''', (after_timestamp, after_timestamp,)).fetchall()
    yield multibar(_('Most played tracks'), *rows_to_xy_multi(rows), horizontal=True)

    rows = conn.execute('''
                        SELECT artist, username, COUNT(*)
                        FROM history
                            INNER JOIN track ON history.track = track.path
                            JOIN track_artist ON track_artist.track = track.path
                            JOIN user ON history.user = user.id
                        WHERE timestamp > ?
                            AND artist IN (SELECT artist
                                           FROM history
                                               INNER JOIN track ON history.track = track.path
                                               JOIN track_artist ON track_artist.track = track.path
                                           WHERE timestamp > ?
                                           GROUP BY artist
                                           ORDER BY COUNT(*) DESC
                                           LIMIT 10)
                        GROUP BY artist, username
                        ''', (after_timestamp, after_timestamp,)).fetchall()
    yield multibar(_('Most played artists'), *rows_to_xy_multi(rows, case_sensitive=False, restore_case=True), horizontal=True)

    rows = conn.execute('''
                        SELECT album, username, COUNT(*)
                        FROM history
                            INNER JOIN track ON history.track = track.path
                            JOIN user ON history.user = user.id
                        WHERE timestamp > ?
                            AND album IN (SELECT album
                                           FROM history
                                               INNER JOIN track ON history.track = track.path
                                           WHERE timestamp > ?
                                           GROUP BY album
                                           ORDER BY COUNT(*) DESC
                                           LIMIT 10)
                        GROUP BY album, username
                        ''', (after_timestamp, after_timestamp,)).fetchall()
    yield multibar(_('Most played albums'), *rows_to_xy_multi(rows, case_sensitive=False, restore_case=True), horizontal=True)

    time_of_day: dict[str, list[int]] = {}
    day_of_week: dict[str, list[int]] = {}

    for username, in conn.execute('SELECT DISTINCT username FROM history JOIN user ON history.user = user.id WHERE timestamp > ?', (after_timestamp,)):
        time_of_day[username] = [0] * 24
        day_of_week[username] = [0] * 7

    for timestamp, username in conn.execute('SELECT timestamp, username FROM history JOIN user ON history.user = user.id WHERE timestamp > ?', (after_timestamp,)):
        dt = datetime.fromtimestamp(timestamp)
        time_of_day[username][dt.hour] += 1
        day_of_week[username][dt.weekday()] += 1

    yield multibar(_('Time of day'), [f'{i:02}:00' for i in range(0, 24)], time_of_day)
    yield multibar(_('Day of week'), [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday')], day_of_week)


def chart_unique_artists(conn: Connection):
    rows = conn.execute('''
                        SELECT playlist, ROUND(COUNT(DISTINCT artist) / CAST(COUNT(artist) AS float), 2) AS ratio
                        FROM track INNER JOIN track_artist ON track.path = track_artist.track
                        GROUP BY playlist
                        ORDER BY ratio
                        ''').fetchall()
    return bar(_('Artist diversity'), _('Ratio'), *rows_to_xy(rows))


def chart_popular_artists_tags(conn: Connection):
    for table, title in (('artist', _('Artists in playlists')), ('tag', _('Tags in playlists'))):
        rows = conn.execute(f'''
                            SELECT {table}, playlist, COUNT({table})
                            FROM track INNER JOIN track_{table} ON track.path = track_{table}.track
                            WHERE {table} IN (SELECT {table} FROM track_{table} GROUP BY {table} ORDER BY COUNT({table}) DESC LIMIT 15)
                            GROUP BY {table}, playlist
                            ''').fetchall()
        yield multibar(title, *rows_to_xy_multi(rows, case_sensitive=False, restore_case=table == 'artist'), horizontal=True)


def similarity_heatmap(conn: Connection):
    playlists = [row[0] for row in conn.execute('SELECT playlist FROM track GROUP BY playlist ORDER BY COUNT(*) DESC LIMIT 15')]
    result = conn.execute('''
                          SELECT t1.playlist, t2.playlist, COUNT(DISTINCT ta1.artist)
                          FROM track_artist ta1
                             JOIN track_artist ta2 ON ta1.artist = ta2.artist
                             JOIN track t1 ON ta1.track = t1.path
                             JOIN track t2 ON ta2.track = t2.path
                          GROUP BY t1.playlist, t2.playlist
                          ''')

    data_dict: dict[tuple(str, str), int] = {}
    for p1, p2, count in result:
        data_dict[(p1, p2)] = count

    xp = playlists[:-1]
    yp = playlists[1:]
    data = []
    for i1, p1 in enumerate(xp):
        for i2, p2 in enumerate(yp):
            if i1 > i2:
                continue
            elif (p1, p2) in data_dict:
                if data_dict[(p1, p2)] is not None:
                    data.append([i1, i2, data_dict[(p1, p2)]])
            else:
                data.append([i1, i2, 0])

    return heatmap(_('Artist similarity'), _('Number of artists in common'), xp, yp, data)


def get_data(period: StatsPeriod):
    """
    Generate charts as json data for stats.jinja2
    """
    with db.connect(read_only=True) as conn:
        data = [*charts_history(conn, period.after_timestamp),
                similarity_heatmap(conn),
                *chart_popular_artists_tags(conn),
                chart_track_year(conn),
                *charts_playlists(conn),
                chart_last_chosen(conn),
                chart_unique_artists(conn)]

    return data
