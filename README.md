# WebApp

Music player for communities (hacker spaces, maker spaces).

## Features

- Per-person playlists, can be toggled individually
- During shuffle play, tracks are chosen from each directory in fair round-robin fashion.
- Album cover automatically fetched using MusicBrainz or Bing web scraper
- Lyrics automatically fetched using web scraper
- Songs are downloaded in the background, switching to a next track is instant
- Responsive design, made for desktop and mobile
- Audio files and images are compressed on-the-fly, facilitating use over cellular data
- Easy to use music downloader within the web interface
- Touch-friendly interface
- Hotkeys for most common actions
- No JavaScript or CSS frameworks, the web interface makes no requests to third party domains
- Audio is RMS-normalized and silence is trimmed from the start and end

## Usage

Prebuilt container image: `ghcr.io/danielkoomen/webapp`. Take the `docker-compose.yaml` file in this repository as an example, replacing `build` with an `image`.

### `MUSIC_MUSIC_DIR` (default `/music`)

This directory should contain one subdirectory for each playlist. Directory names may be prefixed with `Guest-` to mark the playlist as a guest. Place audio files in these playlist directories. Creating directories inside playlist directories is not supported at this time.

An example:

```
music
├── CB
│   ├── Sub Focus & Wilkinson - Ray Of Sun.mp3
│   ├── The Elite - Falling Angels (Official Video) _ Coone & Da Tweekaz & Hard Driver.mp3
│   ├── Toneshifterz - I Am Australian (Hardstyle) _ HQ Videoclip.mp3
├── DK
│   ├── 025 Midnight Oil - Beds Are Burning.mp3
│   ├── 061 Pink Floyd - Another Brick In The Wall.mp3
│   └── 078 Nena - Irgendwie irgendwo irgendwann (long version).mp3
├── Guest-RS
│   ├── Tom Misch & Yussef Dayes - Storm Before The Calm (feat. Kaidi Akinnibi) (Official Audio).webm
│   ├── U & ME - Alt J (Official Audio) [RMkxrJuxRsk].webm
│   └── Zes - Juniper [UNYiVK3Cl98].webm
├── Guest-WD
│   └── 08. Watercolors (feat. Dave Koz).mp3
└── JK
    ├── Aerosmith - Dream On.mp3
    ├── A spaceman came travelling.mp3
    └── A Warrior's Call.mp3
```

Don't worry about removing strings like "(Official Audio)" from song titles, these are automatically removed. If possible, do add the following metadata to each file: artist, album artist, album title, song title, album cover image.

### `MUSIC_CACHE_DIR` (default `/cache`)

This directory is used to store the result of time-consuming operations, like transcoding audio or web scraping for album art. It may be emptied at any time as long as the application is not running.

### `MUSIC_WEB_PASSWORD` (not set by default)

Set an optional password to access the web interface. Strongly recommended if exposed to the internet.

### `MUSIC_REDIS_HOST` / `MUSIC_REDIS_PORT`

Connection details for Redis server. Defaults to `localhost`, port `6379`.

## Development

With docker and docker-compose-plugin installed, run the following command to start a local testing server:
```
docker compose up --build
```

Before doing so, you will need to create a music and cache directory. You may need to change `user` in the docker compose file if your user is not using the default id of 1000.

### Using babel for translations

In templates:
```
{% trans %}Something in English{% endtrans %}
```

In Python:
```
from flask_babel import gettext as _

translated_string = _("Something in English")
```

### Translating from English to other languages

1. Run `./update-translations.sh`
2. Edit the `messages.po` file in `src/translations/<language_code>/LC_MESSAGES/` using a text editor or PO editor like Poedit. To create a new language, run: `pybabel init -i messages.pot -d src/translations -l <language_code>`
3. Run `./update-translations.sh` again to ensure the language files are in a consistent format.

## Made possible by open source software

This project is using many open source software and libraries, such as:

- [Flask](https://flask.palletsprojects.com)
- [BeautifulSoup](https://pypi.org/project/beautifulsoup4)
- [Gunicorn](https://gunicorn.org)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [Pillow](https://pillow.readthedocs.io)
- [Requests](https://pypi.org/project/requests)
- [Material Design Icons](https://materialdesignicons.com)
- [MusicBrainz](https://musicbrainz.org) (musicbrainzngs)
- [sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [Docker, docker compose](https://docs.docker.com/get-docker)

It also relies on some other parties for web scraping, who shall not be named.
