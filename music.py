from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
import os
import random
import subprocess
from subprocess import CompletedProcess

import cache
from metadata import Metadata
import settings


music_base_dir = Path('/music')
last_played: Dict[str, datetime] = {}


class Track:

    def __init__(self, path: Path):
        self.path = path

    def name(self) -> str:
        return self.path.name

    def metadata(self) -> Metadata:
        return Metadata(self.path)

    def transcoded_audio(self) -> bytes:
        in_path_abs = self.path.absolute().as_posix()

        cache_object = cache.get('transcoded audio', in_path_abs)

        if cache_object.exists():
            print('Returning cached audio', flush=True)
            return cache_object.retrieve()

        # 1. Stilte aan het begin weghalen met silenceremove: https://ffmpeg.org/ffmpeg-filters.html#silenceremove
        # 2. Audio omkeren
        # 3. Stilte aan het eind (nu begin) weghalen
        # 4. Audio omkeren
        # 5. Audio normaliseren met dynaudnorm: https://ffmpeg.org/ffmpeg-filters.html#dynaudnorm

        # Nu zou je zeggen dat we ook stop_periods kunnen gebruiken om stilte aan het eind weg te halen, maar
        # dat werkt niet. Van sommige nummers (bijv. irrenhaus) werd alles eraf geknipt behalve de eerste paar
        # seconden. Ik heb geen idee waarom, de documentatie is vaag. Oplossing: keer het nummer om, en haal
        # nog eens stilte aan "het begin" weg.

        filters = '''
        silenceremove=start_periods=1:start_threshold=-50dB,
        areverse,
        silenceremove=start_periods=1:start_threshold=-50dB,
        areverse,
        dynaudnorm=peak=0.5
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
                '-b:a', settings.opus_bitrate,
                '-f', 'opus',
                '-vbr', 'on',
                '-t', settings.max_duration,
                '-filter:a', filters,
                cache_object.path]
        subprocess.run(command,
                       shell=False,
                       check=True,
                       capture_output=False)

        return cache_object.retrieve()


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
        for _attempt in range(10):
            chosen_track = random.choice(tracks)
            if 'Broccoli Fuck' in chosen_track or \
               chosen_track in last_played and \
               datetime.now() - last_played[chosen_track] < timedelta(hours=2):
                print(chosen_track, 'was played recently, picking a new song',
                      flush=True)
                continue
            break

        last_played[chosen_track] = datetime.now()
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

    def search_tracks(self, query: str, limit: int = 3) -> List[Track]:
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
        return subprocess.run(['yt-dlp', '--no-progress', '-f', '251', '--add-metadata', url],
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
        return [
            Person('CB', 'CB', False),
            Person('DK', 'DK', False),
            Person('JK', 'JK', False),
        ]

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
