from __future__ import annotations
from pathlib import Path
from typing import Iterator, Literal, Optional, TYPE_CHECKING
from datetime import datetime
import subprocess
from subprocess import CompletedProcess
import logging
import tempfile
import shutil
from dataclasses import dataclass
from sqlite3 import Connection
from enum import Enum
import random

from auth import User
import cache
import metadata
import settings
import scanner
import bing
import musicbrainz
import reddit
import image
from image import ImageFormat, ImageQuality

if TYPE_CHECKING:
    from metadata import Metadata


log = logging.getLogger('app.music')


# .wma is intentionally missing, ffmpeg support seems to be flaky
MUSIC_EXTENSIONS = [
    '.mp3',
    '.flac',
    '.ogg',
    '.webm',
    '.mkv',
    '.mka',
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


def is_trashed(path: Path) -> bool:
    """
    Returns: Whether this file or directory is trashed, by checking for the
    trash prefix in all path parts.
    """
    for part in path.parts:
        if part.startswith('.trash.'):
            return True
    return False


def is_music_file(path: Path) -> bool:
    """
    Returns: Whether the provided path is a music file, by checking its extension
    """
    for ext in MUSIC_EXTENSIONS:
        if path.name.endswith(ext):
            return True
    return False


def list_tracks_recursively(path) -> Iterator[Path]:
    """
    Scan directory for tracks, recursively
    Args:
        path: Directory Path
    Returns: Paths iterator
    """
    for ext in MUSIC_EXTENSIONS:
        for track_path in path.glob('**/*' + ext):
            if not is_trashed(track_path):
                yield track_path


class AudioType(Enum):
    """
    Opus audio in WebM container, for music player streaming.
    """
    WEBM_OPUS_HIGH = 0

    """
    Opus audio in WebM container, for music player streaming with lower data
    usage.
    """
    WEBM_OPUS_LOW = 1

    """
    Special AAC audio in MP4 container for Safari. Apple press releases
    say Opus in WebM are supported, but that does not seem to be the case.
    caniuse.com claims Opus in CAF container is supported, but doesn't seem
    to work either (tested using Safari 16.0 in macOS Monterey VM).
    We have to use the less-efficient AAC codec at a higher bit rate.
    """
    MP4_AAC = 2

    """
    MP3 files with metadata (including cover art), for use with external
    music player applications and devices Uses the MP3 format for broadest
    compatibility.
    """
    MP3_WITH_METADATA = 3


@dataclass
class Track:
    conn: Connection
    relpath: str
    path: Path
    mtime: int

    @property
    def playlist(self) -> str:
        """
        Returns: Part of track path before first slash
        """
        return self.relpath[:self.relpath.index('/')]

    def metadata(self) -> Metadata:
        """
        Returns: Cached metadata for this track, as a Metadata object
        """
        return metadata.cached(self.conn, self.relpath)

    def get_cover(self, meme: bool) -> Optional[bytes]:
        """
        Find album cover using MusicBrainz or Bing.
        Parameters:
            meta: Track metadata
        Returns: Album cover image bytes, or None if MusicBrainz nor bing found an image.
        """
        meta = self.metadata()

        log.info('Finding cover for: %s', meta.relpath)

        if meme:
            title = meta.title if meta.title else meta.display_title()
            if '-' in title:
                title = title[title.index('-')+1:]

            if random.random() > 0.4:
                image_bytes = reddit.get_image(title)
                if image_bytes:
                    return image_bytes

            image_bytes = bing.image_search(title + ' meme')
            if image_bytes:
                return image_bytes

        # Try MusicBrainz first
        mb_query = meta.album_release_query()
        if image_bytes := musicbrainz.get_cover(mb_query):
            return image_bytes

        # Otherwise try bing
        for query in meta.album_search_queries():
            if image_bytes := bing.image_search(query):
                return image_bytes

        log.info('No suitable cover found')
        return None

    def get_cover_thumbnail(self, meme: bool, img_format: ImageFormat, img_quality: ImageQuality) -> bytes:
        """
        Get thumbnail version of album cover art
        Args:
            meme: Whether to retrieve a meme instead of the proper album cover
            img_format: Image format
            img_quality: Image quality level
        Returns: Thumbnail bytes
        """
        cache_key = self.relpath + str(self.mtime) + str(meme)

        def get_img_function():
            return self.get_cover(meme)

        square = not meme
        return image.thumbnail(get_img_function, cache_key, img_format, img_quality, square)

    def _get_ffmpeg_metadata_options(self):
        meta = self.metadata()
        metadata_options = []
        if meta.album is not None:
            metadata_options.extend(('-metadata', 'album=' + meta.album))
        if meta.artists is not None:
            metadata_options.extend(('-metadata', 'artist=' + metadata.join_meta_list(meta.artists)))
        if meta.title is not None:
            metadata_options.extend(('-metadata', 'title=' + meta.title))
        if meta.year is not None:
            metadata_options.extend(('-metadata', 'date=' + str(meta.year)))
        if meta.album_artist is not None:
            metadata_options.extend(('-metadata', 'album_artist=' + meta.album_artist))
        if meta.track_number is not None:
            metadata_options.extend(('-metadata', 'track=' + str(meta.track_number)))
        metadata_options.extend(('-metadata', 'genre=' + metadata.join_meta_list(meta.tags)))
        return metadata_options

    def transcoded_audio(self,
                         audio_type: AudioType) -> bytes:
        """
        Normalize and compress audio using ffmpeg
        Returns: Compressed audio bytes
        """

        cache_key = 'audio' + str(audio_type) + self.relpath + str(self.mtime)

        cached_data = cache.retrieve(cache_key)
        if cached_data is not None:
            log.info('Returning cached audio')
            return cached_data

        if audio_type in {AudioType.WEBM_OPUS_HIGH, AudioType.WEBM_OPUS_LOW}:
            input_options = ['-map_metadata', '-1']
            bit_rate = '128k' if audio_type == AudioType.WEBM_OPUS_HIGH else '64k'
            audio_options = ['-f', 'webm',
                             '-c:a', 'libopus',
                             '-b:a', bit_rate,
                             '-vbr', 'on',
                             '-frame_duration', '60',
                             '-vn']  # remove video track (and album covers)
        elif audio_type == AudioType.MP4_AAC:
            input_options = ['-map_metadata', '-1']
            audio_options = ['-f', 'mp4',
                             '-c:a', 'aac',
                             '-b:a', '192k',
                             '-vn']  # remove video track (and album covers)
        elif audio_type == AudioType.MP3_WITH_METADATA:
            cover = self.get_cover_thumbnail(False, ImageFormat.JPEG, ImageQuality.HIGH)
            # Write cover to temp file so ffmpeg can read it
            cover_temp_file = tempfile.NamedTemporaryFile('wb')
            cover_temp_file.write(cover)

            input_options = ['-i', cover_temp_file.name,  # Add album cover
                             '-map', '0:0',
                             '-map', '1:0',  # map album image to audio stream
                             '-id3v2_version', '3',
                             '-metadata:s:v', 'title=Album cover',
                             '-metadata:s:v', 'comment=Cover (front)']

            input_options.extend(['-map_metadata', '-1'])  # Discard original metadata
            metadata_options = self._get_ffmpeg_metadata_options()
            input_options.extend(metadata_options)  # Set new metadata

            audio_options = ['-f', 'mp3',
                             '-c:a', 'libmp3lame',
                             '-c:v', 'copy',  # Leave cover as JPEG, don't re-encode as PNG
                             '-q:a', '5']  # VBR ~130kbps (usually 120-150kbps), close to transparent

        filters = 'dynaudnorm=targetrms=0.3:gausssize=101'

        with tempfile.NamedTemporaryFile() as temp_file:
            command = ['ffmpeg',
                    '-y',  # overwrite existing file
                    '-hide_banner',
                    '-loglevel', settings.ffmpeg_loglevel,
                    '-i', self.path.absolute().as_posix(),
                    *input_options,
                    '-filter:a', filters,
                    *audio_options,
                    '-ac', '2',
                    temp_file.name]
            subprocess.run(command, shell=False, check=True, capture_output=False)

            temp_file.seek(0)
            data = temp_file.read()

        if audio_type == AudioType.MP3_WITH_METADATA:
            cover_temp_file.close()

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

            extension = self.path.name.split('.')[-1]
            if extension == 'm4a':
                ffmpeg_format = 'ipod'
            elif extension == 'mka':
                ffmpeg_format = 'matroska'
            else:
                ffmpeg_format = extension
            command.extend(('-f', ffmpeg_format))

            command.append(temp_file.name)

            log.info('Writing metadata: %s', str(command))
            subprocess.run(command, shell=False, check=True, capture_output=False)
            shutil.copy(temp_file.name, self.path)

            scanner.scan_tracks(self.conn, self.playlist)


    @staticmethod
    def by_relpath(conn: Connection, relpath: str) -> 'Track' | None:
        """
        Find track by relative path
        """
        row = conn.execute('SELECT mtime FROM track WHERE path=?',
                              (relpath,)).fetchone()
        if row:
            mtime, = row
            return Track(conn, relpath, from_relpath(relpath), mtime)

        return None


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

        (self.has_title_count,
         self.has_album_count,
         self.has_album_artist_count,
         self.has_year_count,
         self.most_recent_play,
         self.least_recent_play,
         self.most_recent_mtime
         ) = conn.execute('''
                          SELECT SUM(title IS NOT NULL),
                                 SUM(album IS NOT NULL),
                                 SUM(album_artist IS NOT NULL),
                                 SUM(year IS NOT NULL),
                                 MAX(last_played),
                                 MIN(last_played),
                                 MAX(mtime)
                          FROM track WHERE playlist=?
                          ''', (relpath,)).fetchone()


        (self.has_artist_count,
         ) = conn.execute('''
                          SELECT COUNT(DISTINCT track)
                          FROM track_artist JOIN track ON track.path = track
                          WHERE playlist=?
                          ''', (relpath,)).fetchone()

        (self.has_tag_count,
         ) = conn.execute('''
                          SELECT COUNT(DISTINCT track)
                          FROM track_tag JOIN track ON track.path = track
                          WHERE playlist=?
                          ''', (relpath,)).fetchone()


@dataclass
class Playlist:

    conn: Connection
    name: str
    path: Path
    track_count: int

    def choose_track(self, user: Optional[User], tag_mode: Optional[Literal['allow', 'deny']], tags: Optional[list[str]]) -> Track:
        """
        Randomly choose a track from this playlist directory
        Args:
            tag_mode: 'allow' or 'deny'
            tags: List of tags
        Returns: Track object
        """
        random_choices = max(5, min(50, self.track_count // 6))

        query = """
                SELECT track.path, last_played
                FROM track
                WHERE track.playlist=?
                """
        params: list[str | int] = [self.name]

        if user is not None:
            query += ' AND path NOT IN (SELECT track FROM never_play WHERE user = ?)'
            params.append(user.user_id)

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
        rows = self.conn.execute('SELECT path FROM track WHERE playlist=?',
                                 (self.name,)).fetchall()
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
                                (self.name, user.user_id)).fetchone()

        if row is None:
            return False

        return row[0]

    def stats(self) -> PlaylistStats:
        """
        Returns: PlaylistStats
        """
        return PlaylistStats(self.conn, self.name)

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
            name = relpath[:relpath.index('/')]
        except ValueError:  # No slash found
            name = relpath
        track_count = conn.execute('SELECT COUNT(*) FROM track WHERE playlist=?',
                                (name,)).fetchone()[0]
        return Playlist(conn, name, from_relpath(name), track_count)


@dataclass
class UserPlaylist(Playlist):
    write: bool
    favorite: bool


def playlist(conn: Connection, name: str) -> Playlist:
    """
    Get playlist object from the name of a music directory, using information from the database.
    Args:
        name: Name of directory
    Returns: Playlist instance
    """
    row = conn.execute('''
                        SELECT (SELECT COUNT(*) FROM track WHERE playlist=playlist.path)
                        FROM playlist
                        WHERE path=?
                        ORDER BY path ASC
                        ''', (name,)).fetchone()
    track_count, = row
    return Playlist(conn, name, from_relpath(name), track_count)


def user_playlist(conn: Connection, name: str, user_id: int) -> UserPlaylist:
    """
    Get list of favorite playlists
    Args:
        conn
        user_id
    Returns: List of UserPlaylist objects
    """
    # TODO merge to single query when bookworm is released, with a version of sqlite3 supporting outer join

    row1 = conn.execute('''
                        SELECT (SELECT COUNT(*) FROM track WHERE playlist=playlist.path)
                        FROM playlist
                        WHERE path=?
                        ''', (name,)).fetchone()
    row2 = conn.execute('''
                        SELECT write, favorite
                        FROM user_playlist
                        WHERE user=? and playlist=?
                        ''', (user_id, name)).fetchone()

    track_count, = row1

    if row2 is not None:
        write = row2[0] == 1
        favorite = row2[1] == 1
    else:
        write = False
        favorite = False

    return UserPlaylist(conn, name, from_relpath(name), track_count, write, favorite)


def playlists(conn: Connection) -> list[Playlist]:
    """
    List playlists
    Returns: List of Playlist objects
    """
    rows = conn.execute('''
                        SELECT path, (SELECT COUNT(*) FROM track WHERE playlist=playlist.path)
                        FROM playlist
                        ORDER BY path ASC
                        ''')
    return [Playlist(conn, name, from_relpath(name), track_count)
            for name, track_count in rows]


def user_playlists(conn: Connection, user_id: int) -> list[UserPlaylist]:
    playlist_list = []
    # TODO merge to single query when bookworm is released, with a version of sqlite3 supporting outer join

    rows1 = conn.execute('''
                         SELECT playlist, write, favorite FROM user_playlist WHERE user=?
                         ORDER BY favorite DESC, write DESC, playlist ASC
                         ''', (user_id,)).fetchall()
    rows2 = conn.execute('''
                         SELECT path, (SELECT COUNT(*) FROM track WHERE playlist=playlist.path)
                         FROM playlist
                         ORDER BY path ASC
                         ''').fetchall()

    names: set[str] = set()
    for name, write, favorite in rows1:
        for name2, track_count in rows2:
            if name == name2:
                names.add(name)
                playlist_list.append(UserPlaylist(conn, name, from_relpath(name), track_count, write == 1, favorite == 1))
                break

    for name, track_count in rows2:
        if name in names:
            continue
        playlist_list.append(UserPlaylist(conn, name, from_relpath(name), track_count, False, False))

    return playlist_list
