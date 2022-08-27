from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
import os
import random
import subprocess
from subprocess import CompletedProcess
from metadata import Metadata


music_base_dir = Path('/music')
last_played: Dict[str, datetime] = {}


class Person:

    def __init__(self, dir_name: str, display_name: str, is_guest: bool):
        self.music_dir = Path(music_base_dir, dir_name)
        self.dir_name = dir_name
        self.display_name = display_name
        self.is_guest = is_guest

    def choose_track(self) -> str:
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
        return chosen_track

    def count_tracks(self) -> int:
        """
        Returns: Number of tracks in this person's music directory
        """
        return sum(1 for _d in self.music_dir.iterdir())

    def get_track_path(self, track_name: str) -> Path:
        """
        Get the full path for a music file.
        Parameters:
            track_name: Name of music file
        Returns: Path object for a music file
        """
        return Path(self.music_dir, track_name)

    def get_track_metadata(self, track_name: str) -> Metadata:
        return Metadata(self.get_track_path(track_name))

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
