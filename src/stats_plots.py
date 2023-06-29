from io import BytesIO
from base64 import b64encode
from multiprocessing.pool import Pool
from collections import Counter
from datetime import datetime
import time
import tempfile
import os

from flask_babel import _
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp(prefix='music-matplotlib')
from matplotlib import pyplot as plt

import db
from music import Track

# Number of entries to display in a plot, for counters
COUNTER_AMOUNT = 10

plt.style.use(('dark_background', 'fast'))

def fig_start():
    fig = plt.figure(figsize=(7, 4),)
    fig.set_tight_layout(True)
    ax = fig.gca()
    return fig, ax

def fig_end(fig) -> str:
    out = BytesIO()
    fig.savefig(out, format='svg', transparent=True, bbox_inches="tight", pad_inches=0)
    out.seek(0)
    return 'data:image/svg+xml;base64,' + b64encode(out.read()).decode()


def counter_to_xy(counter: Counter, limit=COUNTER_AMOUNT):
    xs = []
    ys = []
    for x, y in counter.most_common(limit):
        xs.append(x)
        ys.append(y)
    return xs, ys


def rows_to_xy(rows: list[tuple]):
    xs = []
    ys = []
    for x, y in rows:
        xs.append(x)
        ys.append(y)
    return xs, ys


# def _time_xticks(hour_offset: int):
#     xticks_x = []
#     xticks_y = []
#     for i in count(hour_offset, 3):
#         if i > hour_offset + 24:
#             break
#         xticks_x.append(i - hour_offset)
#         xticks_y.append(f'{i % 24:02}:00')
#     plt.xticks(xticks_x, xticks_y)


def _plots_history(after_timestamp: int) -> list[str]:
    # tod_offset = 3

    with db.connect(read_only=True) as conn:
        result = conn.execute('''
                            SELECT timestamp, user.username, history.track, history.playlist
                            FROM history
                                JOIN user ON history.user = user.id
                            WHERE timestamp > ?
                            ''', (after_timestamp,))

        playlist_counter: Counter[str] = Counter()
        user_counter: Counter[str] = Counter()
        time_of_day: list[int] = []
        day_of_week: list[int] = []
        artist_counter: Counter[str] = Counter()
        track_counter: Counter[str] = Counter()
        album_counter: Counter[str] = Counter()

        for timestamp, username, relpath, playlist in result:
            playlist_counter.update((playlist,))
            user_counter.update((username,))

            dt = datetime.fromtimestamp(timestamp)
            # time_of_day.append(dt.hour - tod_offset)
            time_of_day.append(dt.hour)
            day_of_week.append(dt.weekday())

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

    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(playlist_counter))
    ax.set_title(_('Top playlists'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    plot_playlists = fig_end(fig)

    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(user_counter))
    ax.set_title(_('Most active users'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    plot_users = fig_end(fig)

    fig, ax = fig_start()
    ax.hist(time_of_day, bins=24, range=(0, 24))
    ax.set_title(_('Time of day'))
    ax.set_xlabel(_('Time of day'))
    ax.set_ylabel(_('Tracks played'))
    ax.set_xticks(list(range(0, 24, 3)) + [24])
    ax.set_xticklabels([f'{i:02}:00' for i in range(0, 24, 3)] + ['00:00'])
    # _time_xticks(tod_offset)
    plot_tod = fig_end(fig)

    fig, ax = fig_start()
    ax.hist(day_of_week, bins=7, range=(-0.5, 6.5), orientation='horizontal')
    ax.set_title(_('Day of week'))
    ax.set_xlabel(_('Tracks played'))
    ax.set_ylabel(_('Day of week'))
    plt.yticks((0, 1, 2, 3, 4, 5, 6), (_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday')))
    plot_dow = fig_end(fig)

    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(track_counter))
    ax.set_title(_('Most played tracks'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    plot_tracks = fig_end(fig)

    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(artist_counter))
    ax.set_title(_('Most played artists'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    plot_artists = fig_end(fig)

    fig, ax = fig_start()
    bars = ax.barh(*counter_to_xy(album_counter))
    ax.set_title(_('Most played albums'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Times played'))
    plot_albums = fig_end(fig)

    return plot_playlists, plot_users, plot_tod, plot_dow, plot_tracks, plot_artists, plot_albums


def _plots_last_played() -> list[str]:
    with db.connect(read_only=True) as conn:
        result = conn.execute('SELECT last_played FROM track')
        words = []
        current = int(time.time())
        for (timestamp,) in result:
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
    ax.set_title(_('Last chosen'))
    ax.set_xlabel(_('Number of tracks'))
    ax.set_ylabel(_('Last chosen'))
    plt.yticks((0, 1, 2, 3, 4), (_('Today'), _('This week'), _('This month'), _('Long ago'), _('Never')))
    plot = fig_end(fig)
    return plot,


def _plots_playlists() -> list[str]:
    with db.connect(read_only=True) as conn:
        counts = conn.execute('SELECT playlist, COUNT(*) FROM track GROUP BY playlist ORDER BY COUNT(*) DESC').fetchall()
        totals = conn.execute('SELECT playlist, SUM(duration)/60 FROM track GROUP BY playlist ORDER BY SUM(duration) DESC').fetchall()
        means = conn.execute('SELECT playlist, AVG(duration)/60 FROM track GROUP BY playlist ORDER BY AVG(duration) DESC').fetchall()

    fig, ax = fig_start()
    bars = ax.barh(*rows_to_xy(counts))
    ax.set_title(_('Number of tracks in playlists'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Number of tracks'))
    plot_counts = fig_end(fig)

    fig, ax = fig_start()
    ax.barh(*rows_to_xy(totals))
    ax.set_title(_('Total duration of tracks in playlists'))
    ax.set_xlabel(_('Total duration in minutes'))
    plot_totals = fig_end(fig)

    fig, ax = fig_start()
    ax.barh(*rows_to_xy(means))
    ax.set_title(_('Mean duration of tracks in playlist'))
    ax.set_xlabel(_('Mean duration in minutes'))
    plot_means = fig_end(fig)

    return plot_counts, plot_totals, plot_means


def _plots_metadata() -> list[str]:
    with db.connect(read_only=True) as conn:
        result = conn.execute('''
                                SELECT year
                                FROM track
                                ''')

        year_counter: Counter[int] = Counter()

        for year, in result:
            if year is not None:
                year_counter.update((year,))

    fig, ax = fig_start()
    bars = ax.bar(*counter_to_xy(year_counter, limit=None))
    ax.set_title(_('Track release year distribution'))
    ax.bar_label(bars)
    ax.set_xlabel(_('Release year'))
    plot_years = fig_end(fig)

    return plot_years,


def get_plots(after_timestamp: int) -> list[str]:
    """
    Get list of plots
    Args:
        after_timestamp: Unix timestamp (seconds). Only history data more recent than
                         this timestamp is considered.
    Returns: List of plots, as strings containing base64 encoded SVG data
    """
    with Pool(4) as p:
        r_history = p.apply_async(_plots_history, (after_timestamp,))
        r_last_played = p.apply_async(_plots_last_played)
        r_playlists = p.apply_async(_plots_playlists)
        r_metadata = p.apply_async(_plots_metadata)

        return [*r_history.get(),
                *r_last_played.get(),
                *r_playlists.get(),
                *r_metadata.get()]
