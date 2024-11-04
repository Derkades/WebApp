import os
import pickle
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests


@dataclass
class State:
    server: str
    token: str
    file_type: str

    def save(self, state_path: Path) -> None:
        with state_path.open('wb') as fp:
            return pickle.dump(self, fp)

    @classmethod
    def load(cls, state_path: Path) -> 'State':
        with state_path.open('rb') as fp:
            return pickle.load(fp)


def setup_state() -> State:
    server = input('Server URL: ').rstrip('/')
    username = input('User name: ')
    password = input('Password: ')

    response = requests.post(server + '/auth/login',
                             json={'username': username,
                                   'password': password},
                             timeout=10)

    response.raise_for_status()
    token = response.json()['token']
    print('Logged in successfully')

    # file_type = input('Download type (original / mp3): ')
    file_type = 'mp3'

    return State(server, token, file_type)


def download_track(state: State, relpath: str, local_path: Path):
    r = requests.get(state.server + '/track/' + quote(relpath) + '/audio',
                     params={'type': 'mp3_with_metadata'},
                     timeout=60, # transcoding may take a while
                     headers={'Cookie': 'token=' + state.token},
                     stream=True)
    r.raise_for_status()
    with local_path.open('wb') as fp:
        shutil.copyfileobj(r.raw, fp)


def track_list(state: State, playlist_name: str):
    r = requests.get(state.server + '/tracks/filter?playlist=' + quote(playlist_name),
                     timeout=10,
                     headers={'Cookie': 'token=' + state.token})
    r.raise_for_status()
    return r.json()['tracks']


def download_playlist(state: State, playlist_name: str):
    tracks = track_list(state, playlist_name)
    playlist_path = Path(playlist_name).resolve()
    all_local_paths: set[str] = set()

    for track in tracks:
        relpath = track['path']
        local_path = Path(relpath + '.mp3').resolve()
        all_local_paths.add(local_path.as_posix())
        # don't allow directory traversal by server
        if not local_path.resolve().is_relative_to(playlist_path):
            raise RuntimeError(f'Path: {relpath} not relative to {playlist_path}')

        if local_path.exists():
            mtime = int(local_path.stat().st_mtime)
            if mtime != track['mtime']:
                print('Out of date: ' + relpath)
            else:
                print('OK: ' + relpath)
                continue
        else:
            print('Missing: ' + relpath)
            local_path.parent.mkdir(exist_ok=True)

        download_track(state, relpath, local_path)
        os.utime(local_path, (time.time(), track['mtime']))

    # Prune deleted tracks
    for track_path in playlist_path.glob('**/*'):
        if track_path.resolve().as_posix() not in all_local_paths:
            print('Delete: ' + relpath)
            track_path.unlink()


def main():
    state_path = Path('download-state.json')

    if state_path.is_file():
        state = State.load(state_path)
        # if not test_state(state):
        #     print('Configuration invalid, please log in again')
        #     state = setup_state()
        #     state.save(state_path)
    else:
        print('Not configured, please log in')
        state = setup_state()
        state.save(state_path)

    download_playlist(state, sys.argv[1])

if __name__ == '__main__':
    main()
