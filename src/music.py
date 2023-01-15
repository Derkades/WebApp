from pathlib import Path
from typing import Iterator, Literal, Optional
from datetime import datetime
import subprocess
from subprocess import CompletedProcess
import logging
import tempfile
import shutil
from dataclasses import dataclass
from sqlite3 import Connection

from auth import User
import cache
import metadata
import settings
import scanner


log = logging.getLogger('app.music')


MUSIC_EXTENSIONS = [
    '.mp3',
    '.flac',
    '.ogg',
    '.webm',
    '.mkv',
    '.mka',
    '.wma',
    '.m4a',
    '.wav',
    '.opus',
    '.aac',
]


def to_relpath(path: Path) -> str:
    """
    Returns: Relative path as string, excluding base music directory
    """
    relpath = path.absolute().as_posix()[len(Path(settings.music_dir).absolute().as_posix())+1:]
    return relpath if len(relpath) > 0 else '.'


def from_relpath(relpath: str) -> Path:
    """
    Creates Path object from string path relative to music base directory, with directory
    traversal protection.
    """
    if relpath.startswith('/'):
        raise Exception('Relative path must not start with /')
    path = Path(settings.music_dir, relpath).absolute()
    if not path.is_relative_to(Path(settings.music_dir)):
        raise Exception('Must not go outside of music base directory')
    return path


def scan_playlist(playlist_path: str) -> Iterator[Path]:
    """
    Scan playlist for tracks, recursively
    Args:
        playlist_path: Playlist name
    Returns: Paths iterator
    """
    yield from scan_music(from_relpath(playlist_path))


def scan_music(path) -> Iterator[Path]:
    """
    Scan directory for tracks, recursively
    Args:
        path: Directory Path
    Returns: Paths iterator
    """
    for ext in MUSIC_EXTENSIONS:
        for track_path in path.glob('**/*' + ext):
            if not track_path.name.startswith('.trash.'):
                yield track_path


def has_music_extension(path: Path) -> bool:
    """
    Check if file is a music file
    """
    for ext in MUSIC_EXTENSIONS:
        if path.name.endswith(ext):
            return True
    return False


@dataclass
class Track:
    conn: Connection
    relpath: str
    path: Path

    @property
    def playlist(self) -> str:
        """
        Returns: Part of track path before first slash
        """
        return self.relpath[:self.relpath.index('/')]

    def metadata(self):
        """
        Returns: Cached metadata for this track, as a Metadata object
        """
        return metadata.cached(self.conn, self.relpath)

    def transcoded_audio(self,
                         quality: Literal['verylow'] | Literal['low'] | Literal['high'],
                         fruit: bool) -> bytes:
        """
        Normalize and compress audio using ffmpeg
        Returns: Compressed audio bytes
        """

        channels_table = {
            'verylow': 1,
            'low': 2,
            'high': 2,
        }

        if fruit:
            # Special AAC audio in MP4 container for Safari. caniuse.com claims opus in CAF
            # container is supported, but doesn't seem to work on Safari 16.0 macOS Monterey,
            # so we'll have to use the less-efficient AAC codec at a higher bit rate.
            container_format = 'mp4'
            audio_codec = 'aac'
            bit_rate_table = {
                'verylow': '64k',
                'low': '128k',
                'high': '256k',
            }
        else:
            # Opus in webm container for all other browsers
            container_format = 'webm'
            audio_codec = 'libopus'
            bit_rate_table = {
                'verylow': '32k',
                'low': '64k',
                'high': '128k',
            }

        channels = channels_table[quality]
        bit_rate = bit_rate_table[quality]

        in_path_abs = self.path.absolute().as_posix()

        cache_key = 'audio' + container_format + in_path_abs + bit_rate

        cached_data = cache.retrieve(cache_key)
        if cached_data is not None:
            log.info('Returning cached audio')
            return cached_data

        # 1. Stilte aan het begin weghalen met silenceremove: https://ffmpeg.org/ffmpeg-filters.html#silenceremove
        # 2. Audio omkeren
        # 3. Stilte aan het eind (nu begin) weghalen
        # 4. Audio omkeren
        # 5. Audio normaliseren met dynaudnorm: https://ffmpeg.org/ffmpeg-filters.html#dynaudnorm
        # 6. Audio fade-in met afade: https://ffmpeg.org/ffmpeg-filters.html#afade-1

        # Nu zou je zeggen dat we ook stop_periods kunnen gebruiken om stilte aan het eind weg te halen, maar
        # dat werkt niet. Van sommige nummers (bijv. irrenhaus) werd alles eraf geknipt behalve de eerste paar
        # seconden. Ik heb geen idee waarom, de documentatie is vaag. Oplossing: keer het nummer om, en haal
        # nog eens stilte aan "het begin" weg.

        # filters = f'''
        # atrim=0:{settings.track_limit_seconds},
        # silenceremove=start_periods=1:start_threshold=-70dB,
        # areverse,
        # silenceremove=start_periods=1:start_threshold=-70dB,
        # areverse,
        # dynaudnorm=targetrms=0.3:gausssize=101,
        # afade
        # '''


        filters = 'dynaudnorm=targetrms=0.3:gausssize=101'

        # Remove whitespace and newlines
        filters = ''.join(filters.split())

        with tempfile.NamedTemporaryFile() as temp_file:
            command = ['ffmpeg',
                    '-y',  # overwrite existing file
                    '-hide_banner',
                    '-loglevel', settings.ffmpeg_loglevel,
                    '-i', in_path_abs,
                    '-map_metadata', '-1',  # browser doesn't need metadata
                    '-vn',  # remove video track (also used by album covers, as mjpeg stream)
                    '-filter:a', filters,
                    '-c:a', audio_codec,
                    '-b:a', bit_rate,
                    '-f', container_format,
                    '-vbr', 'on',
                    '-frame_duration', '60',
                    '-ac', str(channels),
                    temp_file.name]
            subprocess.run(command, shell=False, check=True, capture_output=False)

            temp_file.seek(0)
            data = temp_file.read()
            cache.store(cache_key, data)
            return data

    def write_metadata(self, **meta_dict: str):
        """
        Write metadata to file
        """
        with tempfile.NamedTemporaryFile() as temp_file:
            command = [
                'ffmpeg',
                '-y',
                '-hide_banner',
                '-i', self.path.absolute().as_posix(),
                '-codec', 'copy',
            ]
            if self.path.name.endswith('ogg'):
                meta_flag = '-metadata:s' # Set stream metadata
            else:
                meta_flag = '-metadata' # Set container metadata
            for key, value in meta_dict.items():
                command.extend((meta_flag, key + '=' + ('' if value is None else value)))
            command.extend(('-f', self.path.name.split('.')[-1]))
            command.append(temp_file.name)

            log.info('Writing metadata: %s', str(command))
            subprocess.run(command, shell=False, check=True, capture_output=False)
            shutil.copy(temp_file.name, self.path)

            scanner.scan_tracks(self.conn, self.playlist)


    @staticmethod
    def by_relpath(conn: Connection, relpath: str) -> 'Track':
        """
        Find track by relative path
        """
        return Track(conn, relpath, from_relpath(relpath))


@dataclass
class PlaylistStats:
    track_count: int
    total_duration: int
    mean_duration: int
    artist_count: int
    has_title_count: int
    has_album_count: int
    has_album_artist_count: int
    has_year_count: int
    has_artist_count: int
    has_tag_count: int
    most_recent_play: int
    least_recent_play: int
    most_recent_mtime: int

    def __init__(self, conn: Connection, relpath: str):
        row = conn.execute('SELECT COUNT(*), SUM(duration), AVG(duration) FROM track WHERE playlist=?',
                           (relpath,)).fetchone()
        self.track_count, self.total_duration, self.mean_duration = row

        row = conn.execute('''
                           SELECT COUNT(DISTINCT artist)
                           FROM track_artist JOIN track ON track.path=track
                           WHERE playlist=?
                           ''', (relpath,)).fetchone()
        self.artist_count, = row

        row = conn.execute('''
                           SELECT SUM(title IS NOT NULL),
                                  SUM(album IS NOT NULL),
                                  SUM(album_artist IS NOT NULL),
                                  SUM(year IS NOT NULL),
                                  MAX(last_played),
                                  MIN(last_played),
                                  MAX(mtime)
                           FROM track WHERE playlist=?
                           ''', (relpath,)).fetchone()
        self.has_title_count, self.has_album_count, self.has_album_artist_count, \
            self.has_year_count, self.most_recent_play, self.least_recent_play, self.most_recent_mtime = row

        row = conn.execute('''
                           SELECT COUNT(DISTINCT track)
                           FROM track_artist JOIN track ON track.path = track
                           WHERE playlist=?
                           ''', (relpath,)).fetchone()
        self.has_artist_count, = row

        row = conn.execute('''
                           SELECT COUNT(DISTINCT track)
                           FROM track_tag JOIN track ON track.path = track
                           WHERE playlist=?
                           ''', (relpath,)).fetchone()
        self.has_tag_count, = row

    def as_dict(self) -> dict[str, str | int]:
        return {
            'total_duration': self.total_duration,
            'track_count': self.track_count,
            'mean_duration': self.mean_duration,
            'artist_count': self.artist_count,
            'has_title_count': self.has_title_count,
            'has_album_count': self.has_album_count,
            'has_album_artist_count': self.has_album_artist_count,
            'has_year_count': self.has_year_count,
            'has_artist_count': self.has_artist_count,
            'has_tag_count': self.has_tag_count,
            'most_recent_play': self.most_recent_play,
            'least_recent_play': self.least_recent_play,
            'most_recent_mtime': self.most_recent_mtime,
        }

@dataclass
class Playlist:

    conn: Connection
    relpath: str
    path: Path
    name: str
    track_count: int

    def choose_track(self, tag_mode: Optional[Literal['allow', 'deny']], tags: Optional[list[str]]) -> Track:
        """
        Randomly choose a track from this playlist directory
        Args:
            tag_mode: 'allow' or 'deny'
            tags: List of tags
        Returns: Track object
        """
        random_choices = max(5, min(100, self.track_count // 2))

        query = """
                SELECT track.path, last_played
                FROM track
                WHERE track.playlist=?
                """
        params = [self.relpath]

        track_tags_query = 'SELECT tag FROM track_tag WHERE track = track.path'
        if tag_mode == 'allow':
            assert tags is not None
            query += ' AND (' + ' OR '.join(len(tags) * [f'? IN ({track_tags_query})']) + ')'
            params.extend(tags)
        elif tag_mode == 'deny':
            assert tags is not None
            query += ' AND (' + ' AND '.join(len(tags) * [f'? NOT IN ({track_tags_query})']) + ')'
            params.extend(tags)

        query += ' ORDER BY RANDOM()'
        query += f' LIMIT {random_choices}'

        # From randomly ordered tracks, choose one that was last played longest ago
        query = 'SELECT * FROM (' + query + ') ORDER BY last_played ASC LIMIT 1'

        track, last_played = self.conn.execute(query, params).fetchone()

        current_timestamp = int(datetime.now().timestamp())
        if last_played == 0:
            log.info('Chosen track: %s (never played)', track)
        else:
            hours_ago = (current_timestamp - last_played) / 3600
            log.info('Chosen track: %s (last played %.2f hours ago)', track, hours_ago)

        self.conn.execute('UPDATE track SET last_played = ? WHERE path=?', (current_timestamp, track))

        return Track.by_relpath(self.conn, track)

    def tracks(self) -> list[Track]:
        """
        Get all tracks in this playlist as a list of Track objects
        """
        rows = self.conn.execute('SELECT path FROM track WHERE playlist=?', (self.relpath,)).fetchall()
        return [Track.by_relpath(self.conn, row[0]) for row in rows]

    def download(self, url: str) -> CompletedProcess:
        """
        Start a download using yt-dlp
        Args:
            url: URL to download
        Returns: CompletedProcess object
        """
        return subprocess.run(['yt-dlp',
                               '--no-progress',
                               '-f', 'bestaudio',
                               '--remux-video', 'webm>ogg/mp3>mp3/mka',
                               '--add-metadata',
                               '--no-playlist',
                               '--paths', 'temp:/tmp',
                               url],
                              shell=False,
                              check=False,  # No exception on non-zero exit code
                              cwd=self.path,
                              capture_output=True,
                              text=True)

    def has_write_permission(self, user: User) -> bool:
        """
        Check if user is allowed to modify files in a playlist.
        Args:
            user
        Returns: boolean
        """
        if user.admin:
            return True

        row = self.conn.execute('SELECT write FROM user_playlist WHERE playlist=? AND user=?',
                                (self.relpath, user.user_id)).fetchone()

        if row is None:
            return False

        return row[0]

    def stats(self) -> PlaylistStats:
        return PlaylistStats(self.conn, self.relpath)

    @staticmethod
    def from_path(conn: Connection, path: Path) -> 'Playlist':
        """
        Get parent playlist for a path
        Args:
            conn: Database connection
            path: Any (nested) path
        Returns: Playlist object
        """
        relpath = to_relpath(path)
        try:
            dir_name = relpath[:relpath.index('/')]
        except ValueError:  # No slash found
            dir_name = relpath
        name, = conn.execute('SELECT name FROM playlist WHERE path=?',
                             (dir_name,)).fetchone()
        track_count = conn.execute('SELECT COUNT(*) FROM track WHERE playlist=?',
                                (dir_name,)).fetchone()[0]
        return Playlist(conn, dir_name, from_relpath(dir_name), name, track_count)


def playlist(conn: Connection, dir_name: str) -> Playlist:
    """
    Get playlist object from the name of a music directory, using information from the database.
    Args:
        dir_name: Name of directory
    Returns: Playlist instance
    """
    path = from_relpath(dir_name)
    row = conn.execute('SELECT name FROM playlist WHERE path=?',
                        (dir_name,)).fetchone()
    if row is None:
        raise ValueError('Playlist does not exist: ' + dir_name)
    name, = row
    track_count = conn.execute('SELECT COUNT(*) FROM track WHERE playlist=?',
                                (dir_name,)).fetchone()[0]
    return Playlist(conn, dir_name, path, name, track_count)

def playlists(conn: Connection) -> list[Playlist]:
    """
    List playlists
    Returns: List of Playlist objects
    """

    rows = conn.execute('SELECT path FROM playlist').fetchall()
    return [playlist(conn, row[0]) for row in rows]
