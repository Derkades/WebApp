# Installation

## Pipx

Pipx can install Python programs, automatically installing dependencies in a virtual environment.

First install pipx using your system package manager, e.g. `sudo dnf install pipx`.

Then, run:

```
pipx install 'raphson-mp[online]'
```

Or if you are only planning to use the music player in offline mode, remove the `[online]` part to skip installing some dependencies.

The music player is now available as the command `raphson-mp`.

Unless you are using the music player only in offline mode, ffmpeg is required. Install it using your system package manager, e.g. `sudo apt install ffmpeg` or `sudo dnf install ffmpeg`.

Start the server: `raphson-mp start`.

The music player uses two configurable directories to store data, [--data-dir](./databases.md) and [--music-dir](./music-files.md) which are documented by the linked pages.

## Docker

Take the `compose.prod.yaml` compose file as a starting point.

Management tasks can be performed by running a second instance of the container:
```
docker compose run music --help
```
