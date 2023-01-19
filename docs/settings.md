# Settings

The app is configured using environment variables. Below is a list of all environment variables, with their default values and a brief explanation.

## `TZ`

Configure system timezone. You can find a list of valid time zones [on wikipedia](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

## `MUSIC_MUSIC_DIR` = `/music`

Music directory. See [music-files.md](./music-files.md)

## `MUSIC_DATA_PATH` = `/data`

This directory is used to store the database files.
- `music.db`: Stores accounts and sessions. Also stores an index of playlist, tracks, and metadata.
- `cache.db`: Stores cached data for slow operations. For example, it stores transcoded audio, downloaded album covers, and scraped lyrics. This database may be deleted, but deleting it will severely impact application performance until it is populated again.

## `MUSIC_FFMPEG_LOGLEVEL` = `info`

Value for ffmpeg `-loglevel` option.

## `MUSIC_LOG_LEVEL` = `INFO`

Log level for all app loggers.

## `MUSIC_WEBSCRAPING_USER_AGENT`

User agent used for web scraper. The default value is a common web browser user agent.

## `MUSIC_TRACK_LIMIT_SECONDS` = `900`

Maximum track length. If a track is longer than this value, it is cut.

## `MUSIC_RADIO_PLAYLISTS`

Playlists to choose from, for radio

## `MUSIC_RADIO_ANNOUNCEMENTS_PLAYLIST`

Playlist with radio announcements

## `MUSIC_LASTFM_API_KEY`

## `MUSIC_LASTFM_API_SECRET`