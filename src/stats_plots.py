from io import BytesIO
from base64 import b64encode
from multiprocessing.pool import Pool
from collections import Counter
from sqlite3 import Connection
from datetime import datetime
import time

from flask_babel import _
from matplotlib import pyplot as plt

from music import Track

plt.style.use(('dark_background', 'fast'))

def fig_start():
    fig = plt.figure(figsize=(7, 4),)
    fig.set_tight_layout(True)
    ax = fig.gca()
    # fig, ax = plt.subplots()
    return fig, ax

def fig_end(fig) -> str:
    out = BytesIO()
    fig.savefig(out, format='svg', transparent=True, bbox_inches="tight", pad_inches=0)
    out.seek(0)
    return 'data:image/svg+xml;base64,' + b64encode(out.read()).decode()


def counter_to_xy(counter: Counter):
    xs = []
    ys = []
    for x, y in counter.most_common(10):
        xs.append(x)
        ys.append(y)
    return xs, ys


def f_playlists(data: Counter):
    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(data))
    ax.set_title(_('Top playlists'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    return fig_end(fig)


def f_users(data: Counter):
    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(data))
    ax.set_title(_('Most active users'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    return fig_end(fig)


def f_tod(data: list):
    fig, ax = fig_start()
    ax.hist(data, bins=24, range=(-0.5, 23.5))
    ax.set_title(_('Time of day'))
    ax.set_xlabel(_('Time of day'))
    ax.set_ylabel(_('Tracks played'))
    # plt.xticks([n for n in range(0, 24)], [f'{n:02}:00' for n in range(0, 24)])
    plt.xticks([0, 6, 12, 18, 24], ['00:00', '06:00', '12:00', '18:00', '00:00'])
    return fig_end(fig)


def f_dow(data: list):
    fig, ax = fig_start()
    ax.hist(data, bins=7, range=(-0.5, 6.5), orientation='horizontal')
    ax.set_title(_('Day of week'))
    ax.set_xlabel(_('Tracks played'))
    ax.set_ylabel(_('Day of week'))
    plt.yticks((0, 1, 2, 3, 4, 5, 6), (_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday')))
    return fig_end(fig)


def f_tracks(data: Counter):
    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(data))
    ax.set_title(_('Most played tracks'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    return fig_end(fig)


def f_artists(data: Counter):
    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(data))
    ax.set_title(_('Most played artists'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    return fig_end(fig)


def f_last_played(data: list):
    words = []
    current = int(time.time())
    for timestamp in data:
        if timestamp == 0:
            words.append(4) # never
        if timestamp > current - 60*60*24:
            words.append(0) # today
        elif timestamp > current - 60*60*24*7:
            words.append(1) # this week
        elif timestamp > current - 60*60*24*30:
            words.append(2) # this month
        else:
            words.append(3) # long ago

    fig, ax = fig_start()
    ax.hist(words, bins=5, orientation='horizontal', range=(-0.5, 4.5))
    ax.set_title(_('Last played'))
    ax.set_xlabel(_('Number of tracks'))
    ax.set_ylabel(_('Last played'))
    plt.yticks((0, 1, 2, 3, 4), (_('Today'), _('This week'), _('This month'), _('Long ago'), _('Never')))
    return fig_end(fig)


def get_data(conn: Connection, after_timestamp: int):
    result = conn.execute('''
                          SELECT timestamp, user.username, history.track, history.playlist, track.path IS NOT NULL AS track_exists
                          FROM history
                              JOIN user ON history.user = user.id
                              LEFT JOIN track ON history.track = track.path
                          WHERE timestamp > ?
                          ''', (after_timestamp,))

    playlist_counter = Counter()
    user_counter = Counter()
    time_of_day = []
    day_of_week = []
    artist_counter = Counter()
    track_counter = Counter()

    for timestamp, username, relpath, playlist, track_exists in result:
        playlist_counter.update((playlist,))
        user_counter.update((username,))

        dt = datetime.fromtimestamp(timestamp)
        time_of_day.append(dt.hour)
        day_of_week.append(dt.weekday())

        if track_exists:
            meta = Track.by_relpath(conn, relpath).metadata()
            if meta.artists:
                artist_counter.update(meta.artists)
            track_counter.update((meta.display_title(),))
        else:
            track_counter.update((relpath,))

    result = conn.execute('SELECT last_played FROM track')

    last_played_timestamps = [row[0] for row in result]

    return playlist_counter, user_counter, time_of_day, day_of_week, artist_counter, track_counter, last_played_timestamps


def get_plots(data):
    playlist_counter, user_counter, time_of_day, day_of_week, artist_counter, track_counter, last_played_timestamps = data

    with Pool(4) as p:
        r_playlists = p.apply_async(f_playlists, (playlist_counter,))
        r_users = p.apply_async(f_users, (user_counter,))
        r_tod = p.apply_async(f_tod, (time_of_day,))
        r_dow = p.apply_async(f_dow, (day_of_week,))
        r_tracks = p.apply_async(f_tracks, (track_counter,))
        r_artists = p.apply_async(f_artists, (artist_counter,))
        r_last_played = p.apply_async(f_last_played, (last_played_timestamps,))

        return [r_playlists.get(),
                r_users.get(),
                r_tod.get(),
                r_dow.get(),
                r_tracks.get(),
                r_artists.get(),
                r_last_played.get()]
