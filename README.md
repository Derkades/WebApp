# WebApp

Web-based music player for communities (hacker spaces, maker spaces).

## Introduction

Music is important. However, when you're with a group, who is in charge? Everyone should be, of course! This music player allows everyone to create their own playlists. Then, when you're together, enable the playlists of everyone who is present. Music will be chosen from each playlist with a fair distribution.

## Features

- No repetition!
    - Shuffle algorithm ensures the least recently played songs are picked first.
- No metadata hassle!
    - Album covers are automatically fetched from MusicBrainz or using a bing web scraper
    - Lyrics are automatically fetched using a web scraper
    - Metadata editor to easily correct metadata during music playback
- Easy file management!
    - Built-in web file browser to download, upload, rename and delete files
    - Built-in music downloader using `yt-dlp`
- Performant!
    - Written in pure HTML, CSS and JavaScript without third party libraries. The frontend is fast even, on an old laptop or cheap single board computer!
    - Queued songs are stored as blobs in the browser's storage. Temporary internet connection issues are no problem.
- Mobile compatible!
    - Responsive design, made for desktop and mobile
    - Touch-friendly interface
    - Audio files and images are compressed on-the-fly, with various quality options to save data.
- Welding gloves compatible!
    - Hotkeys are available for common actions, allowing you to skip a track while wearing the most unwieldy attire.
- Freedom!
    - Meant to run on your own server, using your own music files.
    - Web interface makes no requests to the internet, so clients can't be tracked
- Statistics!
    - Last.fm scrobbling (each user can connect their own last.fm account)
- Fair!
    - Audio is RMS-normalized. Loudly mastered EDM will be just as loud as quiet 80s tracks.
- Fun!
    - Enable 'Album cover meme mode' to replace album covers by (sometimes) funny memes related to the song title.

## Screenshots

See [docs/screenshots.md](docs/screenshots.md).

## Usage

See [docs/installation.md](docs/installation.md).

## User management

See [docs/manage.md](docs/manage.md).

## Development and translation

See [docs/development.md](docs/development.md).

## Made possible by open source software

This project is using many open source software and libraries, such as:

- [Python](https://www.python.org/)
- [Python Gunicorn](https://gunicorn.org)
- [Python Flask](https://flask.palletsprojects.com)
- [Python Flask-Babel](https://python-babel.github.io/flask-babel/)
- [Python requests](https://pypi.org/project/requests)
- [Python BeautifulSoup](https://pypi.org/project/beautifulsoup4)
- [Python lxml](https://pypi.org/project/beautifulsoup4)
- [MusicBrainz](https://musicbrainz.org) and Python musicbrainzngs
- [Python Pillow](https://pillow.readthedocs.io)
- [Python bcrypt](https://pypi.org/project/bcrypt/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [Material Design Icons](https://pictogrammers.com/library/mdi)
- [sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [Docker, docker compose](https://docs.docker.com/get-docker)
- [Nginx](https://nginx.com)

It also relies on some other parties for web scraping, who shall not be named.
