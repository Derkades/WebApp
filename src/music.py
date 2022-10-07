from pathlib import Path
from typing import List, Iterator, Optional, Dict
from datetime import datetime
import subprocess
from subprocess import CompletedProcess
import logging
import tempfile
import shutil

import cache
import db
import metadata
import settings


log = logging.getLogger('app.music')


MUSIC_EXTENSIONS = [
    'mp3',
    'flac',
    'ogg',
    'webm',
    'mkv',
    'wma',
    'm4a',
    'wav',
]


def to_relpath(path: Path) -> str:
    """
    Returns: Relative path as string, excluding base music directory
    """
    return path.absolute().as_posix()[len(Path(settings.music_dir).absolute().as_posix())+1:]


def scan_music(path) -> Iterator[Path]:
    """
    Scan playlist directory recursively for tracks
    Returns: Paths iterator
    """
    for ext in MUSIC_EXTENSIONS:
        for track_path in path.glob('**/*.' + ext):
            yield track_path


class Track:

    def __init__(self, relpath: str):
        self.relpath = relpath
        self.path = Path(settings.music_dir, relpath)

        # Prevent directory traversal
        if not self.path.is_relative_to(Path(settings.music_dir)):
            raise Exception()

    def metadata(self):
        """
        Returns: Cached metadata for this track, as a Metadata object
        """
        return metadata.cached(self.relpath)

    def transcoded_audio(self, quality) -> bytes:
        """
        Normalize and compress audio using ffmpeg
        Returns: Compressed audio bytes
        """

        if quality == 'verylow':
            bitrate = '32k'
            channels = 1
            samplerate = 24000
        elif quality == 'low':
            bitrate = '64k'
            channels = 2
            samplerate = 48000
        elif quality == 'high':
            bitrate = '96k'
            channels = 2
            samplerate = 48000
        else:
            raise ValueError('Invalid quality', quality)

        in_path_abs = self.path.absolute().as_posix()

        cache_object = cache.get('transcoded audio', in_path_abs + bitrate)
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

        filters = f'''
        atrim=0:{settings.track_limit_seconds},
        silenceremove=start_periods=1:start_threshold=-70dB,
        areverse,
        silenceremove=start_periods=1:start_threshold=-70dB,
        areverse,
        dynaudnorm=targetrms=0.3:gausssize=101,
        afade
        '''

        # Remove whitespace and newlines
        filters = ''.join(filters.split())

        command = ['ffmpeg',
                '-y',  # overwrite existing file
                '-hide_banner',
                '-loglevel', settings.ffmpeg_loglevel,
                '-i', in_path_abs,
                '-map_metadata', '-1',  # browser heeft metadata niet nodig
                '-filter:a', filters,
                '-ar', str(samplerate),
                '-c:a', 'libopus',
                '-b:a', bitrate,
                '-f', 'opus',
                '-vbr', 'on',
                '-frame_duration', '60',
                '-ac', str(channels),
                cache_object.data_path.absolute().as_posix()]
        subprocess.run(command, shell=False, check=True, capture_output=False)

        cached_data = cache_object.retrieve_overwrite_checksum()

        return cached_data

    def write_metadata(self, meta_dict: Dict[str, str]):
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
            for key, value in meta_dict.items():
                command.extend(('-metadata', key + '=' + ('' if value is None else value)))
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
        return Track(relpath)


class Playlist:

    def __init__(self, path: Path):
        self.path = path
        self.relpath = to_relpath(path)
        with db.get() as conn:
            row = conn.execute('SELECT name, guest FROM playlist WHERE path=?',
                               (self.relpath,)).fetchone()
            self.name, self.guest = row
            self.track_count = conn.execute('SELECT COUNT(*) FROM track WHERE playlist=?',
                                            (self.relpath,)).fetchone()[0]

    def choose_track(self, tag_mode, tags: List[str]) -> Track:
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
        query += ' LIMIT 50'

        # From randomly ordered 20 tracks, choose one that was last played longest ago
        query = 'SELECT * FROM (' + query + ') ORDER BY last_played ASC LIMIT 1'

        with db.get() as conn:
            track, last_played = conn.execute(query, params).fetchone()

            current_timestamp = int(datetime.now().timestamp())
            if last_played == 0:
                log.info('Chosen track: %s (never played)', track)
            else:
                hours_ago = (current_timestamp - last_played) / 3600
                log.info('Chosen track: %s (last played %.2f hours ago)', track, hours_ago)

            conn.execute('UPDATE track_persistent SET last_played = ? WHERE path=?', (current_timestamp, track))

        return Track(track)

    def tracks(self, *args, **kwargs) -> List[Track]:
        """
        Get all tracks in this playlist as a list of Track objects
        """
        with db.get() as conn:
            rows = conn.execute('SELECT path FROM track WHERE playlist=?', (self.relpath,)).fetchall()
            return [Track(row[0]) for row in rows]

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


def playlist(dir_name: str) -> Playlist:
    """
    Get playlist object from the name of a music directory.
    Args:
        dir_name: Name of directory
    Returns: Playlist instance
    """
    return Playlist(Path(settings.music_dir, dir_name))

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
        return [Playlist(Path(settings.music_dir, row[0])) for row in rows]
