from pathlib import Path
from typing import List
from datetime import datetime
import os
import random
import subprocess
from subprocess import CompletedProcess
import logging

import cache
from metadata import Metadata
import settings
from keyval import conn as redis


music_base_dir = Path(settings.music_dir)
log = logging.getLogger('app.music')


class Track:

    def __init__(self, path: Path):
        self.path = path

    def name(self) -> str:
        """
        Returns: Full track file name
        """
        return self.path.name

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
        if quality not in {'low', 'high'}:
            raise ValueError('Invalid quality', quality)

        bitrate = settings.opus_bitrate_low if quality == 'low' else settings.opus_bitrate_high

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
                '-c:a', 'libopus',
                '-b:a', bitrate,
                '-f', 'opus',
                '-vbr', 'on',
                '-filter:a', filters,
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


class Person:

    def __init__(self, dir_name: str, display_name: str, is_guest: bool):
        self.music_dir = Path(music_base_dir, dir_name)
        self.dir_name = dir_name
        self.display_name = display_name
        self.is_guest = is_guest

    def choose_track(self) -> Track:
        """
        Randomly choose a track from this person's music directory
        Returns: Track name
        """
        tracks = [f.name for f in self.music_dir.iterdir() if os.path.isfile(f)]
        current_timestamp = int(datetime.now().timestamp())
        max_attempts = 20

        for attempt in range(max_attempts):
            chosen_track = random.choice(tracks)
            log.info('choose track %s: %s', attempt, chosen_track)
            last_played = redis.get('last_played_' + chosen_track)

            if 'Broccoli Fuck' in chosen_track:
                log.info('%s bad, pick other song', chosen_track)
                continue

            if last_played is not None:
                seconds_ago = current_timestamp - int(last_played.decode())

                if attempt < 5:
                    minimum_time_ago = 60*60*5  # Last 5 hours
                elif attempt < 10:
                    minimum_time_ago = 60*60*4  # Last 2 hours
                elif attempt < 15:
                    minimum_time_ago = 60*60  # Last hour
                else:
                    minimum_time_ago = 15*60  # Last 15 minutes

                if seconds_ago < minimum_time_ago:
                    log.info('...was played %.2f hours ago, picking a new song', seconds_ago/3600)
                    continue
                else:
                    log.info('...was played %.2f hours ago', seconds_ago/3600)
            else:
                log.info('...was not played recently')
            break

        if attempt == max_attempts - 1:
            log.info('Attempts exhausted')

        redis.set('last_played_' + chosen_track, str(current_timestamp).encode())

        return self.track(chosen_track)

    def count_tracks(self) -> int:
        """
        Returns: Number of tracks in this person's music directory
        """
        return sum(1 for _d in self.music_dir.iterdir())

    def track(self, track_name: str) -> Track:
        """
        Get track by name
        Parameters:
            track_name: Track file name
        Returns: Track object
        """
        return Track(Path(self.music_dir, track_name))

    def tracks(self) -> List[Track]:
        """
        Get all this person's tracks as a list of Track objects
        """
        return [Track(entry) for entry in self.music_dir.iterdir()]

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

        for entry in self.music_dir.iterdir():
            if len(results) > limit:
                break
            if query.lower() in entry.name.lower():
                results.append(self.track(entry.name))

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
                               '--remux-video', 'ogg',
                               '-f', '251',
                               '--add-metadata',
                               url],
                              shell=False,
                              check=False,  # No exception on non-zero exit code
                              cwd=self.music_dir,
                              capture_output=True,
                              text=True)

    @staticmethod
    def by_dir_name(dir_name: str) -> 'Person':
        """
        Get person object from the name of a music directory.
        Parameters:
            dir_name: Name of directory
        Returns: Person instance
        """
        if dir_name.startswith('Guest-'):
            return Person(dir_name, dir_name[6:], True)
        else:
            return Person(dir_name, dir_name, False)

    @staticmethod
    def get_main() -> List['Person']:
        """
        Returns: List of Person objects for all Raphson members (CB, DK, JK)
        """
        persons = []
        for music_dir in Path(music_base_dir).iterdir():
            if not music_dir.name.startswith('Guest-'):
                person = Person(music_dir.name, music_dir.name, False)
                persons.append(person)
        return persons

    @staticmethod
    def get_guests() -> List['Person']:
        """
        Returns: List of Person objects for guests, generated dynamically from
                 directory names
        """
        persons = []
        for music_dir in Path(music_base_dir).iterdir():
            if music_dir.name.startswith('Guest-'):
                person = Person(music_dir.name, music_dir.name[6:], True)
                persons.append(person)
        return persons

    @staticmethod
    def get_all() -> List['Person']:
        """
        Returns: Concatenation of get_main() and get_guests()
        """
        return [*Person.get_main(), *Person.get_guests()]
