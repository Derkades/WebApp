from __future__ import annotations

import logging
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from sqlite3 import Connection
from typing import TYPE_CHECKING, Iterator, Literal, Optional
from subprocess import CalledProcessError

from app import (bing, cache, image, metadata, musicbrainz, reddit, scanner,
                 settings)
from app.auth import User
from app.image import ImageQuality

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
        raise ValueError('Relative path must not start with /')
    path = Path(settings.music_dir, relpath).absolute()
    if not path.is_relative_to(Path(settings.music_dir)):
        raise ValueError('Must not go outside of music base directory')
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


def list_tracks_recursively(path: Path) -> Iterator[Path]:
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


def sort_artists(artists: Optional[list[str]], album_artist: Optional[str]) -> Optional[list[str]]:
    """
    Move album artist to start of artist list
    """
    if artists and album_artist and album_artist in artists:
        artists.remove(album_artist)
        return [album_artist] + artists

    return artists


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

    def _get_possible_covers(self, meme: bool) -> Iterator[bytes]:
        meta = self.metadata()

        if meme:
            title = meta.title if meta.title else meta.display_title()
            if '-' in title:
                title = title[title.index('-')+1:]

            if random.random() > 0.5:
                image_bytes = reddit.get_image(title)
                if image_bytes:
                    yield image_bytes

            yield from bing.image_search(title + ' meme')

        # Try MusicBrainz first
        if (meta.title or meta.album) and (meta.album_artist or meta.artists):
            album = meta.album if meta.album and not metadata.ignore_album(meta.album) else meta.title
            artist = meta.album_artist if meta.album_artist else ' '.join(meta.artists)  # mypy: disable=arg-type
            if image_bytes := musicbrainz.get_cover(artist, album):
                yield image_bytes
        else:
            log.info('Skip MusicBrainz search, not enough metadata')

        # Otherwise try bing
        for query in meta.album_search_queries():
            yield from bing.image_search(query)

        log.info('No suitable cover found, returning fallback image')
        yield Path('app', 'static', 'raphson.png').read_bytes()


    def get_cover(self, meme: bool, img_quality: ImageQuality) -> Optional[bytes]:
        """
        Find album cover using MusicBrainz or Bing.
        Parameters:
            meta: Track metadata
        Returns: Album cover image bytes, or None if MusicBrainz nor bing found an image.
        """
        general_cache_key =  'cover' + self.relpath + str(self.mtime) + str(meme)
        quality_cache_key = general_cache_key + img_quality.value

        cache_data = cache.retrieve(quality_cache_key)
        if cache_data is not None:
            log.info('Returning cover thumbnail from cache: %s', quality_cache_key)
            return cache_data

        log.info('Cover thumbnail not cached, need to download album cover image')

        for cover_bytes in self._get_possible_covers(meme):
            with tempfile.TemporaryDirectory(prefix='music-cover') as temp_dir:
                input_path = Path(temp_dir, 'input')
                input_path.write_bytes(cover_bytes)

                try:
                    log.info('Generating thumbnails')

                    for quality in ImageQuality:
                        output_path = Path(temp_dir, 'output-' + quality.value)
                        image.webp_thumbnail(input_path, output_path, img_quality, square=not meme)
                        cache.store(general_cache_key + quality.value, output_path.read_bytes())
                except CalledProcessError:
                    log.warning('Failed to generate thumbnail, image is probably corrupt. Trying another image.')
                    continue

            cache_data = cache.retrieve(quality_cache_key)

            if cache_data is None:
                raise ValueError('Should have just been added to cache')

            return cache_data


    def _get_ffmpeg_metadata_options(self) -> list[str]:
        meta = self.metadata()
        metadata_options: list[str] = []
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

    def get_loudnorm_filter(self) -> str:
        """Get ffmpeg loudnorm filter string"""
        return 'loudnorm=I=-16'

        # cache_key = 'loud' + self.relpath + str(self.mtime)
        # cached_data = cache.retrieve(cache_key)
        # if cached_data is not None:
        #     log.info('Returning cached loudness data')
        #     return cached_data.decode()

        # # First phase of 2-phase loudness normalization
        # # http://k.ylo.ph/2016/04/04/loudnorm.html
        # log.info('Measuring loudness...')
        # meas_command = ['ffmpeg',
        #                 '-hide_banner',
        #                 '-i', self.path.absolute().as_posix(),
        #                 '-map', '0:a',
        #                 '-af', 'loudnorm=print_format=json',
        #                 '-f', 'null',
        #                 '-']
        # # Annoyingly, loudnorm outputs to stderr instead of stdout.
        # # Disabling logging also hides the loudnorm output...
        # meas_result = subprocess.run(meas_command, shell=False, capture_output=True, check=False)

        # if meas_result.returncode != 0:
        #     log.warning('FFmpeg exited with exit code %s', meas_result.returncode)
        #     log.warning('--- stdout ---\n%s', meas_result.stdout.decode())
        #     log.warning('--- stderr ---\n%s', meas_result.stderr.decode())
        #     raise RuntimeError()

        # # Manually find the start of loudnorm info json
        # meas_out = meas_result.stderr.decode()

        # meas_json = json.loads(meas_out[meas_out.rindex('Parsed_loudnorm_0')+37:])

        # log.info('Measured integrated loudness: %s', meas_json['input_i'])

        # loudnorm = \
        #     'loudnorm=I=-16:' \
        #     f"measured_I={meas_json['input_i']}:" \
        #     f"measured_TP={meas_json['input_tp']}:" \
        #     f"measured_LRA={meas_json['input_lra']}:" \
        #     f"measured_thresh={meas_json['input_thresh']}:" \
        #     f"offset={meas_json['target_offset']}:" \
        #     'linear=true'

        # cache.store(cache_key, loudnorm.encode(), cache.YEAR)
        # return loudnorm


    def transcoded_audio(self,
                         audio_type: AudioType) -> bytes:
        """
        Normalize and compress audio using ffmpeg
        Returns: Compressed audio bytes
        """
        cache_key = 'audio5' + str(audio_type) + self.relpath + str(self.mtime)

        cached_data = cache.retrieve(cache_key)

        if cached_data is not None:
            log.info('Returning cached audio')
            return cached_data

        loudnorm = self.get_loudnorm_filter()

        input_options = ['-map', '0:a', # only keep audio
                         '-map_metadata', '-1']  # discard metadata

        if audio_type in {AudioType.WEBM_OPUS_HIGH, AudioType.WEBM_OPUS_LOW}:
            bit_rate = '128k' if audio_type == AudioType.WEBM_OPUS_HIGH else '48k'
            audio_options = ['-f', 'webm',
                             '-c:a', 'libopus',
                             '-b:a', bit_rate,
                             '-vbr', 'on',
                             # Higher frame duration offers better compression at the cost of latency
                             '-frame_duration', '60',
                             '-vn']  # remove video track (and album covers)
        elif audio_type == AudioType.MP4_AAC:
            # https://trac.ffmpeg.org/wiki/Encode/AAC
            audio_options = ['-f', 'mp4',
                             '-c:a', 'aac',
                             '-q:a', '3', # 96k-144k
                             # +faststart to allow playback without downloading entire file
                             '-movflags', '+faststart',
                             '-vn']  # remove video track (and album covers)
        # elif audio_type == AudioType.MP3_WITH_METADATA:
        #     # https://trac.ffmpeg.org/wiki/Encode/MP3
        #     cover = self.get_cover_thumbnail(False, ImageFormat.JPEG, ImageQuality.HIGH)
        #     # Write cover to temp file so ffmpeg can read it
        #     cover_temp_file = tempfile.NamedTemporaryFile('wb')  # pylint: disable=consider-using-with
        #     cover_temp_file.write(cover)

        #     input_options = ['-i', cover_temp_file.name,  # Add album cover
        #                      '-map', '0:a', # include audio stream from first input
        #                      '-map', '1:0', # include first stream from second input
        #                      '-id3v2_version', '3',
        #                      '-map_metadata', '-1',  # discard original metadata
        #                      '-metadata:s:v', 'title=Album cover',
        #                      '-metadata:s:v', 'comment=Cover (front)',
        #                      *self._get_ffmpeg_metadata_options()]  # set new metadata

        #     audio_options = ['-f', 'mp3',
        #                      '-c:a', 'libmp3lame',
        #                      '-c:v', 'copy',  # Leave cover as JPEG, don't re-encode as PNG
        #                      '-q:a', '5']  # VBR 128kbps

        with tempfile.NamedTemporaryFile() as temp_output:
            command = ['ffmpeg',
                    '-y',  # overwriting file is required, because the created temp file already exists
                    '-hide_banner',
                    '-nostats',
                    '-loglevel', settings.ffmpeg_loglevel,
                    '-i', self.path.absolute().as_posix(),
                    *input_options,
                    *audio_options,
                    '-t', str(settings.track_limit_seconds),
                    '-ac', '2',
                    '-filter:a', loudnorm,
                    temp_output.name]
            subprocess.run(command, shell=False, check=True)
            audio_data = temp_output.read()

        # if audio_type == AudioType.MP3_WITH_METADATA:
        #     cover_temp_file.close()

        cache.store(cache_key, audio_data, cache.YEAR)
        return audio_data

    def write_metadata(self, **meta_dict: str):
        """
        Write metadata to file
        """
        original_extension = '.' + self.path.name.split('.')[-1]
        with tempfile.NamedTemporaryFile(suffix=original_extension) as temp_file:
            command = [
                'ffmpeg',
                '-y',  # overwriting file is required, because the created temp file already exists
                '-hide_banner',
                '-nostats',
                '-loglevel', settings.ffmpeg_loglevel,
                '-i', self.path.absolute().as_posix(),
                '-codec', 'copy',
            ]

            if original_extension == '.ogg':
                meta_flag = '-metadata:s' # Set stream metadata
            else:
                meta_flag = '-metadata' # Set container metadata

            for key, value in meta_dict.items():
                command.extend((meta_flag, key + '=' + ('' if value is None else value)))

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
    most_recent_choice: int
    least_recent_choice: int
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
         self.most_recent_choice,
         self.least_recent_choice,
         self.most_recent_mtime
         ) = conn.execute('''
                          SELECT SUM(title IS NOT NULL),
                                 SUM(album IS NOT NULL),
                                 SUM(album_artist IS NOT NULL),
                                 SUM(year IS NOT NULL),
                                 MAX(last_chosen),
                                 MIN(last_chosen),
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

    def choose_track(self,
                     user: Optional[User],
                     tag_mode: Optional[Literal['allow', 'deny']] = None,
                     tags: Optional[list[str]] = None) -> Track:
        """
        Randomly choose a track from this playlist directory
        Args:
            tag_mode: 'allow' or 'deny'
            tags: List of tags
        Returns: Track object
        """
        random_choices = max(3, min(10, self.track_count // 6))

        query = """
                SELECT track.path, last_chosen
                FROM track
                WHERE track.playlist=?
                """
        params: list[str | int] = [self.name]

        if user is not None:
            query += ' AND NOT EXISTS (SELECT 1 FROM dislikes WHERE user=? AND track=path)'
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
        query = 'SELECT * FROM (' + query + ') ORDER BY last_chosen ASC LIMIT 1'

        track, last_chosen = self.conn.execute(query, params).fetchone()

        current_timestamp = int(datetime.now().timestamp())
        if last_chosen == 0:
            log.info('Chosen track: %s (never played)', track)
        else:
            hours_ago = (current_timestamp - last_chosen) / 3600
            log.info('Chosen track: %s (last played %.2f hours ago)', track, hours_ago)

        self.conn.execute('UPDATE track SET last_chosen = ? WHERE path=?', (current_timestamp, track))

        track = Track.by_relpath(self.conn, track)
        if track is None:
            raise RuntimeError('Track has just been selected from the database so it must exist')
        return track

    def has_write_permission(self, user: User) -> bool:
        """
        Check if user is allowed to modify files in a playlist.
        Args:
            user
        Returns: boolean
        """
        if user.admin:
            return True

        row = self.conn.execute('SELECT user FROM user_playlist_write WHERE playlist=? AND user=?',
                                (self.name, user.user_id)).fetchone()

        return row is not None

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
    Get playlist by name
    Args:
        conn: Database connection
        name: Name of directory
    Returns: Playlist object
    """
    row = conn.execute('''
                        SELECT (SELECT COUNT(*) FROM track WHERE playlist=playlist.path)
                        FROM playlist
                        WHERE path=?
                        ''', (name,)).fetchone()
    track_count, = row
    return Playlist(conn, name, from_relpath(name), track_count)


def user_playlist(conn: Connection, name: str, user_id: int) -> UserPlaylist:
    """
    Get playlist by name, with user-specific information
    Args:
        conn: Database connection
        name: Playlist name
        user_id
    Returns: UserPlaylist object
    """
    row = conn.execute('''
                       SELECT (SELECT COUNT(*) FROM track WHERE playlist=path),
                              EXISTS(SELECT 1 FROM user_playlist_write WHERE playlist=path AND user=:user) AS write,
                              EXISTS(SELECT 1 FROM user_playlist_favorite WHERE playlist=path AND user=:user) AS favorite
                       FROM playlist
                       WHERE path=:playlist
                       ORDER BY favorite DESC, write DESC, path ASC
                       ''', {'user': user_id, 'playlist': name}).fetchone()
    track_count, write, favorite = row
    return UserPlaylist(conn, name, from_relpath(name), track_count, write == 1, favorite == 1)


def playlists(conn: Connection) -> list[Playlist]:
    """
    List playlists
    Returns: List of Playlist objects
    """
    rows = conn.execute('''
                        SELECT path, (SELECT COUNT(*) FROM track WHERE playlist=playlist.path)
                        FROM playlist
                        ''')
    return [Playlist(conn, name, from_relpath(name), track_count)
            for name, track_count in rows]


def user_playlists(conn: Connection, user_id: int, all_writable=False) -> list[UserPlaylist]:
    """
    List playlists, with user-specific information
    Args:
        conn: Database connection
        user_id
    Returns: List of UserPlaylist objects
    """
    rows = conn.execute('''
                        SELECT path,
                               (SELECT COUNT(*) FROM track WHERE playlist=playlist.path),
                               EXISTS(SELECT 1 FROM user_playlist_write WHERE playlist=path AND user=:user) AS write,
                               EXISTS(SELECT 1 FROM user_playlist_favorite WHERE playlist=path AND user=:user) AS favorite
                        FROM playlist
                        ORDER BY favorite DESC, write DESC, path ASC
                        ''', {'user': user_id})

    return [UserPlaylist(conn, name, from_relpath(name), track_count, write == 1 or all_writable, favorite == 1)
            for name, track_count, write, favorite in rows]
