from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
import os
import random
import subprocess
from subprocess import CompletedProcess


music_base_dir = Path('/music')
last_played: Dict[str, datetime] = {}


class Person:

    def __init__(self, dir_name: str, display_name: str, is_guest: bool):
        self.music_dir = Path(music_base_dir, dir_name)
        self.dir_name = dir_name
        self.display_name = display_name
        self.is_guest = is_guest

    def choose_track(self) -> str:
        tracks = [f.name for f in self.music_dir.iterdir() if os.path.isfile(f)]
        for attempt in range(10):
            chosen_track = random.choice(tracks)
            if chosen_track in last_played:
                if datetime.now() - last_played[chosen_track] < timedelta(hours=2):
                    print(chosen_track, 'was played recently, picking a new song', flush=True)
                    continue
            break

        last_played[chosen_track] = datetime.now()
        return chosen_track

    def count_tracks(self) -> int:
        return sum(1 for _d in self.music_dir.iterdir())

    def get_track_path(self, track_name: str) -> Path:
        return Path(self.music_dir, track_name)

    def download(self, url: str) -> CompletedProcess:
        return subprocess.run(['yt-dlp', '--no-progress', '-f', '251', url],
                              shell=False,
                              cwd=self.music_dir,
                              capture_output=True,
                              text=True)

    @staticmethod
    def by_dir_name(dir_name: str) -> 'Person':
        if dir_name.startswith('Guest-'):
            return Person(dir_name, dir_name[6:], True)
        else:
            return Person(dir_name, dir_name, False)

    @staticmethod
    def get_main() -> List['Person']:
        return [
            Person('CB', 'CB', False),
            Person('DK', 'DK', False),
            Person('JK', 'JK', False),
        ]

    @staticmethod
    def get_guests() -> List['Person']:
        persons = []
        for music_dir in Path(music_base_dir).iterdir():
            if music_dir.name.startswith('Guest-'):
                persons.append(Person(music_dir.name, music_dir.name[6:], True))
        return persons

    @staticmethod
    def get_all() -> List['Person']:
        return [*Person.get_main(), *Person.get_guests()]
