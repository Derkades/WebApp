from pathlib import Path
from typing import List, Iterator
from datetime import datetime
import random
import subprocess
from subprocess import CompletedProcess
import logging

import cache
from metadata import Metadata
import settings
from keyval import conn as redis


music_base_dir = Path(settings.music_dir).absolute()
log = logging.getLogger('app.music')


MUSIC_EXTENSIONS = [
    'mp3',
    'flac',
    'ogg',
    'webm',
    'mkv',
    'wma',
    'm4a',
]


class Track:

    def __init__(self, path: Path):
        self.path = path

        # Prevent directory traversal
        if not path.is_relative_to(music_base_dir):
            raise Exception()

    def relpath(self) -> str:
        """
        Returns: Track path, excluding base directory
        """
        return self.path.absolute().as_posix()[len(music_base_dir.as_posix())+1:]

    def metadata(self) -> Metadata:
        """
        Get track metadata using ffmpeg
        Returns: Metadata object
        """
        return Metadata(self.path)

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

        filters = '''
        atrim=0:600,
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
        subprocess.run(command,
                       shell=False,
                       check=True,
                       capture_output=False)

        cache_object.update_checksum()
        cached_data = cache_object.retrieve()

        if cached_data is None:
            raise ValueError("cached data should not be null, we've just written to it")

        return cached_data

    @staticmethod
    def by_relpath(relpath: str) -> 'Track':
        """
        Find track by relative path
        """
        return Track(Path(music_base_dir, relpath))


class Playlist:

    def __init__(self, dir_name: str, display_name: str, is_guest: bool):
        self.music_dir = Path(music_base_dir, dir_name)
        self.dir_name = dir_name
        self.display_name = display_name
        self.is_guest = is_guest

    def track_paths(self) -> Iterator[Path]:
        """
        Scan playlist directory recursively for tracks
        Returns: Paths iterator
        """
        for ext in MUSIC_EXTENSIONS:
            for path in self.music_dir.glob('**/*.' + ext):
                yield path

    def choose_track(self, choices=20) -> Track:
        """
        Randomly choose a track from this playlist directory
        Returns: Track name
        """
        tracks = list(self.track_paths())
        current_timestamp = int(datetime.now().timestamp())

        # Randomly choose some amount of tracks, then pick the track that was played the longest ago

        best_track = None
        best_time = None

        for track in random.choices(tracks, k=choices):
            last_played_b = redis.get('last_played_' + track.as_posix())

            if last_played_b is None:
                best_track = track
                best_time = 0
                break

            last_played = int(last_played_b.decode())

            if best_time is None or last_played < best_time:
                best_track = track
                best_time = last_played

        if best_track is None:
            raise ValueError()

        if best_time == 0:
            log.info('Chosen track: %s (never played)', best_track)
        else:
            hours_ago = (current_timestamp - best_time) / 3600
            log.info('Chosen track: %s (last played %.2f hours ago)', best_track, hours_ago)

        redis.set('last_played_' + best_track.as_posix(), str(current_timestamp).encode())

        return Track(best_track)

    def count_tracks(self) -> int:
        """
        Returns: Number of tracks in this playlists's music directory
        """
        return sum(1 for _d in self.track_paths())

    def has_music(self) -> bool:
        """
        Returns: Whether this playlist contains at least one music file
        """
        try:
            next(self.track_paths())
            return True
        except StopIteration:
            return False

    def tracks(self) -> List[Track]:
        """
        Get all tracks in this playlist as a list of Track objects
        """
        return [Track(entry) for entry in self.track_paths()]

    def search_tracks(self, query: str, limit: int = 3) -> List[Track]:
        """
        Get list of tracks matching search query
        Parameters:
            query: Search query
            limit: Maximum number of results
        Returns: List of Track objects
        """
        # TODO levenshtein distance?
        results: List[Track] = []

        for path in self.track_paths():
            if len(results) > limit:
                break
            if query.lower() in path.name.lower():
                results.append(Track(path))

        return results

    def download(self, url: str) -> CompletedProcess:
        """
        Start a download using yt-dlp
        Parameters:
            url: URL to download
        Returns: CompletedProcess object
        """
        return subprocess.run(['yt-dlp',
                               '--no-progress',
                               '-f', 'bestaudio',
                               '--remux-video', 'webm>ogg/mp3>mp3/mka',
                               '--add-metadata',
                               url],
                              shell=False,
                              check=False,  # No exception on non-zero exit code
                              cwd=self.music_dir,
                              capture_output=True,
                              text=True)

    @staticmethod
    def by_dir_name(dir_name: str) -> 'Playlist':
        """
        Get playlist object from the name of a music directory.
        Parameters:
            dir_name: Name of directory
        Returns: Playlist instance
        """
        if dir_name.startswith('Guest-'):
            return Playlist(dir_name, dir_name[6:], True)
        else:
            return Playlist(dir_name, dir_name, False)

    @staticmethod
    def get_main() -> List['Playlist']:
        """
        Returns: List of Playlist objects for all Raphson members (CB, DK, JK)
        """
        playlists = []
        for music_dir in Path(music_base_dir).iterdir():
            if not music_dir.name.startswith('Guest-'):
                playlist = Playlist(music_dir.name, music_dir.name, False)
                if playlist.has_music():
                    playlists.append(playlist)
        return playlists

    @staticmethod
    def get_guests() -> List['Playlist']:
        """
        Returns: List of Playlist objects for guests, generated dynamically from
                 directory names
        """
        playlists = []
        for music_dir in Path(music_base_dir).iterdir():
            if music_dir.name.startswith('Guest-'):
                playlist = Playlist(music_dir.name, music_dir.name[6:], True)
                if playlist.has_music():
                    playlists.append(playlist)
        return playlists

    @staticmethod
    def get_all() -> List['Playlist']:
        """
        Returns: Concatenation of get_main() and get_guests()
        """
        return [*Playlist.get_main(), *Playlist.get_guests()]
