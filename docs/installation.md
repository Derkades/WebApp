# Installation

See [databases](./databases.md) and [music files](./music-files.md) for more information about the file structure required by the music player.

## Pipx

Pipx can install Python programs, automatically installing dependencies in a virtual environment.

First install pipx using your system package manager, e.g. `sudo dnf install pipx`.

Then, run:

```
pipx install raphson-mp
```

The music player is now available as the command `raphson-mp`.

Unless you are using the music player only in offline mode, ffmpeg is required. Install it using your system package manager, e.g. `sudo dnf install ffmpeg`.

## Docker

Take the `compose.prod.yaml` compose file as a starting point.

Management tasks can be performed by running a second instance of the container:
```
docker compose run music --help
```
