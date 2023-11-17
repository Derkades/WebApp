# Settings

The app is configured using environment variables. Below is a list of all environment variables, with their default values and a brief explanation.

For boolean values, specify `1` or `true` (case insensitive) for true. Anything else is considered false.

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

Log level for all python loggers.

## `MUSIC_WEBSCRAPING_USER_AGENT`

User agent used for web scraper. The default value is a common web browser user agent.

## `MUSIC_TRACK_LIMIT_SECONDS` = `1200`

Maximum track length. If a track is longer than this value, it is truncated.

## `MUSIC_RADIO_PLAYLISTS`

Playlists to choose from, for radio. Semicolon separated.

## `MUSIC_LASTFM_API_KEY`

## `MUSIC_LASTFM_API_SECRET`

## `MUSIC_ENV`

Set to `dev` to enable developmnent mode. Default is `prod`.

## `MUSIC_PROXIES_X_FORWARDED_FOR`

Number of proxies in front of backend app that append to the X-Forwarded-For header. Defaults to 0. Setting it to less than the actual amount means the app sees the IP address of one of your proxies for all users. Setting it to a value greater than the actual amount of proxies means users can forge their remote address to be any arbitrary string.

## `MUSIC_OFFLINE_MODE` = True

Set to true to run the music player in [offline mode](./offline.md)
