from pathlib import Path
from typing import List, Iterator, Optional, Dict
from datetime import datetime
import subprocess
from subprocess import CompletedProcess
import logging
import tempfile
import shutil
from dataclasses import dataclass

import cache
import db
import metadata
import settings


log = logging.getLogger('app.music')


MUSIC_EXTENSIONS = [
    '.mp3',
    '.flac',
    '.ogg',
    '.webm',
    '.mkv',
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


def scan_music(path) -> Iterator[Path]:
    """
    Scan playlist directory recursively for tracks
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

    relpath: str
    path: Path

    def metadata(self):
        """
        Returns: Cached metadata for this track, as a Metadata object
        """
        return metadata.cached(self.relpath)

    def transcoded_audio(self, quality, fruit) -> bytes:
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

        cache_object = cache.get('audio2', container_format + in_path_abs + bit_rate)
        cached_data = cache_object.retrieve()
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
                cache_object.data_path.absolute().as_posix()]
        subprocess.run(command, shell=False, check=True, capture_output=False)

        cached_data = cache_object.retrieve_overwrite_checksum()

        return cached_data

    def write_metadata(self, **meta_dict: Dict[str, str]):
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

            self.update_database()

    def update_database(self):
        """
        Update metadata in database for this track only
        """
        meta = metadata.probe(self.path)

        with db.get() as conn:
            conn.execute('UPDATE track SET title=?, album=?, album_artist=?, year=? WHERE path=?',
                        (meta.title, meta.album, meta.album_artist, meta.year, self.relpath))

            conn.execute('DELETE FROM track_artist WHERE track=?', (self.relpath,))
            conn.execute('DELETE FROM track_tag WHERE track=?', (self.relpath,))

            if meta.artists is not None:
                artist_insert = [(self.relpath, artist) for artist in meta.artists]
                conn.executemany(('INSERT INTO track_artist (track, artist) VALUES (?, ?)'), artist_insert)

            tag_insert = [(self.relpath, tag) for tag in meta.tags]
            conn.executemany(('INSERT INTO track_tag (track, tag) VALUES (?, ?)'), tag_insert)

    @staticmethod
    def by_relpath(relpath: str) -> 'Track':
        """
        Find track by relative path
        """
        return Track(relpath, from_relpath(relpath))


@dataclass
class Playlist:

    relpath: str
    path: Path
    name: str
    guest: bool
    track_count: int

    def choose_track(self, tag_mode, tags: List[str], reuse_conn = None) -> Track:
        """
        Randomly choose a track from this playlist directory
        Args:
            tag_mode: 'allow' or 'deny'
            tags: List of tags
        Returns: Track object
        """
        query = """
                SELECT track.path, last_played
                FROM track
                INNER JOIN track_persistent ON track.path = track_persistent.path
                WHERE track.playlist=?
                """
        params = [self.relpath]
        if tag_mode == 'allow':
            query += ' AND (' + ' OR '.join(len(tags) * ['? IN (SELECT tag FROM track_tag WHERE track = track.path)']) + ')'
            params.extend(tags)
        elif tag_mode == 'deny':
            query += ' AND (' + ' AND '.join(len(tags) * ['? NOT IN (SELECT tag FROM track_tag WHERE track = track.path)']) + ')'
            params.extend(tags)

        query += ' ORDER BY RANDOM()'
        query += ' LIMIT 10'

        # From randomly ordered tracks, choose one that was last played longest ago
        query = 'SELECT * FROM (' + query + ') ORDER BY last_played ASC LIMIT 1'

        with db.get() if reuse_conn is None else reuse_conn as conn:
            track, last_played = conn.execute(query, params).fetchone()

            current_timestamp = int(datetime.now().timestamp())
            if last_played == 0:
                log.info('Chosen track: %s (never played)', track)
            else:
                hours_ago = (current_timestamp - last_played) / 3600
                log.info('Chosen track: %s (last played %.2f hours ago)', track, hours_ago)

            conn.execute('UPDATE track_persistent SET last_played = ? WHERE path=?', (current_timestamp, track))

        return Track.by_relpath(track)

    def tracks(self) -> List[Track]:
        """
        Get all tracks in this playlist as a list of Track objects
        """
        with db.get() as conn:
            rows = conn.execute('SELECT path FROM track WHERE playlist=?', (self.relpath,)).fetchall()
            return [Track.by_relpath(row[0]) for row in rows]

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


def playlist(dir_name: str, reused_conn = None) -> Playlist:
    """
    Get playlist object from the name of a music directory, using information from the database.
    Args:
        dir_name: Name of directory
    Returns: Playlist instance
    """
    path = from_relpath(dir_name)
    with db.get() if reused_conn is None else reused_conn as conn:
        row = conn.execute('SELECT name, guest FROM playlist WHERE path=?',
                           (dir_name,)).fetchone()
        if row is None:
            raise ValueError('Playlist does not exist: ' + dir_name)
        name, guest = row
        track_count = conn.execute('SELECT COUNT(*) FROM track WHERE playlist=?',
                                   (dir_name,)).fetchone()[0]
    return Playlist(dir_name, path, name, guest, track_count)

def playlists(guest: Optional[bool] = None) -> List[Playlist]:
    """
    List playlists
    Args:
        guest: True to list only list guest playlist, False for non-guest
               playlists, None for both.
    Returns: List of Playlist objects
    """
    if guest is None:
        query = 'SELECT path FROM playlist'
    elif guest is True:
        query = 'SELECT path FROM playlist WHERE guest=1'
    elif guest is False:
        query = 'SELECT path FROM playlist WHERE guest=0'
    else:
        raise ValueError()

    with db.get() as conn:
        rows = conn.execute(query).fetchall()
        return [playlist(row[0], conn) for row in rows]
