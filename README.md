# WebApp

Web-based music player for communities (hacker spaces, maker spaces).

## Introduction

Music is crucial when working on projects. However, when you're with a group, who is in charge? Everyone should be, of course! This music player allows everyone to create their own playlists. Then, when you're together, enable the playlists of everyone who is present. Music will be chosen from each playlist with a fair distribution.

## Features

- No repetition
    - Shuffle algorithm ensures the least recently played songs are picked first.
- No metadata hassle
    - Album covers are automatically fetched from MusicBrainz or using a web scraper
    - Lyrics are automatically fetched using a web scraper
    - Metadata editor to easily correct metadata on the fly
    - Audio is loudness-normalized ensuring consistent volume for all genres.
- Easy file management
    - Built-in web file browser to download, upload, rename and delete files
    - Built-in music downloader using `yt-dlp`
- Responsive and mobile compatible
    - Touch-friendly interface
    - Audio files and images are compressed on-the-fly, with various quality options to save data.
    - Also keyboard-friendly interface; hotkeys are available for common actions, allowing you to skip a track while wearing welding gloves.
- Statistics
    - See what other's are playing now or in the past
    - Statistics page with graphs based on historical data
    - Last.fm scrobbling (each user can connect their own last.fm account)
- Fun
    - Enable 'Album cover meme mode' to replace album covers by (sometimes) funny memes related to the song title.
- News
    - Optionally, insert news from [news scraper](https://github.com/Derkades/news-scraper) on the hour to keep up-to-date.
- Minimal: fast and secure
    - Written in pure HTML, CSS and JavaScript with minimal third party libraries. The frontend should be fast, even on an old laptop or cheap single board computer.
    - Queued songs are stored as blobs in the browser's storage. Temporary network connection issues are no problem.
    - Python dependencies are kept to a minimum, and we ship a custom build of FFmpeg for minimal storage usage.
    - Very strict Content-Security-Policy allows no communication from clients to the internet.

## Screenshots

See [docs/screenshots.md](docs/screenshots.md).

## Usage

See [docs/installation.md](docs/installation.md).

## User management

See [docs/manage.md](docs/manage.md).

## Development and translation

See [docs/development.md](docs/development.md).
