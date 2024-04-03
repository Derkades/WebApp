# Installation

See [databases](./databases.md) and [music files](./music-files.md) for more information about the file structure required by the music player.

## Git clone

Requirements: ffmpeg, python3 and some dependencies (see requirements.txt)

Clone the repository:
```
git clone https://github.com/DanielKoomen/WebApp
```

Create the required directories:
```
mkdir data music
```

Start the server:
```
python3 mp.py start
```

For options help please run `python3 mp.py --help`.

## Docker

Take the `compose.prod.yaml` compose file as a starting point.

Management tasks can be performed by running a second instance of the container:
```
docker compose run music --help
```
